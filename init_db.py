# init_db.py
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os

# --- IMPORTANT ---
# Set your PostgreSQL connection details here.
DB_NAME = "dermatology_db"
DB_USER = "postgres" 
DB_PASSWORD = "Noor@818" # Change this to your password
DB_HOST = "localhost"
DB_PORT = "5432"

# Connection string for the default 'postgres' database
conn_string_default = f"dbname='postgres' user='{DB_USER}' host='{DB_HOST}' password='{DB_PASSWORD}' port='{DB_PORT}' sslmode='disable'"

try:
    # --- Step 1: Connect to the default database to create our new one ---
    conn = psycopg2.connect(conn_string_default)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT) # Needed to run CREATE DATABASE
    cursor = conn.cursor()
    
    # Check if the database already exists
    cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}'")
    exists = cursor.fetchone()
    if not exists:
        cursor.execute(f"CREATE DATABASE {DB_NAME}")
        print(f"Database '{DB_NAME}' created successfully.")
    else:
        print(f"Database '{DB_NAME}' already exists.")
        
    cursor.close()
    conn.close()

    # --- Step 2: Connect to the new database to create tables ---
    conn_string_new_db = f"dbname='{DB_NAME}' user='{DB_USER}' host='{DB_HOST}' password='{DB_PASSWORD}' port='{DB_PORT}' sslmode='disable'"
    conn = psycopg2.connect(conn_string_new_db)
    cursor = conn.cursor()

    # Read the SQL script
    with open("init_db.sql", "r") as f:
        sql_script = f.read()

    # Execute the script to create tables
    cursor.execute(sql_script)
    conn.commit()
    print("Tables created successfully inside 'dermatology_db'.")

except psycopg2.Error as e:
    print(f"An error occurred: {e}")

finally:
    # Clean up
    if 'cursor' in locals() and cursor and not cursor.closed:
        cursor.close()
    if 'conn' in locals() and conn and not conn.closed:
        conn.close()
    print("Process finished. Connection closed.")
