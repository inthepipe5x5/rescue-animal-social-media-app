import psycopg2
import os
import dotenv

dotenv.load_dotenv()

conn = psycopg2.connect(
    host=os.environ.get("SUPABASE_HOST"),
    database="postgres",
    user=os.environ.get("SUPABASE_USER"),
    password=os.environ.get("SUPABASE_PW"),
    port=5432,
    sslmode="require"
)

cur = conn.cursor()
cur.execute("SELECT version();")
version = cur.fetchone()
print(version)

cur.close()
conn.close()