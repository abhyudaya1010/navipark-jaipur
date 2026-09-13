import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

HUBS = ["Sindhi_Camp", "C_Scheme", "JLN_Marg", "Tonk_Road", "Airport_Corridor"]
HUB_BASE_RATIO = {
    "Sindhi_Camp": 0.75,
    "C_Scheme": 0.68,
    "JLN_Marg": 0.80,
    "Tonk_Road": 0.65,
    "Airport_Corridor": 0.70
}

np.random.seed(42)
n_samples = 1200
X_hub = np.random.choice(HUBS, size=n_samples)
X_cap = np.random.choice([150, 220, 320, 380, 450, 600], size=n_samples)
X_hour = np.random.randint(0, 24, size=n_samples)
X_dow = np.random.randint(1, 8, size=n_samples)

y_occ = []
for h_name, cap, hr, dow in zip(X_hub, X_cap, X_hour, X_dow):
    base_r = HUB_BASE_RATIO[h_name]
    rush = 1.25 if (8 <= hr <= 10 or 17 <= hr <= 20) else (0.55 if hr <= 5 else 0.95)
    weekend_factor = 1.10 if dow in [6, 7] else 1.00
    target_occ = min(int(cap), max(5, int(cap * base_r * rush * weekend_factor + np.random.normal(0, cap * 0.03))))
    y_occ.append(target_occ)
y_occ = np.array(y_occ)

preprocessor = ColumnTransformer(
    transformers=[('cat', OneHotEncoder(drop='first'), [0])],
    remainder='passthrough'
)

model = Pipeline(steps=[
    ('prep', preprocessor),
    ('regressor', GradientBoostingRegressor(n_estimators=60, random_state=42))
])

model.fit(np.column_stack((X_hub, X_cap, X_hour, X_dow)), y_occ)

def get_hub_prediction(hub_name: str, total_capacity: int, hour: int, day_of_week: int) -> dict:
    X_input = np.array([[hub_name, total_capacity, int(hour), int(day_of_week)]], dtype=object)
    pred_occ = float(model.predict(X_input)[0])
    safe_occ = int(np.clip(round(pred_occ), 5, total_capacity))
    return {
        "hub_name": hub_name,
        "total_capacity": total_capacity,
        "predicted_occupied": safe_occ,
        "occupancy_percentage": round((safe_occ / total_capacity) * 100, 1)
    }
    
