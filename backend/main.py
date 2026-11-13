
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

    if len(rows) < 2:
        raise HTTPException(
            status_code=422,
            detail="At least two observations are required"
        )

    # Convert timestamps
    arrivals = [
        datetime.fromisoformat(row[0])
        for row in rows
    ]

    # Calculate intervals between consecutive arrivals
    intervals = []

    for i in range(1, len(arrivals)):
        difference = (
            arrivals[i] - arrivals[i - 1]
        ).total_seconds() / 3600

        if difference > 0:
            intervals.append(difference)

    if not intervals:
        raise HTTPException(
            status_code=422,
            detail="No valid arrival intervals found"
        )

    # Calculate average and median intervals
    sorted_intervals = sorted(intervals)

    average_hours = sum(intervals) / len(intervals)

    middle = len(sorted_intervals) // 2

    if len(sorted_intervals) % 2 == 0:
        median_hours = (
            sorted_intervals[middle - 1]
            + sorted_intervals[middle]
        ) / 2
    else:
        median_hours = sorted_intervals[middle]

    # Calculate interval variability
    variance = sum(
        (value - average_hours) ** 2
        for value in intervals
    ) / len(intervals)

    standard_deviation = variance ** 0.5

    variability_percent = (
        standard_deviation / average_hours * 100
        if average_hours > 0 else 0
    )

    # Assess data reliability
    if len(arrivals) >= 20 and variability_percent <= 10:
        reliability = "high"
    elif len(arrivals) >= 10 and variability_percent <= 20:
        reliability = "medium"
    else:
        reliability = "low"

    # Predict the next arrival using the median
    latest_arrival = arrivals[-1]

    predicted_arrival = (
        latest_arrival
        + timedelta(hours=median_hours)
    )

    return {
        "locality_id": locality_id,
        "observations": len(arrivals),
        "average_interval_hours": round(average_hours, 2),
        "median_interval_hours": round(median_hours, 2),
        "variability_percent": round(variability_percent, 2),
        "reliability": reliability,
        "latest_arrival": latest_arrival.isoformat(),
        "predicted_next_arrival": predicted_arrival.isoformat(),
        "prediction_type": "experimental",
        "data_source": "simulated"
    }
