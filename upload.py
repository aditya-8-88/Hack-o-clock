import pandas as pd
from sqlalchemy import create_engine

# Step 1: Load the CSV file with encoding fix
csv_path = 'sales_data_sample.csv'  # Replace with your actual file path

try:
    df = pd.read_csv(csv_path)
except UnicodeDecodeError:
    df = pd.read_csv(csv_path, encoding='ISO-8859-1')  # Fallback encoding

# Step 2: Neon connection string
connection_string = "postgresql://cohort_owner:t5TKWuPm3FMZ@ep-winter-poetry-a57jcanb-pooler.us-east-2.aws.neon.tech/cohort?sslmode=require"

# Step 3: Create database engine
engine = create_engine(connection_string)

# Step 4: Upload DataFrame to PostgreSQL
table_name = "sales_report"  # Changed to valid SQL table name (no space)
df.to_sql(table_name, engine, if_exists='replace', index=False)

print(f"✅ Data uploaded to table '{table_name}' successfully.")
