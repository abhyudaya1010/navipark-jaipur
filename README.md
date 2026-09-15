# 🚘 NaviPark 3D Jaipur Pro
> Smart mobility, live OSRM corridor routing, ML occupancy prediction, EV POI discovery, and multi-stop heritage TSP solver for Jaipur.

| Metric / Scope | Spec |
| :--- | :--- |
| **Coverage** | Jaipur (JL Marg, WTP, GT, Amer, Albert Hall) |
| **Routing** | OSRM API + Haversine combinatorial TSP (`N!`) |
| **Forecasting** | Scikit-Learn `RandomForestRegressor` (diurnal curves) |
| **Resilience** | Zero-config automatic fallback to mock telemetry |

## Architecture & Stack
* **UI/PWA**: Streamlit + Glassmorphism UI + Custom PWA Manifest/Service Worker shim
* **Geospatial & Routing**: OSRM API (driving coordinates, distance/duration legs) + PyDeck (3D column/path layers)
* **ML Predictor**: Scikit-Learn `RandomForestRegressor` trained on diurnal occupancy curves (peak hours, tariff tiers, day-of-week)
* **Live Telemetry Fallback**: Supabase relational schema with automated background sync + offline mock state fallback (`DEFAULT_HUBS_DATA`)
* **Optimization**: Exact combinatorial TSP solver (`itertools.permutations` + Haversine distance) for Jaipur heritage circuits

## Features
1. **Interactive 3D Corridor Map**: Live traffic congestion coloring (Free-Flow, Moderate, Heavy) + interactive vehicle progress telemetry.
2. **Digital Gate Pass**: Instant QR pass generation with pay-at-venue calculations.
3. **ML Occupancy & Demand Predictor**: 24-hour diurnal load forecasting per hub/charger.
4. **Heritage TSP Solver**: Optimal touring sequence across Amer Fort, Jal Mahal, Hawa Mahal, City Palace, and Albert Hall.
