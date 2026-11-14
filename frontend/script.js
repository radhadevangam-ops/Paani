
const API_BASE_URL = "YOUR_FASTAPI_URL";

const localitySelect = document.getElementById("locality-select");
const predictionElement = document.getElementById("prediction");
const reliabilityElement = document.getElementById("reliability");
const predictionNote = document.getElementById("prediction-note");
const reportsContainer = document.getElementById("reports");
const reportForm = document.getElementById("report-form");
const reportMessage = document.getElementById("report-message");

async function apiRequest(endpoint, options = {}) {
    if (API_BASE_URL === "YOUR_FASTAPI_URL") {
        throw new Error("Backend URL has not been configured.");
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...options.headers
        }
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.detail || `API error: ${response.status}`);
    }

    return data;
}

function formatDate(value) {
    return new Date(value).toLocaleString("en-IN", {
        dateStyle: "medium",
        timeStyle: "short"
    });
}

async function loadLocalities() {
    try {
        const localities = await apiRequest("/localities");

        localitySelect.innerHTML = "";

        if (localities.length === 0) {
            localitySelect.add(new Option("No localities available", ""));
            return;
        }

        localities.forEach(locality => {
            localitySelect.add(
                new Option(locality.name, locality.id)
            );
        });

        await loadLocalityData(localitySelect.value);

    } catch (error) {
        console.error(error);
        localitySelect.innerHTML = "";
        localitySelect.add(new Option("Could not load localities", ""));
        predictionElement.textContent = "Unavailable";
        reliabilityElement.textContent = "Unavailable";
        predictionNote.textContent = error.message;
    }
}

async function loadLocalityData(localityId) {
    if (!localityId) return;

    await Promise.all([
        loadPrediction(localityId),
        loadReports(localityId)
    ]);
}

async function loadPrediction(localityId) {
    predictionElement.textContent = "Loading...";
    reliabilityElement.textContent = "Loading...";

    try {
        const data = await apiRequest(
            `/localities/${localityId}/prediction`
        );

        predictionElement.textContent =
            formatDate(data.predicted_next_arrival);

        reliabilityElement.textContent =
            data.reliability.toUpperCase();

        predictionNote.textContent =
            `${data.observations} observations · ` +
            `Experimental prediction · ` +
            `Data source: ${data.data_source}`;

    } catch (error) {
        console.error(error);

        predictionElement.textContent = "Unavailable";
        reliabilityElement.textContent = "Unavailable";
        predictionNote.textContent = error.message;
    }
}

async function loadReports(localityId) {
    reportsContainer.textContent = "Loading reports...";

    try {
        const reports = await apiRequest(
            `/localities/${localityId}/reports`
        );

        reportsContainer.innerHTML = "";

        if (reports.length === 0) {
            reportsContainer.textContent = "No reports available yet.";
            return;
        }

        reports.forEach(report => {
            const item = document.createElement("div");
            item.className = "report";

            const details = document.createElement("div");

            const arrival = document.createElement("strong");
            arrival.textContent = formatDate(report.actual_arrival);

            const duration = document.createElement("small");
            duration.textContent =
                `${report.duration_minutes} minutes`;

            const source = document.createElement("small");
            source.textContent = `Source: ${report.source}`;

            details.append(arrival, duration, source);
            item.appendChild(details);
            reportsContainer.appendChild(item);
        });

    } catch (error) {
        console.error(error);
        reportsContainer.textContent =
            "Could not load reports: " + error.message;
    }
}

localitySelect.addEventListener("change", () => {
    loadLocalityData(localitySelect.value);
});

reportForm.addEventListener("submit", async event => {
    event.preventDefault();

    const localityId = localitySelect.value;
    const arrivalTime =
        document.getElementById("arrival-time").value;

    const duration = Number(
        document.getElementById("duration").value
    );

    if (!localityId || !arrivalTime || duration <= 0) {
        reportMessage.textContent =
            "Please complete all report fields.";
        return;
    }

    const report = {
        locality_id: Number(localityId),
        actual_arrival: arrivalTime + ":00",
        duration_minutes: duration,
        source: "resident"
    };

    try {
        reportMessage.textContent = "Submitting report...";

        await apiRequest("/reports", {
            method: "POST",
            body: JSON.stringify(report)
        });

        reportMessage.textContent =
            "Report submitted successfully.";

        reportForm.reset();
        await loadLocalityData(localityId);

    } catch (error) {
        console.error(error);
        reportMessage.textContent =
            "Submission failed: " + error.message;
    }
});

loadLocalities();
