__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
import altair as alt
import streamlit as st
import pandas as pd
import psycopg2
import time
from utils import save_db_details, get_the_output_from_llm, execute_the_solution
from utils import explain_chart

# ─── Session State ──────────────────────────────────────────────────────────────
for key, default in {
    'db_uri': None,
    'unique_id': None,
    'messages': [],
    'metrics': {'processing_time': None, 'query_complexity': None, 'rows_returned': None},
    'last_df': None
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ─── UI Setup ───────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Database Assistant", layout="wide")
page = st.sidebar.radio("Navigate to:", ["Chat", "Visualize & Analyze"])

# Sidebar: DB Connect + Metrics
with st.sidebar:
    st.header("Database Connection")
    uri = st.text_input("PostgreSQL URI", placeholder="postgresql://username:password@host:port/database")
    if st.button("Connect"):
        if not uri:
            st.warning("Please enter a connection string")
        else:
            try:
                with st.spinner("Connecting..."):
                    t0 = time.time()
                    conn = psycopg2.connect(uri)
                    conn.close()
                    st.session_state.db_uri = uri
                    st.session_state.unique_id = save_db_details(uri)
                    st.success(f"Connected in {time.time()-t0:.2f}s")
            except Exception as e:
                st.error(f"Connection failed: {e}")
                st.session_state.db_uri = None
                st.session_state.unique_id = None

    st.header("Query Metrics")
    m = st.session_state.metrics
    if m['processing_time'] is not None:
        c1, c2 = st.columns(2)
        c1.metric("Processing Time", f"{m['processing_time']:.2f}s")
        c2.metric("Complexity", m['query_complexity'].capitalize() if m['query_complexity'] else "N/A")
        if m['rows_returned'] is not None:
            st.metric("Rows Returned", m['rows_returned'])

# ─── Chat Interface ─────────────────────────────────────────────────────────────
st.header("Ask Your Database")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        c = msg["content"]
        if isinstance(c, dict) and c.get("type")=="dataframe":
            st.dataframe(c["data"])
            if "sql" in c:
                with st.expander("View SQL Query"):
                    st.code(c["sql"])
            if "metrics" in c:
                with st.expander("Query Performance"):
                    mm = c["metrics"]
                    a,b = st.columns(2)
                    a.metric("Time", f"{mm['processing_time']:.2f}s")
                    b.metric("Complexity", mm['query_complexity'].capitalize())
                    if 'rows_returned' in mm:
                        st.metric("Rows", mm['rows_returned'])
        else:
            # plain text
            st.write(c.get("text") if isinstance(c, dict) else c)

if prompt := st.chat_input("Ask about your data..."):
    st.chat_message("user").write(prompt)
    st.session_state.messages.append({"role":"user","content":prompt})

    if not st.session_state.db_uri:
        response = {"type":"text","text":"Please connect first","metrics":{'processing_time':0,'query_complexity':'low'}}
    else:
        with st.spinner("Processing..."):
            t0 = time.time()
            try:
                response = get_the_output_from_llm(
                    prompt,
                    st.session_state.unique_id,
                    st.session_state.db_uri
                )
                # stamp timing
                if isinstance(response,dict) and "metrics" in response:
                    response["metrics"]["processing_time"] = time.time()-t0
                    st.session_state.metrics = response["metrics"]
                # if dataframe: stash for viz
                if isinstance(response,dict) and response.get("type")=="dataframe":
                    st.session_state.last_df = response["data"]
            except Exception as e:
                response = {"type":"text","text":f"Error: {e}","metrics":{'processing_time':time.time()-t0,'query_complexity':'low'}}
                st.session_state.metrics = response["metrics"]

    with st.chat_message("assistant"):
        if isinstance(response,dict) and response.get("type")=="dataframe":
            st.dataframe(response["data"])
            with st.expander("SQL & Metrics"):
                t1, t2 = st.tabs(["SQL","Metrics"])
                with t1: st.code(response["sql"])
                with t2:
                    mm = response["metrics"]
                    x,y = st.columns(2)
                    x.metric("Time",f"{mm['processing_time']:.2f}s")
                    y.metric("Complexity",mm['query_complexity'].capitalize())
                    if 'rows_returned' in mm:
                        st.metric("Rows",mm['rows_returned'])
        else:
            txt = response.get("text") if isinstance(response,dict) else str(response)
            st.write(txt)
            if isinstance(response,dict) and "metrics" in response:
                with st.expander("Metrics"):
                    mm = response["metrics"]
                    st.metric("Time",f"{mm['processing_time']:.2f}s")
                    st.metric("Complexity",mm['query_complexity'].capitalize())

    st.session_state.messages.append({"role":"assistant","content":response})

# ─── Visualization & Analysis ──────────────────────────────────────────────────
st.markdown("---")
st.header("Visualization & Analysis")

def clean_numeric(df):
    return df.apply(lambda col: pd.to_numeric(col.astype(str).str.replace(",", ""), errors="coerce"))

df = st.session_state.last_df
if df is None:
    st.info("Run a query above to see charts.")
else:
    # Ensure numeric columns
    num_df = df.apply(pd.to_numeric, errors="coerce").dropna(axis=1, how="all")
    
    if num_df.empty:
        st.warning("No numeric columns to plot.")
    else:
        x_col = st.selectbox("Select X-axis column", df.columns, key="viz_x")
        y_col = st.selectbox("Select Y-axis column", num_df.columns, key="viz_y")
        chart_type = st.radio("Chart type", ["Line", "Bar", "Histogram"], horizontal=True)

        st.subheader("📈 Chart")

        # Prepare clean DataFrame
        plot_df = pd.DataFrame({x_col: df[x_col], y_col: df[y_col]}).dropna()

        if chart_type == "Line":
            st.line_chart(plot_df.set_index(x_col))
        elif chart_type == "Bar":
            st.bar_chart(plot_df.set_index(x_col))
        elif chart_type == "Histogram":
            hist = alt.Chart(plot_df).mark_bar().encode(
                alt.X(y_col, bin=alt.Bin(maxbins=30), title=y_col),
                alt.Y('count()', title='Frequency')
            ).properties(width=700, height=400)
            st.altair_chart(hist, use_container_width=True)

        # 📝 Explain Data (optional)
        if st.button("📝 Explain Data"):
            sample = plot_df.head(5)
            explanation = explain_chart(sample, x_col, y_col, chart_type)
            st.markdown(f"**Insight:** {explanation}")
            # Optional: plug into your `explain_chart(...)` logic here
