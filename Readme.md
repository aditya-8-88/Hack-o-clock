 
# Natural Language to SQL Assistant with Gemini AI

 

A Streamlit-powered AI assistant that converts natural language queries into SQL using Google's Gemini AI, executes them on PostgreSQL databases, and displays results with rich visualizations and performance metrics.
 

## Features ✨

- **Natural Language Processing**: Converts plain English questions to SQL
- **Schema Analysis**: Auto-discovers tables/columns/relationships
- **Smart Formatting**: Automatically formats results (currency, dates, numbers)
- **Query Explanation**: Shows generated SQL with explanations
- **Performance Metrics**: Tracks processing time & resource usage
- **Conversation History**: Maintains context-aware chat history
- **DB Connection Management**: Secure URI-based PostgreSQL connections

## Workflow Diagram 🔄

```mermaid
graph TD
    A[User Input] --> B(Gemini AI Processing)
    B --> C{SQL Valid?}
    C -->|Yes| D[Execute on PostgreSQL]
    C -->|No| E[Error Handling]
    D --> F[Format Results]
    F --> G[Display Metrics]
    G --> H[Update Chat History]
    E --> H
Installation 🛠️


Clone Repository

 
git clone https://github.com/yourusername/nl2sql-assistant.git
cd nl2sql-assistant


Install Dependencies
 
pip install -r requirements.txt
Configure Environment

python

# .env
GEMINI_API_KEY="your_google_api_key"


# Configuration ⚙️
Database Connection Format:
 
postgresql://<user>:<password>@<host>:<port>/<database>


Folder Structure:
├── app.py          # Main application
├── utils.py        # Core logic module
├── csvs/           # Auto-generated schema files
├── vectors/        # ChromaDB vector stores
└── .env            # Configuration secrets



Usage 🚀
Start Application

 
streamlit run app.py


# Sample Queries:

plaintext
Copy
"Show top 5 customers by total purchases"
"Compare monthly sales between 2023 and 2024"
"List products with stock below 50 units"
Interface Guide:

Left Sidebar: Database connection & metrics

Main Area: Chat interface with query/results

Expandable Sections: SQL code & explanations

Query Processing Flow 🔍
Schema Analysis:

Auto-extract tables/columns/relationships

Create vector embeddings for schema

NLU Processing:

Gemini AI analyzes query intent

Identifies relevant tables/columns

SQL Generation:

python
Copy
def generate_sql(query, schema_info, foreign_keys):
    # Uses Gemini's advanced reasoning to create optimized SQL
    # Implements FK-aware JOINs and proper aggregation
    return validated_sql
Execution & Formatting:

python
Copy
def execute_the_solution(sql, db_uri):
    # Safe query execution
    # Automatic currency/date/number formatting
    return pandas.DataFrame | error_message
Result Presentation:

Interactive dataframes

Syntax-highlighted SQL

Performance metrics dashboard

Tech Stack 🧩
Component	Technology
Natural Language	Google Gemini AI
Database	PostgreSQL
UI Framework	Streamlit
Vector Store	ChromaDB
Data Processing	Pandas/Numpy
ORM	psycopg2
Environment	python-dotenv
Contributing 🤝
Fork the repository

Create your feature branch (git checkout -b feature/amazing-feature)

Commit changes (git commit -m 'Add some amazing feature')

Push to branch (git push origin feature/amazing-feature)

Open a Pull Request

License 📄
MIT License - see LICENSE for details

Acknowledgments 🙏
Google Gemini Team for advanced AI capabilities

Streamlit for intuitive UI framework

PostgreSQL community for robust database system

Contact: aryanshukla095@gmail.com | LinkedIn Profile: # gemini_sql_chat
# gemini_sql_chat
