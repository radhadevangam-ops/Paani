
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import sqlite3

app = FastAPI(
    title="Paani API",
    description="Water supply monitoring and prediction platform",
    version="1.0.0"
)


# Database connection
def get_connection():
    connection = sqlite3.connect("paani.db")
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


# Create database tables
def create_database():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS localities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            locality_id INTEGER NOT NULL,
            actual_arrival TEXT NOT NULL,
            duration_minutes INTEGER NOT NULL,
            source TEXT NOT NULL,
            FOREIGN KEY (locality_id) REFERENCES localities(id)
        )
    """)

    connection.commit()
    connection.close()


create_database()


# Request formats
class Locality(BaseModel):
    name: str


class SupplyReport(BaseModel):
    locality_id: int
    actual_arrival: datetime
    duration_minutes: int = Field(gt=0)
    source: str = "resident"


# Home endpoint
@app.get("/")
def home():
    return {
        "message": "Welcome to Paani!",
        "status": "running"
    }


# Add a locality
@app.post("/localities")
def add_locality(locality: Locality):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "INSERT INTO localities (name) VALUES (?)",
            (locality.name.strip(),)
        )
        connection.commit()

        return {
            "message": "Locality added successfully",
            "id": cursor.lastrowid,
            "name": locality.name.strip()
        }

    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="This locality already exists"
        )

    finally:
        connection.close()


# Retrieve all localities
@app.get("/localities")
def get_localities():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT id, name FROM localities")
    rows = cursor.fetchall()

    connection.close()

    return [
        {"id": row[0], "name": row[1]}
        for row in rows
    ]


# Add a water-supply report
@app.post("/reports")
def add_report(report: SupplyReport):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT id FROM localities WHERE id = ?",
        (report.locality_id,)
    )

    if cursor.fetchone() is None:
        connection.close()
        raise HTTPException(
            status_code=404,
            detail="Locality not found"
        )

    cursor.execute("""
        INSERT INTO reports (
            locality_id,
            actual_arrival,
            duration_minutes,
            source
        )
        VALUES (?, ?, ?, ?)
    """, (
        report.locality_id,
        report.actual_arrival.isoformat(),
        report.duration_minutes,
        report.source
    ))

    connection.commit()
    report_id = cursor.lastrowid
    connection.close()

    return {
        "message": "Water-supply report saved successfully",
        "report_id": report_id,
        "locality_id": report.locality_id
    }


# Retrieve all reports
@app.get("/reports")
def get_reports():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            reports.id,
            localities.name,
            reports.actual_arrival,
            reports.duration_minutes,
            reports.source
        FROM reports
        JOIN localities
        ON reports.locality_id = localities.id
        ORDER BY reports.id DESC
    """)

    rows = cursor.fetchall()
    connection.close()

    return [
        {
            "id": row[0],
            "locality": row[1],
            "actual_arrival": row[2],
            "duration_minutes": row[3],
            "source": row[4]
        }
        for row in rows
    ]


# Retrieve reports for one locality
@app.get("/localities/{locality_id}/reports")
def get_locality_reports(locality_id: int):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT id FROM localities WHERE id = ?",
        (locality_id,)
    )

    if cursor.fetchone() is None:
        connection.close()
        raise HTTPException(
            status_code=404,
            detail="Locality not found"
        )

    cursor.execute("""
        SELECT id, actual_arrival, duration_minutes, source
        FROM reports
        WHERE locality_id = ?
        ORDER BY id DESC
    """, (locality_id,))

    rows = cursor.fetchall()
    connection.close()

    return [
        {
            "id": row[0],
            "actual_arrival": row[1],
            "duration_minutes": row[2],
            "source": row[3]
        }
        for row in rows
    ]


# Predict the next water arrival
@app.get("/localities/{locality_id}/prediction")
def predict_next_arrival(locality_id: int):

    connection = get_connection()
    cursor = connection.cursor()

    # Check whether locality exists
    cursor.execute(
        "SELECT id FROM localities WHERE id = ?",
        (locality_id,)
    )

    if cursor.fetchone() is None:
        connection.close()
        raise HTTPException(
            status_code=404,
            detail="Locality not found"
        )

    # Retrieve historical arrival times
    cursor.execute("""
        SELECT actual_arrival
        FROM reports
        WHERE locality_id = ?
        ORDER BY actual_arrival ASC
    """, (locality_id,))

    rows = cursor.fetchall()
    connection.close()

    # At least two observations are required
    if len(rows) < 2:
        raise HTTPException(
            status_code=422,
            detail="Not enough historical data"
        )

    # Convert stored timestamps into datetime objects
    arrivals = [
        datetime.fromisoformat(row[0])
        for row in rows
    ]

    # Calculate intervals between arrivals
    intervals = []

    for i in range(1, len(arrivals)):
        difference = (
            arrivals[i] - arrivals[i - 1]
        ).total_seconds()

        intervals.append(difference)

    # Calculate average interval
    average_seconds = sum(intervals) / len(intervals)

    # Predict the next arrival
    latest_arrival = arrivals[-1]

    predicted_arrival = (
        latest_arrival + timedelta(seconds=average_seconds)
    )

    return {
        "locality_id": locality_id,
        "observations": len(arrivals),
        "average_interval_hours": average_seconds / 3600,
        "latest_arrival": latest_arrival.isoformat(),
        "predicted_next_arrival": predicted_arrival.isoformat(),
        "prediction_type": "experimental",
        "data_source": "simulated"
    }


