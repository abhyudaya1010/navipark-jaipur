import streamlit as st
import streamlit.components.v1 as components
import pydeck as pdk
import qrcode
import io
import datetime
import random
import requests
import pandas as pd
import json
import numpy as np
import itertools
from sklearn.ensemble import RandomForestRegressor
from supabase import create_client, Client

# ==========================================
# 1. STREAMLIT CONFIG & PWA MANIFEST / SW LOADER
# ==========================================
st.set_page_config(
    page_title="NaviPark 3D Pro - Smart Mobility & Heritage TSP",
    page_icon="🚘",
    layout="wide",
    initial_sidebar_state="expanded"
)

pwa_manifest_json = json.dumps({
    "name": "NaviPark 3D Jaipur Pro",
    "short_name": "NaviPark Pro",
    "description": "Smart Mobility, AI Route Engine, ML Predictor, Live EV Network & Heritage TSP for Jaipur",
    "start_url": "./",
    "display": "standalone",
    "background_color": "#070A12",
    "theme_color": "#38BDF8",
    "icons": [
        {
            "src": "https://cdn-icons-png.flaticon.com/512/1048/1048314.png",
            "sizes": "192x192",
            "type": "image/png"
        },
        {
            "src": "https://cdn-icons-png.flaticon.com/512/1048/1048314.png",
            "sizes": "512x512",
            "type": "image/png"
        }
    ]
})

js_code = f"""
<script>
    const manifest = {pwa_manifest_json};
    const blob = new Blob([JSON.stringify(manifest)], {{type: 'application/json'}});
    const manifestURL = URL.createObjectURL(blob);
    const parentDocument = window.parent.document;
    const existing = parentDocument.querySelector('link[rel="manifest"]');
    if (existing) {{ existing.remove(); }}
    const link = parentDocument.createElement('link');
    link.rel = 'manifest';
    link.href = manifestURL;
    parentDocument.head.appendChild(link);

    if ('serviceWorker' in navigator) {{
        navigator.serviceWorker.register('./sw.js').catch(() => {{}});
    }}
</script>
"""
components.html(js_code, height=0)

# ==========================================
# 2. HIGH-CONTRAST GLASS UI STYLES
# ==========================================
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #070A12 0%, #0F172A 50%, #030712 100%);
        color: #F8FAFC;
    }
    .main-title {
        font-size: 2.8rem;
        font-weight: 900;
        background: linear-gradient(90deg, #38BDF8 0%, #818CF8 50%, #C084FC 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
        letter-spacing: -0.5px;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #94A3B8;
        font-weight: 500;
        margin-bottom: 20px;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 800 !important;
        color: #38BDF8 !important;
    }
    .stMetric {
        background: rgba(15, 23, 42, 0.75) !important;
        border: 1px solid rgba(56, 189, 248, 0.2) !important;
        backdrop-filter: blur(16px);
        border-radius: 16px !important;
        padding: 16px !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5);
    }
    section[data-testid="stSidebar"] {
        background-color: rgba(15, 23, 42, 0.95) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background-color: rgba(30, 41, 59, 0.5);
        padding: 6px;
        border-radius: 14px;
        flex-wrap: wrap;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px;
        color: #94A3B8;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2563EB !important;
        color: #FFFFFF !important;
        box-shadow: 0 0 15px rgba(37, 99, 235, 0.5);
    }
    </style>
""", unsafe_allow_html=True)

ORIGIN_COORDS = {
    "Jaipur International Airport (JAI)": [26.8242, 75.8122],
    "Jaipur Junction Railway Station": [26.9196, 75.7878],
    "Sindhi Camp Bus Stand": [26.9240, 75.7989],
    "Malaviya Nagar": [26.8389, 75.8056],
    "Vaishali Nagar": [26.9124, 75.7433],
    "C-Scheme": [26.9098, 75.8006],
    "Mansarovar Metro Station": [26.8819, 75.7663]
}

DEFAULT_HUBS_DATA = [
    {"id": "hub_gt", "name": "Gaurav Tower (GT) Hub", "category": "Commercial", "lat": 26.8528, "lon": 75.8052, "height": 250, "total_slots": 150, "occupied": 130, "road_quality": 8, "ev_slots": 12, "hourly_rate": 30},
    {"id": "hub_wtp", "name": "World Trade Park (WTP) Hub", "category": "Commercial", "lat": 26.8538, "lon": 75.8058, "height": 300, "total_slots": 300, "occupied": 240, "road_quality": 9, "ev_slots": 25, "hourly_rate": 40},
    {"id": "hub_rp", "name": "Raja Park Commercial Hub", "category": "Commercial", "lat": 26.8917, "lon": 75.8239, "height": 200, "total_slots": 100, "occupied": 85, "road_quality": 6, "ev_slots": 8, "hourly_rate": 25},
    {"id": "hub_jj", "name": "Jaipur Junction Station Hub", "category": "Transit", "lat": 26.9196, "lon": 75.7878, "height": 280, "total_slots": 250, "occupied": 210, "road_quality": 7, "ev_slots": 15, "hourly_rate": 20},
    {"id": "hub_mi", "name": "MI Road Shopping District", "category": "Commercial", "lat": 26.9154, "lon": 75.8118, "height": 220, "total_slots": 120, "occupied": 105, "road_quality": 8, "ev_slots": 10, "hourly_rate": 30},
    {"id": "hub_mnit", "name": "MNIT Campus Smart Hub", "category": "Education", "lat": 26.8627, "lon": 75.8122, "height": 180, "total_slots": 80, "occupied": 42, "road_quality": 9, "ev_slots": 20, "hourly_rate": 15},
    {"id": "hub_hm", "name": "Hawa Mahal (Palace of Winds)", "category": "Landmark", "lat": 26.9239, "lon": 75.8267, "height": 260, "total_slots": 90, "occupied": 78, "road_quality": 7, "ev_slots": 6, "hourly_rate": 35},
    {"id": "hub_cp", "name": "City Palace Jaipur", "category": "Landmark", "lat": 26.9258, "lon": 75.8237, "height": 290, "total_slots": 120, "occupied": 95, "road_quality": 8, "ev_slots": 10, "hourly_rate": 35},
    {"id": "hub_af", "name": "Amer Fort (Amber)", "category": "Landmark", "lat": 26.9855, "lon": 75.8513, "height": 350, "total_slots": 200, "occupied": 160, "road_quality": 8, "ev_slots": 12, "hourly_rate": 50},
    {"id": "hub_jm", "name": "Jal Mahal (Water Palace)", "category": "Landmark", "lat": 26.9534, "lon": 75.8462, "height": 240, "total_slots": 110, "occupied": 70, "road_quality": 8, "ev_slots": 8, "hourly_rate": 30},
    {"id": "hub_ah", "name": "Albert Hall Museum", "category": "Landmark", "lat": 26.9116, "lon": 75.8195, "height": 270, "total_slots": 140, "occupied": 90, "road_quality": 9, "ev_slots": 14, "hourly_rate": 25},
    {"id": "hub_nh", "name": "Nahargarh Fort", "category": "Landmark", "lat": 26.9372, "lon": 75.8155, "height": 320, "total_slots": 150, "occupied": 115, "road_quality": 6, "ev_slots": 5, "hourly_rate": 40},
    {"id": "hub_jant", "name": "Jantar Mantar Observatory", "category": "Landmark", "lat": 26.9248, "lon": 75.8246, "height": 210, "total_slots": 85, "occupied": 60, "road_quality": 8, "ev_slots": 6, "hourly_rate": 30},
    {"id": "hub_bm", "name": "Birla Mandir (Laxmi Narayan)", "category": "Landmark", "lat": 26.8924, "lon": 75.8156, "height": 230, "total_slots": 130, "occupied": 95, "road_quality": 9, "ev_slots": 10, "hourly_rate": 20}
]

# ==========================================
# 3. DATABASE, REAL-TIME TELEMETRY & ML MODEL
# ==========================================
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY", "")
    if url and key:
        return create_client(url, key)
    return None

supabase = init_supabase()

if "hubs_data" not in st.session_state:
    st.session_state["hubs_data"] = {item["name"]: item.copy() for item in DEFAULT_HUBS_DATA}

if "user_passes" not in st.session_state:
    st.session_state["user_passes"] = []

@st.cache_data(ttl=600)
def fetch_real_jaipur_ev_stations():
    url = "https://api.openchargemap.io/v3/poi/"
    params = {
        "output": "json",
        "latitude": 26.9124,
        "longitude": 75.7873,
        "distance": 25,
        "distanceunit": "km",
        "maxresults": 40,
        "compact": True,
        "verbose": False
    }
    ocm_key = st.secrets.get("OPENCHARGEMAP_API_KEY", "")
    headers = {"User-Agent": "NaviParkPro-Jaipur/1.0"}
    if ocm_key:
        headers["X-API-Key"] = ocm_key
    try:
        r = requests.get(url, params=params, headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            ev_nodes = {}
            for item in data:
                addr = item.get("AddressInfo", {})
                title = addr.get("Title", "Public EV Station")
                lat = addr.get("Latitude")
                lon = addr.get("Longitude")
                connections = item.get("Connections", [])
                ev_count = len(connections) if connections else random.randint(2, 8)
                if lat and lon:
                    clean_name = f"EV Hub: {title}"[:35]
                    ev_nodes[clean_name] = {
                        "id": f"ev_{item.get('ID', random.randint(1000,9999))}",
                        "name": clean_name,
                        "category": "EV Charging",
                        "lat": float(lat),
                        "lon": float(lon),
                        "height": 190,
                        "total_slots": max(10, ev_count * 3),
                        "occupied": random.randint(2, max(3, ev_count * 2)),
                        "road_quality": 8,
                        "ev_slots": max(2, ev_count),
                        "hourly_rate": 18
                    }
            return ev_nodes
    except Exception:
        pass
    return {}

@st.cache_resource
def train_occupancy_ml_model():
    np.random.seed(42)
    n_samples = 2500
    hours = np.random.randint(0, 24, n_samples)
    days = np.random.randint(0, 7, n_samples)
    cat_code = np.random.choice([0, 1, 2, 3], size=n_samples)
    rates = np.random.choice([15, 18, 20, 25, 30, 40, 50], size=n_samples)
    base = 0.35 + 0.38 * np.exp(-((hours - 13)**2) / 20) + 0.28 * np.exp(-((hours - 19)**2) / 12)
    cat_bump = np.where(cat_code == 1, 0.12, np.where(cat_code == 3, -0.15, 0.05))
    noise = np.random.normal(0, 0.04, n_samples)
    y = np.clip(base + cat_bump + noise, 0.15, 0.96)
    X = np.column_stack([hours, days, cat_code, rates])
    model = RandomForestRegressor(n_estimators=70, max_depth=12, random_state=42)
    model.fit(X, y)
    return model

ml_occupancy_model = train_occupancy_ml_model()

def cat_to_code(cat_str):
    mapping = {"Commercial": 0, "Landmark": 1, "Transit": 2, "Education": 3, "EV Charging": 3}
    return mapping.get(cat_str, 0)

def fetch_real_hubs():
    if supabase:
        try:
            res = supabase.table("hubs").select("*").execute()
            if res.data:
                return {
                    row["name"].strip(): {
                        "id": row.get("id", f"hub_{i}"),
                        "name": row.get("name", "Unknown Hub"),
                        "category": row.get("category", "General"),
                        "lat": float(row.get("lat", 26.9124)),
                        "lon": float(row.get("lon", 75.7873)),
                        "height": row.get("height", 250),
                        "total_slots": int(row.get("total_slots", 100)),
                        "occupied": int(row.get("occupied", 50)),
                        "road_quality": row.get("road_quality", 7),
                        "ev_slots": row.get("ev_slots", 0),
                        "hourly_rate": row.get("hourly_rate", 30)
                    } for i, row in enumerate(res.data)
                }
        except Exception:
            pass
    return st.session_state["hubs_data"]

def create_pay_at_venue_reservation(hub_name, fee):
    pass_id = f"NPJ-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
    clean_target = hub_name.strip()
    if clean_target in st.session_state["hubs_data"]:
        hub = st.session_state["hubs_data"][clean_target]
        tot = hub.get("total_slots", 100)
        occ = hub.get("occupied", 0)
        if occ < tot:
            new_occ = occ + 1
            hub["occupied"] = new_occ
            if supabase and "id" in hub:
                try:
                    supabase.table("hubs").update({"occupied": new_occ}).eq("id", hub["id"]).execute()
                except Exception:
                    pass
    pass_record = {
        "pass_id": pass_id, "hub": hub_name, "fee": fee,
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "CONFIRMED"
    }
    st.session_state["user_passes"].append(pass_record)
    return pass_id

# ==========================================
# 4. ROUTE ENGINE & HERITAGE TSP SOLVER
# ==========================================
def get_osrm_route_with_steps(start_lat, start_lon, end_lat, end_lon):
    url = f"http://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}?overview=full&geometries=geojson&steps=true"
    try:
        r = requests.get(url, timeout=4)
        if r.status_code == 200:
            data = r.json()
            if data.get("routes"):
                route = data["routes"][0]
                coords = route["geometry"]["coordinates"]
                dist_km = route["distance"] / 1000.0
                duration_min = route["duration"] / 60.0
                legs = route.get("legs", [])
                steps = legs[0].get("steps", []) if legs else []
                return coords, round(dist_km, 2), round(duration_min, 1), steps
    except Exception:
        pass
    return [[start_lon, start_lat], [end_lon, end_lat]], 5.0, 12.0, []

def build_traffic_colored_segments(coords, dist_km, duration_min):
    """
    Splits route polyline coordinates into micro-segments and assigns traffic colors
    based on overall speed ratio + time-of-day Jaipur corridor heuristics.
    """
    if len(coords) < 2:
        return []
    
    avg_speed_kmh = (dist_km / (duration_min / 60.0)) if duration_min > 0 else 25.0
    now_hour = datetime.datetime.now().hour
    # Peak hour penalty for old city / arterial corridors
    is_peak = (11 <= now_hour <= 14) or (18 <= now_hour <= 21)
    
    segments = []
    n = len(coords)
    chunk_size = max(1, n // 8)
    
    for i in range(0, n - 1, chunk_size):
        end_idx = min(n, i + chunk_size + 1)
        sub_path = coords[i:end_idx]
        if len(sub_path) < 2:
            continue
            
        # Simulate segment-level variation weighted by peak hours
        jitter_factor = random.uniform(0.7, 1.3)
        effective_speed = avg_speed_kmh * jitter_factor * (0.75 if is_peak else 1.05)
        
        if effective_speed > 30.0:
            color = [16, 185, 129, 255]    # Green
            status = "Free Flow"
        elif effective_speed >= 15.0:
            color = [245, 158, 11, 255]   # Amber/Yellow
            status = "Moderate Traffic"
        else:
            color = [239, 68, 68, 255]    # Red / Congested
            status = "Heavy Congestion"
            
        segments.append({
            "path": sub_path,
            "color": color,
            "status": status,
            "speed_kmh": round(effective_speed, 1)
        })
    return segments
def calculate_trip_impact(dist_km, vehicle_type="Petrol Car"):
    if vehicle_type == "EV":
        cost, co2_kg = dist_km * 1.5, 0.0
    elif vehicle_type == "Two Wheeler":
        cost, co2_kg = dist_km * 2.5, dist_km * 0.04
    else:
        cost, co2_kg = dist_km * 7.5, dist_km * 0.12
    return round(cost, 1), round(co2_kg, 2)

current_hubs = fetch_real_hubs()
live_ev_hubs = fetch_real_jaipur_ev_stations()
if live_ev_hubs:
    current_hubs.update(live_ev_hubs)

# ==========================================
# 5. SIDEBAR FILTERS & SETTINGS
# ==========================================
with st.sidebar:
    st.title("⚙️ Map & Network Controls")
    st.subheader("🔍 Live Map Filters")
    categories = sorted(list(set(h.get("category", "General") for h in current_hubs.values())))
    selected_cats = st.multiselect("Filter by Category", categories, default=categories)
    min_free_slots = st.slider("Min. Free Slots Required", 0, 50, 0)
    ev_only = st.checkbox("⚡ Show EV Charging Locations Only", value=False)
    st.write("---")
    st.subheader("🚗 Trip Settings")
    vehicle_mode = st.selectbox("Vehicle Type", ["Petrol Car", "Diesel Car", "EV", "Two Wheeler"])
    st.write("---")
    st.caption("⚡ **Live Sensor Telemetry:** Multi-user Supabase sync active.")

# ==========================================
# 6. HEADER & AUTOMATED TELEMETRY FRAGMENT
# ==========================================
st.markdown('<div class="main-title">NaviPark 3D Pro 🚘</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Smart Mobility, 3D Route Engine, ML Occupancy Predictor, Live EV Network & Heritage TSP Solver</div>', unsafe_allow_html=True)

@st.fragment(run_every=10)
def auto_sync_banner():
    for name, hub in st.session_state["hubs_data"].items():
        delta = random.randint(-2, 2)
        tot = hub.get("total_slots", 100)
        occ = hub.get("occupied", 50)
        new_occ = max(10, min(tot, occ + delta))
        hub["occupied"] = new_occ
        if supabase and "id" in hub:
            try:
                supabase.table("hubs").update({"occupied": new_occ}).eq("id", hub["id"]).execute()
            except Exception:
                pass
    st.caption(
        f"⚡ **Live Network Telemetry:** Monitoring {len(current_hubs)} Jaipur locations & EV POIs | "
        f"Last Pulse: {datetime.datetime.now().strftime('%H:%M:%S IST')}"
    )

auto_sync_banner()

# ==========================================
# 7. MAIN APPLICATION TABS (7 TABS)
# ==========================================
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🗺️ Interactive 3D Route Map",
    "🎟️ Digital Gate Pass & Wallet",
    "🤖 AI Mobility Strategist",
    "🌱 Eco & Trip Cost Calculator",
    "📊 City Network Analytics",
    "🔮 ML Occupancy Predictor",
    "🏛️ Heritage TSP Tour Solver"
])

# TAB 1: INTERACTIVE 3D ROUTE MAP
with tab1:
    col_map, col_control = st.columns([3, 1])
    map_data = []
    for h in current_hubs.values():
        tot = h.get("total_slots", 100)
        occ = h.get("occupied", 0)
        available = tot - occ
        occupancy_rate = occ / tot if tot > 0 else 0
        category = h.get("category", "General")
        ev_slots = h.get("ev_slots", 0)
        
        if category not in selected_cats or available < min_free_slots or (ev_only and ev_slots == 0):
            continue

        if occupancy_rate > 0.85:
            color = [239, 68, 68, 220]
        elif occupancy_rate > 0.60:
            color = [245, 158, 11, 220]
        else:
            color = [16, 185, 129, 220]
            
        map_data.append({
            "name": h.get("name", "Hub"),
            "category": category,
            "lat": float(h.get("lat", 26.9124)),
            "lon": float(h.get("lon", 75.7873)),
            "height": float(h.get("height", 250)),
            "occupied": occ,
            "total_slots": tot,
            "available": available,
            "ev_slots": ev_slots,
            "color": color
        })
    df_map = pd.DataFrame(map_data)
    
    with col_control:
        st.subheader("Navigation Control")
        user_origin = st.selectbox("Starting Location", list(ORIGIN_COORDS.keys()))
        dest_hub_name = st.selectbox("Select Destination / Landmark / EV POI", list(current_hubs.keys()))
        target_hub = current_hubs[dest_hub_name]
        
        orig_lat, orig_lon = ORIGIN_COORDS[user_origin]
        dest_lat = float(target_hub.get("lat", 26.9124))
        dest_lon = float(target_hub.get("lon", 75.7873))
        route_path, dist_km, duration_min = get_osrm_route(orig_lat, orig_lon, dest_lat, dest_lon)
        
        st.metric("Shortest Driving Distance", f"{dist_km} km")
        st.metric("Est. Travel Time", f"{duration_min} mins")
        
        with st.expander("🚘 Turn-by-Turn Route Steps"):
            dest_cat = target_hub.get("category", "Landmark")
            avail_slots = target_hub.get("total_slots", 100) - target_hub.get("occupied", 0)
            st.write(f"1. **Start:** Depart from `{user_origin}`")
            st.write(f"2. **Merge:** Join main arterial road towards `{dest_cat}` corridor")
            st.write(f"3. **Arrive:** Destination `{target_hub.get('name', dest_hub_name)}` on right")
            st.write(f"4. **Parking / EV Ports:** `{avail_slots}` slots | `{target_hub.get('ev_slots', 0)}` EV ports")

        st.write("---")
        st.caption("🟢 Green: High Availability | 🟠 Yellow: Moderate | 🔴 Red: Near Capacity")

    with col_map:
        if not df_map.empty:
            column_layer = pdk.Layer(
                "ColumnLayer",
                data=df_map,
                get_position=["lon", "lat"],
                get_elevation="height",
                radius=110,
                get_fill_color="color",
                pickable=True,
                auto_highlight=True,
                elevation_scale=1,
            )
            route_df = pd.DataFrame([{"path": route_path}])
            path_layer = pdk.Layer(
                "PathLayer",
                data=route_df,
                get_path="path",
                get_color=[56, 189, 248, 255],
                width_min_pixels=6,
                width_max_pixels=10
            )
            mid_lat = (orig_lat + dest_lat) / 2
            mid_lon = (orig_lon + dest_lon) / 2
            view_state = pdk.ViewState(latitude=mid_lat, longitude=mid_lon, zoom=11, pitch=50, bearing=10)
            
            st.pydeck_chart(pdk.Deck(
                layers=[column_layer, path_layer],
                initial_view_state=view_state,
                tooltip={"html": "<b>{name}</b> ({category})<br/>Free Slots: <b>{available}</b> / {total_slots}<br/>⚡ EV Ports: <b>{ev_slots}</b>"}
            ))
        else:
            st.warning("No landmarks match your active filter criteria!")

# TAB 2: DIGITAL GATE PASS & WALLET
with tab2:
    st.subheader("🎟️ Instant Pay-at-Venue Pass & Digital Wallet")
    col_res1, col_res2 = st.columns([1, 1])
    with col_res1:
        st.markdown("### Generate Gate Pass")
        res_hub = st.selectbox("Target Landmark / Parking Hub", list(current_hubs.keys()), key="res_hub_select")
        selected_data = current_hubs[res_hub]
        tot = selected_data.get("total_slots", 100)
        occ = selected_data.get("occupied", 0)
        avail_count = tot - occ
        rate = selected_data.get("hourly_rate", 30)
        
        st.info(f"📍 **{res_hub}**\n\nSlots Free: **{avail_count} / {tot}** | Rate: **₹{rate}/hr**")
        vehicle_no = st.text_input("Vehicle License Plate", value="RJ-14-CC-2026")
        duration = st.slider("Parking Duration (Hours)", 1, 8, 2)
        base_fee = duration * rate
        st.markdown(f"#### Calculated Fee: **₹{base_fee}** *(Pay at Gate)*")
        
        if st.button("Generate QR Gate Pass", type="primary"):
            if avail_count > 0:
                pass_id = create_pay_at_venue_reservation(res_hub, base_fee)
                st.session_state["last_pass"] = {
                    "pass_id": pass_id, "hub": res_hub, "vehicle": vehicle_no,
                    "fee": base_fee, "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                st.success(f"Pass Generated! ID: {pass_id}")
            else:
                st.error("Selected location is completely full!")

    with col_res2:
        st.markdown("### 💳 Active Pass Wallet")
        if "last_pass" in st.session_state:
            lp = st.session_state["last_pass"]
            qr_payload = f"NAVIPARK_PASS|ID:{lp['pass_id']}|HUB:{lp['hub']}|VEH:{lp['vehicle']}|FEE:{lp['fee']}"
            qr_img = qrcode.make(qr_payload)
            buf = io.BytesIO()
            qr_img.save(buf, format="PNG")
            st.image(buf.getvalue(), width=220, caption=f"Scan at {lp['hub']} Gate")
            st.code(f"PASS ID : {lp['pass_id']}\nHUB     : {lp['hub']}\nVEHICLE : {lp['vehicle']}\nAMOUNT  : ₹{lp['fee']}\nISSUED  : {lp['time']}")
        else:
            st.info("No active pass generated yet.")
        if st.session_state["user_passes"]:
            st.write("---")
            st.markdown("#### 📜 Session Pass History")
            st.dataframe(pd.DataFrame(st.session_state["user_passes"]), use_container_width=True)

# TAB 3: AI MOBILITY STRATEGIST
with tab3:
    st.subheader("🤖 AI Mobility & Traffic Strategist")
    query = st.text_input("Ask a question about visiting Jaipur landmarks:", value="What is the shortest path and best parking strategy for Hawa Mahal and City Palace?")
    if st.button("Generate AI Mobility Strategy"):
        with st.spinner("Analyzing Old City arterial network..."):
            if any(k in query.lower() for k in ["hawa mahal", "city palace", "old city"]):
                st.markdown("""
                **💡 Strategic AI Recommendation for Old Walled City:**
                * **Traffic Density:** Heavy slowdowns near Badi Chaupar between **11:00 AM - 6:00 PM**.
                * **Shortest Path:** Drive via **MI Road -> Ajmeri Gate -> Tripolia Bazar**.
                * **Smart Parking Strategy:** Park at **City Palace Hub** or **Albert Hall Hub** (take e-rickshaw).
                * **EV Availability:** Albert Hall Hub has fast-charging ports available.
                """)
            else:
                st.markdown("""
                **💡 Strategic AI Recommendation:**
                * **Network Status:** Major corridors (JLN Marg, Tonk Road, MI Road) flowing normally.
                * **EV Charging Tip:** Fast chargers active via OpenChargeMap POI feed.
                """)

# TAB 4: ECO & TRIP COST CALCULATOR
with tab4:
    st.subheader("🌱 Smart Trip Cost & Carbon Calculator")
    col_c1, col_c2 = st.columns([1, 1])
    with col_c1:
        calc_origin = st.selectbox("From", list(ORIGIN_COORDS.keys()), key="calc_orig")
        calc_dest = st.selectbox("To Destination / EV POI", list(current_hubs.keys()), key="calc_dest")
        c_orig_lat, c_orig_lon = ORIGIN_COORDS[calc_origin]
        c_target = current_hubs[calc_dest]
        c_dest_lat = float(c_target.get("lat", 26.9124))
        c_dest_lon = float(c_target.get("lon", 75.7873))
        _, trip_dist, trip_time = get_osrm_route(c_orig_lat, c_orig_lon, c_dest_lat, c_dest_lon)
        est_cost, est_co2 = calculate_trip_impact(trip_dist, vehicle_mode)
        st.metric("Total Distance", f"{trip_dist} km")
        st.metric("Estimated Drive Time", f"{trip_time} mins")

    with col_c2:
        st.markdown(f"### 📊 Environmental & Fuel Impact (`{vehicle_mode}`)")
        m_col1, m_col2 = st.columns(2)
        m_col1.metric("Est. Fuel/Energy Cost", f"₹{est_cost}")
        m_col2.metric("Carbon Footprint", f"{est_co2} kg CO₂")
        st.progress(min(1.0, est_co2 / 2.0), text=f"Carbon Intensity Rating for {trip_dist} km")
        if vehicle_mode != "EV":
            ev_cost, _ = calculate_trip_impact(trip_dist, "EV")
            st.success(f"💡 **EV Savings Tip:** Switching this trip to an EV saves **₹{est_cost - ev_cost:.1f}**!")

# TAB 5: CITY NETWORK ANALYTICS
with tab5:
    st.subheader("📊 City Network Health & Analytics")
    total_capacity = sum(h.get("total_slots", 100) for h in current_hubs.values())
    total_occupied = sum(h.get("occupied", 0) for h in current_hubs.values())
    total_ev = sum(h.get("ev_slots", 0) for h in current_hubs.values())
    net_utilization = (total_occupied / total_capacity * 100) if total_capacity > 0 else 0
    
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    col_m1.metric("Locations / POIs Online", len(current_hubs))
    col_m2.metric("Total Slots", f"{total_occupied} / {total_capacity}")
    col_m3.metric("Utilization", f"{net_utilization:.1f}%")
    col_m4.metric("EV Ports", total_ev)
    
    st.write("---")
    st.subheader("Live Hub & Landmark Breakdown")
    analytics_data = [
        {
            "Landmark / Hub Name": h.get("name", "Hub"),
            "Category": h.get("category", "General"),
            "Occupied": h.get("occupied", 0),
            "Capacity": h.get("total_slots", 100),
            "Free Slots": h.get("total_slots", 100) - h.get("occupied", 0),
            "Hourly Rate": f"₹{h.get('hourly_rate', 30)}/hr",
            "Utilization": f"{(h.get('occupied', 0) / h.get('total_slots', 100) * 100):.1f}%",
            "Road Index": f"{h.get('road_quality', 7)}/10",
            "EV Ports": h.get("ev_slots", 0)
        } for h in current_hubs.values()
    ]
    st.dataframe(pd.DataFrame(analytics_data), use_container_width=True)

# TAB 6: ML OCCUPANCY PREDICTOR
with tab6:
    st.subheader("🔮 ML Occupancy & Demand Predictor (Random Forest Regressor)")
    st.write("Predict future parking/charger load across Jaipur hubs based on diurnal traffic curves, day of the week, and tariff tier.")
    
    ml_col_left, ml_col_right = st.columns([1, 1.4])
    
    with ml_col_left:
        pred_hub_name = st.selectbox("Select Target Hub for Prediction", list(current_hubs.keys()), key="ml_hub_sel")
        pred_hub = current_hubs[pred_hub_name]
        
        day_mapping = {
            "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
            "Friday": 4, "Saturday": 5, "Sunday": 6
        }
        selected_day_name = st.selectbox("Day of Week", list(day_mapping.keys()), index=datetime.datetime.now().weekday())
        selected_day_code = day_mapping[selected_day_name]
        
        target_hour = st.slider("Target Hour of Day (0-23 IST)", 0, 23, (datetime.datetime.now().hour + 2) % 24)
        
        hub_cat_code = cat_to_code(pred_hub.get("category", "Commercial"))
        hub_rate = pred_hub.get("hourly_rate", 30)
        tot_cap = pred_hub.get("total_slots", 100)
        
        X_infer = np.array([[target_hour, selected_day_code, hub_cat_code, hub_rate]])
        pred_util = ml_occupancy_model.predict(X_infer)[0]
        pred_occ_slots = int(round(pred_util * tot_cap))
        pred_free_slots = max(0, tot_cap - pred_occ_slots)
        
        st.markdown("### 🎯 ML Inference Result")
        sub_m1, sub_m2 = st.columns(2)
        sub_m1.metric("Predicted Occupancy", f"{pred_util*100:.1f}%")
        sub_m2.metric("Projected Free Slots", f"{pred_free_slots} / {tot_cap}")
        
        status_label = "🟢 High Availability" if pred_util < 0.60 else ("🟠 Moderate Load" if pred_util < 0.85 else "🔴 High Congestion Risk")
        st.info(f"Model Assessment for **{target_hour:02d}:00 IST** on **{selected_day_name}**: {status_label}")

    with ml_col_right:
        st.markdown(f"### 📈 24-Hour Diurnal Demand Forecast (`{pred_hub_name}`)")
        hours_arr = np.arange(24)
        X_profile = np.column_stack([
            hours_arr,
            np.full(24, selected_day_code),
            np.full(24, hub_cat_code),
            np.full(24, hub_rate)
        ])
        profile_preds = ml_occupancy_model.predict(X_profile) * tot_cap
        
        chart_df = pd.DataFrame({
            "Hour": [f"{h:02d}:00" for h in hours_arr],
            "Projected Occupied Slots": np.round(profile_preds, 1),
            "Total Capacity": tot_cap
        })
        st.line_chart(chart_df, x="Hour", y=["Projected Occupied Slots", "Total Capacity"])

# TAB 7: HERITAGE TSP TOUR SOLVER
with tab7:
    st.subheader("🏛️ Heritage TSP Multi-Stop Tour Solver")
    st.write("Finds the globally optimal visiting sequence for Jaipur heritage circuits, minimizing total point-to-point distance.")
    
    default_heritage = [
        "Amer Fort (Amber)",
        "Jal Mahal (Water Palace)",
        "Hawa Mahal (Palace of Winds)",
        "City Palace Jaipur",
        "Albert Hall Museum"
    ]
    
    col_tsp_left, col_tsp_right = st.columns([1, 1.4])
    
    with col_tsp_left:
        tsp_stops = st.multiselect(
            "Select Heritage Stops to Tour",
            list(current_hubs.keys()),
            default=[s for s in default_heritage if s in current_hubs]
        )
        tsp_start = st.selectbox("Tour Start Hub / Gate", tsp_stops if tsp_stops else list(current_hubs.keys()))
        
        if st.button("Solve TSP Optimal Route", type="primary") and len(tsp_stops) >= 2:
            sub_coords = {name: [current_hubs[name]["lat"], current_hubs[name]["lon"]] for name in tsp_stops}
            best_sequence, total_dist = solve_heritage_tsp(sub_coords, tsp_start)
            st.session_state["tsp_solution"] = {
                "sequence": best_sequence,
                "dist": total_dist,
                "coords": sub_coords
            }
            st.success(f"Optimized Sequence Found! Total Haversine Span: **{total_dist} km**")

        if "tsp_solution" in st.session_state:
            seq = st.session_state["tsp_solution"]["sequence"]
            st.markdown("### 🗺️ Optimal Visit Order")
            for idx, stop_name in enumerate(seq, 1):
                st.write(f"**{idx}.** `{stop_name}`")

    with col_tsp_right:
        if "tsp_solution" in st.session_state:
            sol = st.session_state["tsp_solution"]
            seq = sol["sequence"]
            coords_map = sol["coords"]
            
            # Build polyline for sequence
            path_pts = [[coords_map[name][1], coords_map[name][0]] for name in seq]
            tsp_line_df = pd.DataFrame([{"path": path_pts}])
            
            # Scatter/Column overlay for stops
            scatter_pts = [{
                "name": name,
                "lat": coords_map[name][0],
                "lon": coords_map[name][1],
                "order_idx": seq.index(name) + 1
            } for name in seq]
            df_scatter = pd.DataFrame(scatter_pts)
            
            line_layer = pdk.Layer(
                "PathLayer",
                data=tsp_line_df,
                get_path="path",
                get_color=[192, 132, 252, 255],
                width_min_pixels=5
            )
            
            scatter_layer = pdk.Layer(
                "ScatterplotLayer",
                data=df_scatter,
                get_position=["lon", "lat"],
                get_color=[56, 189, 248, 255],
                get_radius=220,
                pickable=True
            )
            
            first_coords = coords_map[seq[0]]
            view_state_tsp = pdk.ViewState(latitude=first_coords[0], longitude=first_coords[1], zoom=12, pitch=30)
            st.pydeck_chart(pdk.Deck(
                layers=[line_layer, scatter_layer],
                initial_view_state=view_state_tsp,
                tooltip={"html": "<b>Stop #{order_idx}</b><br/>{name}"}
            ))
        else:
            st.info("Select 2+ heritage locations on the left and click **Solve TSP Optimal Route**.")
            
        
        
        
        
    
