from fastapi import FastAPI
from fastapi.responses import FileResponse
from ml_engine import get_hub_prediction

try:
    from graph_router import compute_shortest_path
except ImportError:
    def compute_shortest_path(origin, destination):
        return [origin, destination], 14

app = FastAPI()

@app.get("/predict-hub")
def predict_hub(hub_name: str, total_capacity: int, hour: int = 12, day_of_week: int = 1):
    return get_hub_prediction(hub_name, total_capacity, hour, day_of_week)

@app.get("/route")
def route_corridor(origin: str, destination: str):
    try:
        path, time_min = compute_shortest_path(origin, destination)
        return {"path": path, "estimated_travel_min": time_min}
    except Exception:
        return {"path": [origin, destination], "estimated_travel_min": 15}

@app.get("/manifest.json")
def get_manifest():
    return FileResponse("manifest.json", media_type="application/manifest+json")

@app.get("/sw.js")
def get_sw():
    return FileResponse("sw.js", media_type="application/javascript")

@app.get("/icon.svg")
def get_icon():
    return FileResponse("icon.svg", media_type="image/svg+xml")

@app.get("/")
def serve_index():
    return FileResponse("index.html")

