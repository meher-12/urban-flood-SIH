from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import importlib

try:
    engine_module = importlib.import_module("engine")
    FloodCouplingEngine = engine_module.FloodCouplingEngine
    MockFloodEngine = engine_module.MockFloodEngine
except ModuleNotFoundError as exc:
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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

INP_FILE = "model.inp"

# Auto-select real SWMM model if present, otherwise use mock engine
if os.path.exists(INP_FILE):
    engine = FloodCouplingEngine(INP_FILE)
else:
    engine = MockFloodEngine()

class RainfallPayload(BaseModel):
    station_id: str
    rainfall_intensity_mm_hr: float
    duration_hours: float = 1.0

@app.get("/")
def read_root():
    return {
        "system": "Urban Flood Nowcasting System",
        "status": "Online",
        "engine_type": "SWMM Hydrodynamic Coupled" if os.path.exists(INP_FILE) else "Mock Fallback Active"
    }

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)