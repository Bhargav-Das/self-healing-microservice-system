
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

# Locate project root
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables
load_dotenv(BASE_DIR / ".env", override=True)

# Construct database URL safely
database_url = URL.create(
    drivername="postgresql+psycopg",
    username=os.environ["POSTGRES_USER"],
    password=os.environ["POSTGRES_PASSWORD"],
    host="localhost",
    port=5432,
    database=os.environ["POSTGRES_DB"],
)

print("Connecting to PostgreSQL...")

try:
    engine = create_engine(
        database_url,
        connect_args={"connect_timeout": 5}
    )

    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT 1")
        ).scalar()

        print("Database connection successful!")
        print("Test result:", result)

except Exception as error:
    print("Database connection failed!")
    print("Error type:", type(error).__name__)
    print("Details:", str(error).splitlines()[0])
