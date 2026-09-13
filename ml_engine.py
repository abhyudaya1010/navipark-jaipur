import numpy as np
from sklearn.ensemble import RandomForestRegressor

# Synthetic dynamic training data for Jaipur urban mobility
X_train = np.array([
    [150/250, 9, 1, 0.85],  [100/250, 14, 1, 0.40], [200/250, 19, 1, 0.90], [250/250, 3, 1, 0.10],
    [150/250, 10, 3, 0.85], [100/250, 15, 3, 0.45], [200/250, 20, 3, 0.95], [250/250, 4, 3, 0.15],
    [120/250, 11, 5, 0.80], [180/250, 18, 5, 0.85],  [150/250, 8, 0, 0.90],  [200/250, 21, 6, 0.85]
] * 10)
y_train = np.clip(X_train[:, 1] * 3.2 + X_train[:, 3] * 45 + np.random.normal(0, 2, len(X_train)), 8, 98)

model = RandomForestRegressor(n_estimators=60, random_state=42)
model.fit(X_train, y_train)

def get_hub_prediction(hub_name: str, total_capacity: int, hour: int, day_of_week: int):
    is_peak = (8 <= hour <= 11) or (17 <= hour <= 21)
    base_factor = 0.88 if is_peak else 0.32
    
    X_input = np.array([[total_capacity / 250.0, hour, day_of_week, base_factor]])
    pred_occ = float(np.clip(model.predict(X_input)[0], 8, 98))
    
    # Hub-specific Jaipur modifier (WTP/GT heavier during evening/weekend)
    if ("World Trade Park" in hub_name or "Gaurav Tower" in hub_name) and is_peak:
        pred_occ = min(98.0, pred_occ + 12.0)
    elif "Railway Station" in hub_name:
        pred_occ = min(95.0, pred_occ + 5.0)

    free_slots = max(0, round(total_capacity * (1.0 - pred_occ / 100.0)))
    traffic_score = round(min(100, pred_occ * 0.92))
    ev_util = round(min(98, pred_occ * 0.78))
    
    status = "Congested / High Load" if pred_occ > 72 or traffic_score > 68 else "Normal Flow"
    
    return {
        "hub_name": hub_name,
        "network_status": status,
        "parking": {
            "predicted_occupancy_pct": round(pred_occ, 1),
            "estimated_free_slots": free_slots
        },
        "traffic_density_score": traffic_score,
        "ev_charging_utilization_pct": ev_util
    }
