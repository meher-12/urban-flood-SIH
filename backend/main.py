import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import importlib

try:
    engine_module = importlib.import_module("engine")
    FloodCouplingEngine = engine_module.FloodCouplingEngine
    MockFloodEngine = engine_module.MockFloodEngine
except ModuleNotFoundError as exc:
    try:
        engine_module = importlib.import_module("backend.engine")
        FloodCouplingEngine = engine_module.FloodCouplingEngine
        MockFloodEngine = engine_module.MockFloodEngine
    except ModuleNotFoundError:
        raise RuntimeError(
            "The local 'engine.py' module is required to start this application."
        ) from exc

app = FastAPI(
    title="Urban Flood Nowcasting API",
    description="SIH Backend for Real-time Drainage & Rainfall Coupling Simulation",
    version="1.0.0"
)

# Enable CORS for communication with React, Flutter, or Node frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
INP_FILE = BASE_DIR / "model.inp"
MOCK_DATA_FILE = BASE_DIR.parent / "src" / "data" / "MockData.json"

# Auto-select real SWMM model if present, otherwise use mock engine
if INP_FILE.exists() and engine_module.Simulation is not None:
    engine = FloodCouplingEngine(str(INP_FILE))
else:
    engine = MockFloodEngine()

incidents = []

if MOCK_DATA_FILE.exists():
    import json

    with MOCK_DATA_FILE.open(encoding="utf-8") as mock_file:
        incidents = json.load(mock_file).get("incidents", [])

class RainfallPayload(BaseModel):
    station_id: str
    rainfall_intensity_mm_hr: float
    duration_hours: float = 1.0


class IncidentPayload(BaseModel):
    type: str
    severity: Literal["Low", "Medium", "Critical"]
    lat: float
    lng: float
    notes: str


class RoutePayload(BaseModel):
    rainIntensity: float
    drainCapacity: float

@app.get("/")
def read_root():
    return {
        "system": "Urban Flood Nowcasting System",
        "status": "Online",
        "engine_type": "SWMM Hydrodynamic Coupled" if INP_FILE.exists() and engine_module.Simulation is not None else "Mock Fallback Active"
    }


@app.get("/api/v1/telemetry/live")
def get_live_telemetry():
    if not MOCK_DATA_FILE.exists():
        raise HTTPException(status_code=503, detail="Telemetry data is unavailable")

    import json

    with MOCK_DATA_FILE.open(encoding="utf-8") as mock_file:
        return json.load(mock_file)

@app.post("/api/v1/predict")
def predict_flood(payload: RainfallPayload):
    """
    Triggers the coupling simulation engine based on real-time sensor data or meteorological forecasts.
    """
    try:
        results = engine.run_simulation(payload.rainfall_intensity_mm_hr)
        return {
            "station_id": payload.station_id,
            "prediction_results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/hotspots")
def get_historical_hotspots():
    """
    Returns chronic urban waterlogging bottlenecks loaded from GIS city layers.
    """
    return {
        "city": "Target Smart City",
        "total_monitored_nodes": 142,
        "critical_hotspots": [
            {"id": "J104", "lat": 12.9716, "lng": 77.5946, "reason": "Constricted pipe diameter / high runoff"},
            {"id": "B2", "lat": 12.9816, "lng": 77.6046, "reason": "Low elevation basin accumulation"},
            {"id": "Subway_01", "lat": 12.9256, "lng": 77.5842, "reason": "Depressed roadway geometry"}
        ]
    }


@app.post("/api/v1/incidents")
def create_incident(payload: IncidentPayload):
    incident = {
        "id": f"INC-{int(datetime.now(timezone.utc).timestamp() * 1000) % 100000:05d}",
        **payload.model_dump(),
        "timestamp": datetime.now().astimezone().strftime("%I:%M %p"),
        "status": "ACTIVE",
    }
    incidents.append(incident)
    return {"success": True, **incident}


@app.delete("/api/v1/incidents/{incident_id}")
def resolve_incident(incident_id: str):
    for incident in incidents:
        if incident["id"] == incident_id:
            incident["status"] = "RESOLVED"
            return {"success": True, "incidentId": incident_id}
    raise HTTPException(status_code=404, detail="Incident not found")


@app.post("/api/v1/routes/evaluate")
def evaluate_route(payload: RoutePayload):
    critical = payload.rainIntensity > 70 and payload.drainCapacity < 50
    return {
        "primaryRoutePassable": not critical,
        "primaryDepthMeters": round(payload.rainIntensity * 0.012, 2),
        "detourRecommended": critical,
        "detourDeltaKm": 1.8,
        "detourDeltaMins": 4,
    }


@app.websocket("/ws/telemetry")
async def telemetry_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.send_json({
                "event": "SENSOR_UPDATE",
                "sensorId": "SENSOR-01",
                "newWaterLevel": 0.85,
                "timestamp": datetime.now().astimezone().isoformat(),
            })
            await asyncio.sleep(10)
    except WebSocketDisconnect:
        pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)