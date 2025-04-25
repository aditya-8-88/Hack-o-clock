__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

import streamlit as st
import pandas as pd
import psycopg2
import time
from utils import save_db_details, get_the_output_from_llm, execute_the_solution

# Initialize session state
if 'db_uri' not in st.session_state:
    st.session_state.db_uri = None
if 'unique_id' not in st.session_state:
    st.session_state.unique_id = None
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'metrics' not in st.session_state:
    st.session_state.metrics = {
        'processing_time': None,
        'query_complexity': None,
        'rows_returned': None
    }

# UI Setup
st.set_page_config(page_title="Database Assistant", layout="wide")
# st.title("Smart SQL")

# Database Connection
with st.sidebar:
    st.header("Database Connection")
    uri = st.text_input(
        "PostgreSQL URI",
        placeholder="postgresql://username:password@host:port/database"
    )
    
    if st.button("Connect"):
        if not uri:
            st.warning("Please enter a connection string")
        else:
            try:
                with st.spinner("Connecting..."):
                    start_time = time.time()
                    # Test connection
                    conn = psycopg2.connect(uri)
                    conn.close()
                    
                    # Save connection details
                    st.session_state.db_uri = uri
                    st.session_state.unique_id = save_db_details(uri)
                    connection_time = time.time() - start_time
                    
                    st.success(f"Successfully connected in {connection_time:.2f}s!")
            except Exception as e:
                st.error(f"Connection failed: {str(e)}")
                st.session_state.db_uri = None
                st.session_state.unique_id = None
    
    # Metrics section in sidebar
    st.header("Query Metrics")
    if st.session_state.metrics['processing_time'] is not None:
        cols = st.columns(2)
        cols[0].metric("Processing Time", f"{st.session_state.metrics['processing_time']:.2f}s")
        cols[1].metric("Complexity", st.session_state.metrics['query_complexity'].capitalize())
        
        if st.session_state.metrics['rows_returned'] is not None:
            st.metric("Rows Returned", st.session_state.metrics['rows_returned'])

# Chat Interface
st.header("Ask Your Database")

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if isinstance(message["content"], dict):
            if message["content"].get("type") == "dataframe":
                st.dataframe(message["content"]["data"])
                if "sql" in message["content"]:
                    with st.expander("View SQL Query"):
                        st.code(message["content"]["sql"])
                if "metrics" in message["content"]:
                    with st.expander("Query Performance"):
                        m = message["content"]["metrics"]
                        cols = st.columns(2)
                        cols[0].metric("Processing Time", f"{m['processing_time']:.2f}s")
                        cols[1].metric("Complexity", m['query_complexity'].capitalize())
                        if 'rows_returned' in m:
                            st.metric("Rows Returned", m['rows_returned'])
            else:
                st.write(message["content"].get("text", "No content"))
        else:
            st.write(message["content"])

# Chat input
if prompt := st.chat_input("Ask about your data..."):
    # Add user message to history
    st.chat_message("user").write(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Check connection
    if not st.session_state.db_uri:
        response = {
            "type": "text", 
            "text": "Please connect to a database first",
            "metrics": {
                "processing_time": 0,
                "query_complexity": "low"
            }
        }
    else:
        with st.spinner("Processing your query..."):
            start_time = time.time()
            try:
                # Get response from LLM
                response = get_the_output_from_llm(
                    prompt, 
                    st.session_state.unique_id,
                    st.session_state.db_uri
                )
                
                # Update processing time
                processing_time = time.time() - start_time
                if isinstance(response, dict) and "metrics" in response:
                    response["metrics"]["processing_time"] = processing_time
                
                # Update session metrics
                if isinstance(response, dict) and "metrics" in response:
                    st.session_state.metrics = response["metrics"]
                    
            except Exception as e:
                response = {
                    "type": "text",
                    "text": f"Error processing query: {str(e)}",
                    "metrics": {
                        "processing_time": time.time() - start_time,
                        "query_complexity": "low"
                    }
                }
                st.session_state.metrics = response["metrics"]
    
    # Display response
    with st.chat_message("assistant"):
        if isinstance(response, dict):
            if response["type"] == "dataframe":
                print(response["data"])
                st.dataframe(response["data"])
                with st.expander("View SQL Query & Metrics"):
                    tab1, tab2 = st.tabs(["SQL Query", "Performance"])
                    with tab1:
                        st.code(response["sql"])
                    with tab2:
                        if "metrics" in response:
                            m = response["metrics"]
                            cols = st.columns(2)
                            cols[0].metric("Processing Time", f"{m['processing_time']:.2f}s")
                            cols[1].metric("Complexity", m['query_complexity'].capitalize())
                            if 'rows_returned' in m:
                                st.metric("Rows Returned", m['rows_returned'])
            else:
                st.write(response["text"])
                if "metrics" in response:
                    with st.expander("Query Metrics"):
                        m = response["metrics"]
                        st.metric("Processing Time", f"{m['processing_time']:.2f}s")
                        st.metric("Complexity", m['query_complexity'].capitalize())
    
    # Store response
    st.session_state.messages.append({
        "role": "assistant", 
        "content": response
    })

def describe_data_with_gemini(data):
    """Generate a description of the data using Gemini API."""
    if data.empty:
        return "The dataset is empty. Please provide a valid dataset."

    # Convert DataFrame to a string representation
    data_preview = data.head(5).to_string(index=False)

    # Create a prompt for Gemini
    prompt = f"""
    You are a data analyst. Analyze the following dataset and provide a brief description:
    
    Dataset Preview:
    {data_preview}
    
    Include details about:
    1. The type of data (e.g., sales, customer, product, etc.).
    2. Key columns and their significance.
    3. Any patterns or insights you can infer from the preview.
    """

    try:
        response = gemini_model.generate_content(prompt)
        if not response.text:
            raise ValueError("Empty response from Gemini")
        return response.text.strip()
    except Exception as e:
        return f"Error generating description: {str(e)}"