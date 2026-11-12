
from fastapi import FastAPI
from pydantic import BaseModel
import sqlite3

app = FastAPI(
    title="Paani API",
    description="Water supply monitoring and prediction platform",
    version="1.0.0"
)

# Create the database and localities table
def create_database():
    connection = sqlite3.connect("paani.db")
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS localities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)

    connection.commit()
    connection.close()


create_database()


# Data format for a new locality
class Locality(BaseModel):
    name: str


@app.get("/")
def home():
    return {
        "message": "Welcome to Paani!",
        "status": "running"
    }


# Retrieve all localities
@app.get("/localities")
def get_localities():
    connection = sqlite3.connect("paani.db")
    cursor = connection.cursor()

    cursor.execute("SELECT id, name FROM localities")
    rows = cursor.fetchall()

    connection.close()

    return [
        {"id": row[0], "name": row[1]}
        for row in rows
    ]


# Add a new locality
@app.post("/localities")
def add_locality(locality: Locality):
    connection = sqlite3.connect("paani.db")
    cursor = connection.cursor()

    try:
        cursor.execute(
            "INSERT INTO localities (name) VALUES (?)",
            (locality.name.strip(),)
        )
        connection.commit()

        new_id = cursor.lastrowid

        return {
            "message": "Locality added successfully",
            "id": new_id,
            "name": locality.name.strip()
        }

    except sqlite3.IntegrityError:
        return {"error": "This locality already exists"}

    finally:
        connection.close()
