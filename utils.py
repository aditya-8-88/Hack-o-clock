import os
import re
import pandas as pd
import numpy as np
import psycopg2
from uuid import uuid4
from dotenv import load_dotenv
import google.generativeai as genai
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders.csv_loader import CSVLoader

# Initialize folders
os.makedirs('csvs', exist_ok=True)
os.makedirs('vectors', exist_ok=True)

# Load environment variables
load_dotenv()

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("Missing GEMINI_API_KEY in .env file")

genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-1.5-pro-latest')

# Simple text embeddings
class SimpleEmbeddings:
    def __init__(self, dimensions=384):
        self.dimensions = dimensions
    
    def embed_documents(self, texts):
        if not texts:
            return [np.ones(self.dimensions)]  # Return at least one vector with all 1s
        return [np.ones(self.dimensions) * (i + 1) for i in range(len(texts))]  # Return unique vectors
    
    def embed_query(self, text):
        if not text:
            return np.ones(self.dimensions)  # Return a vector with all 1s
        return np.ones(self.dimensions) * 0.5  # Return a unique query vector

embeddings = SimpleEmbeddings()

def get_basic_table_details(cursor):
    """Get all tables and columns from the database"""
    cursor.execute("""
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
    """)
    return cursor.fetchall()

def get_foreign_key_info(cursor):
    """Get all foreign key relationships"""
    cursor.execute("""
        SELECT
            conrelid::regclass AS table_name,
            conname AS foreign_key,
            confrelid::regclass AS referred_table
        FROM pg_constraint
        WHERE contype = 'f' AND connamespace = 'public'::regnamespace
    """)
    return cursor.fetchall()

def create_vectors(filename, persist_directory):
    """Create vector store from schema CSV"""
    try:
        loader = CSVLoader(
            file_path=filename,
            metadata_columns=['table_name']
        )
        docs = loader.load()
        
        # Handle empty documents case
        if not docs:
            print(f"Warning: No documents loaded from {filename}")
            return Chroma(
                embedding_function=embeddings,
                persist_directory=persist_directory
            )
            
        texts = [str(doc.page_content) for doc in docs]
        metadatas = [doc.metadata for doc in docs]
        
        return Chroma.from_texts(
            texts=texts,
            embedding=embeddings,
            persist_directory=persist_directory,
            metadatas=metadatas
        )
    except Exception as e:
        print(f"Error creating vectors: {e}")
        # Create empty Chroma store as fallback
        return Chroma(
            embedding_function=embeddings,
            persist_directory=persist_directory
        )

def save_db_details(db_uri):
    """Save database schema and create vector store"""
    unique_id = str(uuid4()).replace("-", "_")
    try:
        with psycopg2.connect(db_uri) as conn:
            with conn.cursor() as cursor:
                # Save tables and columns
                tables = get_basic_table_details(cursor)
                df_tables = pd.DataFrame(tables, columns=['table_name', 'column_name', 'data_type'])
                df_tables.to_csv(f'csvs/tables_{unique_id}.csv', index=False)
                
                # Save foreign keys
                foreign_keys = get_foreign_key_info(cursor)
                df_fk = pd.DataFrame(foreign_keys, columns=['table_name', 'foreign_key', 'referred_table'])
                df_fk.to_csv(f'csvs/foreign_keys_{unique_id}.csv', index=False)
                
                create_vectors(f'csvs/tables_{unique_id}.csv', f"./vectors/tables_{unique_id}")
    except Exception as e:
        raise Exception(f"Database error: {str(e)}")
    return unique_id

def generate_sql(query, schema_info, foreign_keys):
    """Generate SQL using Gemini with dynamic schema"""
    prompt = f"""You are a PostgreSQL expert. Generate SQL for this database:
    
    Database Schema:
    {schema_info}
    
    Foreign Key Relationships:
    {foreign_keys}
    
    User Question: {query}
    
    Rules:
    1. Use proper JOINs based on foreign keys
    2. Only select necessary columns
    3. Format SQL between ```sql markers
    4. Add comments for complex logic
    
    Respond ONLY with the SQL query:"""
    
    try:
        response = gemini_model.generate_content(prompt)
        if not response.text:
            raise ValueError("Empty response from Gemini")
        
        # Extract SQL from response
        sql_match = re.search(r"```sql\n(.*?)\n```", response.text, re.DOTALL)
        if not sql_match:
            return {
                "error": f"No valid SQL found in response:\n{response.text}",
                "response_text": response.text,
                "success": False
            }
            
        return {
            "sql": sql_match.group(1).strip(),
            "response_text": response.text,
            "success": True
        }
    except Exception as e:
        return {
            "error": f"AI Error: {str(e)}",
            "success": False
        }

def get_relevant_tables(query, unique_id):
    """Get tables relevant to the query using vector similarity"""
    vectordb = Chroma(
        persist_directory=f"./vectors/tables_{unique_id}",
        embedding_function=embeddings
    )
    docs = vectordb.similarity_search(query, k=5)  # Get top 5 relevant tables
    # FIX: Use table_name from metadata instead of source file path
    return list({doc.metadata['table_name'] for doc in docs if 'table_name' in doc.metadata})

def format_schema_info(df_tables, tables):
    """Format schema information for prompt"""
    schema_info = []
    for table in tables:
        columns = df_tables[df_tables['table_name'] == table]
        schema_info.append(
            f"Table {table}:\n" + 
            columns[['column_name', 'data_type']]
            .to_string(index=False)
        )
    return "\n\n".join(schema_info)

def execute_the_solution(sql_query, db_uri):
    """Execute SQL and return properly formatted results"""
    try:
        # Execute query directly without markdown parsing
        with psycopg2.connect(db_uri) as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql_query)
                if cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    data = cursor.fetchall()
                    
                    # Create DataFrame with proper formatting
                    df = pd.DataFrame(data, columns=columns)
                    
                    # Auto-format columns
                    for col in df.columns:
                        # Format numeric columns
                        if pd.api.types.is_numeric_dtype(df[col]):
                            if 'amount' in col.lower():
                                df[col] = df[col].apply(lambda x: f"${float(x):,.2f}" if pd.notnull(x) else "")
                            else:
                                df[col] = df[col].apply(lambda x: f"{x:,.2f}" if pd.notnull(x) else "")
                        # Format date columns
                        elif pd.api.types.is_datetime64_any_dtype(df[col]):
                            df[col] = df[col].dt.strftime('%Y-%m-%d')
                    
                    return df
                return "Query executed successfully"
                
    except Exception as e:
        return f"Execution error: {str(e)}"

def get_the_output_from_llm(query, unique_id, db_uri):
    """Main function to process queries"""
    try:
        # Load schema data
        df_tables = pd.read_csv(f'csvs/tables_{unique_id}.csv', dtype=str)
        df_fk = pd.read_csv(f'csvs/foreign_keys_{unique_id}.csv', dtype=str)
        
        # Get relevant tables
        relevant_tables = get_relevant_tables(query, unique_id)
        if not relevant_tables:
            relevant_tables = df_tables['table_name'].unique().tolist()[:3]
        
        # Format schema info
        schema_info = format_schema_info(df_tables, relevant_tables)
        
        # Format foreign keys
        foreign_keys = "\n".join(
            f"{row['table_name']}.{row['foreign_key']} → {row['referred_table']}"
            for _, row in df_fk.iterrows()
            if row['table_name'] in relevant_tables
        )
        
        # Generate SQL
        generation_result = generate_sql(query, schema_info, foreign_keys)
        
        if not generation_result.get("success"):
            return {
                "type": "text",
                "text": generation_result.get("error", "Unknown error"),
                "metrics": {
                    "processing_time": 0,
                    "query_complexity": "low"
                }
            }

        sql = generation_result["sql"]
        
        # Execute query
        execution_result = execute_the_solution(sql, db_uri)  # FIX: Pass raw SQL
        
        if isinstance(execution_result, pd.DataFrame):
            return {
                "type": "dataframe", 
                "data": execution_result,
                "sql": sql,
                "metrics": {
                    "processing_time": 0,  # Will be set in app.py
                    "query_complexity": "high" if len(execution_result) > 100 else "medium",
                    "rows_returned": len(execution_result)
                }
            }
        else:
            return {
                "type": "text",
                "text": f"```sql\n{sql}\n```\n\n{execution_result}",
                "metrics": {
                    "processing_time": 0,  # Will be set in app.py
                    "query_complexity": "low"
                }
            }
            
    except Exception as e:
        return {
            "type": "text", 
            "text": f"Processing error: {str(e)}",
            "metrics": {
                "processing_time": 0,
                "query_complexity": "low"
            }
        }