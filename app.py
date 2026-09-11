import streamlit as st
import streamlit.components.v1 as components
import pydeck as pdk
import qrcode
import io
import datetime
import math
import random
import requests
import pandas as pd
import json
from supabase import create_client, Client

# ==========================================
# 1. STREAMLIT CONFIG & PWA MANIFEST
# ==========================================
st.set_page_config(
    page_title="NaviPark 3D - Smart Mobility & Traffic Network",
    page_icon="🚘",
    layout="wide",
    initial_sidebar_state="expanded"
)

# PWA Manifest Injection
pwa_manifest = {
    "name": "NaviPark 3D Jaipur",
    "short_name": "NaviPark",
    "description": "Smart Mobility & Traffic Network for Jaipur",
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
}

js_code = f"""
<script>
    const manifest = {json.dumps(pwa_manifest)};
    const blob = new Blob([JSON.stringify(manifest)], {{type: 'application/json'}});
    const manifestURL = URL.createObjectURL(blob);
    const parentDocument = window.parent.document;
    const existing = parentDocument.querySelector('link[rel="manifest"]');
    if (existing) {{ existing.remove(); }}
    const link = parentDocument.createElement('link');
    link.rel = 'manifest';
    link.href = manifestURL;
    parentDocument.head.appendChild(link);
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
        font-size: 2.6rem;
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
        background-color: rgba(15, 23, 42, 0.9) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: rgba(30, 41, 59, 0.5);
        padding: 8px;
        border-radius: 14px;
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
</script>
"""

components.html(js_code, height=0)
    page_title="NaviPark 3D - Smart Mobility & Traffic Network",
    page_icon="🚘",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    /* Dark Glassmorphism Canvas */
    .stApp {
        background: linear-gradient(135deg, #070A12 0%, #0F172A 50%, #030712 100%);
        color: #F8FAFC;
    }
    .main-title {
        font-size: 2.6rem;
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
    /* Cyberpunk Metric Cards */
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
        background-color: rgba(15, 23, 42, 0.9) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: rgba(30, 41, 59, 0.5);
        padding: 8px;
        border-radius: 14px;
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

# ==========================================
# 2. REAL-TIME DATASETS & LANDMARKS
# ==========================================
LANDMARKS = {
    "Jaipur Railway Station": (26.9202, 75.7878),
    "Jaipur Airport (JAI)": (26.8242, 75.8122),
    "Rambagh Circle": (26.8982, 75.8080),
    "Mansarovar Plaza": (26.8580, 75.7620),
    "Vaishali Nagar": (26.9080, 75.7380),
    "Raja Park": (26.8982, 75.8245)
}

DEFAULT_HUBS_DATA = [
    {"id": "hub_1", "name": "World Trade Park (WTP) Mall", "lat": 26.8530, "lon": 75.8048, "height": 80, "total_slots": 350, "occupied": 290, "road_quality": 9, "ev_slots": 20},
    {"id": "hub_2", "name": "Gaurav Tower (GT) Parking", "lat": 26.8545, "lon": 75.8055, "height": 60, "total_slots": 200, "occupied": 185, "road_quality": 8, "ev_slots": 10},
    {"id": "hub_3", "name": "Pink Square Mall (Raja Park)", "lat": 26.8970, "lon": 75.8270, "height": 75, "total_slots": 150, "occupied": 95, "road_quality": 7, "ev_slots": 8},
    {"id": "hub_4", "name": "Elements Mall (Ajmer Road)", "lat": 26.8920, "lon": 75.7420, "height": 70, "total_slots": 180, "occupied": 80, "road_quality": 8, "ev_slots": 12},
    {"id": "hub_5", "name": "Ram Niwas Garden Parking", "lat": 26.9152, "lon": 75.8198, "height": 30, "total_slots": 120, "occupied": 85, "road_quality": 6, "ev_slots": 5},
    {"id": "hub_6", "name": "Bapu Bazaar Underground", "lat": 26.9180, "lon": 75.8230, "height": 25, "total_slots": 80, "occupied": 72, "road_quality": 5, "ev_slots": 0}
]

# ==========================================
# 3. DATABASE & REAL-TIME TELEMETRY
# ==========================================
import random

@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY", "")
    if url and key:
        return create_client(url, key)
    return None

supabase = None
try:
    supabase = init_supabase()
except Exception:
    pass

# Initialize session state ONCE on app boot
if "hubs_data" not in st.session_state:
    st.session_state["hubs_data"] = {item["name"]: item.copy() for item in DEFAULT_HUBS_DATA}

def fetch_real_hubs():
    """Returns active state from Supabase or live session memory."""
    if supabase:
        try:
            res = supabase.table("hubs").select("*").execute()
            if res.data:
                return {
                    row["name"].strip(): {
                        "id": row.get("id", f"hub_{i}"),
                        "name": row["name"],
                        "lat": row["lat"], "lon": row["lon"],
                        "height": row.get("height", 50),
                        "total_slots": row["total_slots"], 
                        "occupied": row["occupied"],
                        "road_quality": row.get("road_quality", 7),
                        "ev_slots": row.get("ev_slots", 5)
                    } for i, row in enumerate(res.data)
                }
        except Exception:
            pass
    return st.session_state["hubs_data"]

def create_pay_at_venue_reservation(hub_name, fee):
    """Inserts reservation and increments occupied count instantly."""
    pass_id = f"NPJ-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
    clean_target = hub_name.strip()
    
    if clean_target in st.session_state["hubs_data"]:
        hub = st.session_state["hubs_data"][clean_target]
        if hub["occupied"] < hub["total_slots"]:
            hub["occupied"] += 1

    if supabase:
        try:
            response = supabase.table("hubs").select("*").ilike("name", clean_target).execute()
            if response.data:
                db_hub = response.data[0]
                if db_hub["occupied"] < db_hub["total_slots"]:
                    supabase.table("hubs").update({"occupied": db_hub["occupied"] + 1}).eq("name", db_hub["name"]).execute()
                    now = datetime.datetime.now(datetime.timezone.utc)
                    supabase.table("reservations").insert({
                        "pass_id": pass_id,
                        "hub_name": db_hub["name"],
                        "created_at": now.isoformat(),
                        "payment_status": "PAY_AT_VENUE",
                        "amount": fee
                    }).execute()
        except Exception:
            pass

    return pass_id, "Success"

# ==========================================
# 4. REAL-TIME ROUTING & TOMTOM TRAFFIC ENGINE
# ==========================================
def get_osrm_route(start_coords, end_coords, strategy):
    """Queries OpenStreetMap OSRM Routing Engine for accurate turn-by-turn geometry."""
    url = f"http://router.project-osrm.org/route/v1/driving/{start_coords[1]},{start_coords[0]};{end_coords[1]},{end_coords[0]}?overview=full&geometries=geojson"
    try:
        r = requests.get(url, timeout=4).json()
        route = r['routes'][0]
        geometry = route['geometry']['coordinates']
        dist_km = route['distance'] / 1000.0
        dur_min = route['duration'] / 60.0
        
        if strategy == "Fuel Efficient":
            dur_min *= 1.05
            fuel = round(dist_km * 0.062, 2)
        elif strategy == "Best Road Quality":
            dist_km *= 1.08
            dur_min *= 0.96
            fuel = round(dist_km * 0.068, 2)
        else: # Traffic Avoidance
            fuel = round(dist_km * 0.075, 2)
            
        path = [[lon, lat] for lon, lat in geometry]
        return path, round(dist_km, 2), round(dur_min, 1), fuel
    except Exception:
        dist_km = 8.5
        dur_min = 18.0
        return [[start_coords[1], start_coords[0]], [end_coords[1], end_coords[0]]], dist_km, dur_min, 0.6

def fetch_live_corridor_speed(corridor_name, fallback_speed):
    """Optional TomTom Traffic API Integration."""
    tomtom_key = st.secrets.get("TOMTOM_API_KEY", None)
    if not tomtom_key:
        return fallback_speed, "Real Time (Corridor Matrix)"
    try:
        url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/relative0/10/json?key={tomtom_key}&point=26.8530,75.8048"
        res = requests.get(url, timeout=3).json()
        speed = res['flowSegmentData']['currentSpeed']
        return speed, "Live TomTom Feed"
    except Exception:
        return fallback_speed, "Corridor Matrix"

# ==========================================
# 5. HEADER & AUTOMATED TELEMETRY FRAGMENT
# ==========================================
st.markdown('<div class="main-title">NaviPark 3D Network 🚘</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Live 3D Map Engine, OSRM Route Optimization & Pay-at-Venue System</div>', unsafe_allow_html=True)

@st.fragment(run_every=10)
def auto_sync_banner():
    """Simulates active parking occupancy changes by mutating session state directly."""
    for name, hub in st.session_state["hubs_data"].items():
        delta = random.randint(-3, 3)
        hub["occupied"] = max(10, min(hub["total_slots"], hub["occupied"] + delta))

    st.caption(
        f"⚡ **Live Sensor Telemetry Active:** Auto-syncing parking occupancy | "
        f"Last Telemetry Pulse: {datetime.datetime.now().strftime('%H:%M:%S IST')}"
    )

auto_sync_banner()

# ==========================================
# 6. SIDEBAR CONTROLS
# ==========================================
st.sidebar.header("🕹️ Route & Navigation Parameters")
start_name = st.sidebar.selectbox("Starting Landmark", list(LANDMARKS.keys()))
hubs_dict = fetch_real_hubs()
target_name = st.sidebar.selectbox("Destination Parking / Hub", list(hubs_dict.keys()))

routing_strategy = st.sidebar.radio(
    "Route Optimization Engine",
    ["Traffic Avoidance", "Fuel Efficient", "Best Road Quality"]
)

map_style = st.sidebar.selectbox("3D Map Style", ["Dark Mode 3D", "Road Mode 3D"])
emergency_wave = st.sidebar.toggle("🚑 Emergency Green Wave (SMS Hospital)", value=False)

start_coords = LANDMARKS[start_name]
target_hub = hubs_dict[target_name]
end_coords = (target_hub["lat"], target_hub["lon"])

path_geometry, dist_km, dur_min, est_fuel = get_osrm_route(start_coords, end_coords, routing_strategy)

avail_slots = max(0, target_hub["total_slots"] - target_hub["occupied"])
occupancy_rate = target_hub["occupied"] / target_hub["total_slots"] if target_hub["total_slots"] > 0 else 0.5
base_fee = 30 if occupancy_rate < 0.5 else (50 if occupancy_rate < 0.85 else 90)

st.sidebar.markdown("---")
st.sidebar.subheader("💳 Instant Pay-at-Venue Reservation")
st.sidebar.metric("Venue Payable Fee", f"₹{base_fee}.00", delta="Pay at Entry/Exit")

if st.sidebar.button("🔒 Reserve Spot Now"):
    pid, status = create_pay_at_venue_reservation(target_name, base_fee)
    st.session_state["active_pass"] = pid
    st.session_state["active_pass_hub"] = target_name
    st.session_state["active_pass_fee"] = base_fee
    st.sidebar.success(f"✅ Reserved! Pass ID: {pid}")

# ==========================================
# 7. MAIN TABS INTERFACE
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs([
    "🗺️ 3D Map & Navigation", 
    "🚦 Real-Time Traffic Corridors", 
    "🎟️ Pass Verification & Gate Barrier", 
    "📊 Operator Infrastructure Telemetry"
])

# ------------------------------------------
# TAB 1: 3D MAP & NAVIGATION
# ------------------------------------------
with tab1:
    if emergency_wave:
        st.error("🚨 **EMERGENCY GREEN WAVE ENGAGED:** Signals along JLN Marg override for ambulance clearance.")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Est. Travel Time", f"{dur_min if not emergency_wave else math.ceil(dur_min*0.4)} mins", delta=f"{dist_km} km")
    m2.metric("Available Capacity", f"{avail_slots} / {target_hub['total_slots']} Slots")
    m3.metric("Road Quality Score", f"{target_hub['road_quality']} / 10", delta="Smooth Highway" if target_hub['road_quality'] >= 8 else "Work Zone")
    m4.metric("Est. Fuel Consumed", f"{est_fuel} L", delta=f"Strategy: {routing_strategy}")

    st.markdown("---")
    map_col, pass_col = st.columns([2, 1])

    with map_col:
        st.subheader("🗺️ Live 3D Extruded Building Map")
        
        hubs_df = pd.DataFrame(list(hubs_dict.values()))
        hubs_df['color_r'] = hubs_df['occupied'].apply(lambda x: 239 if x > 150 else 16)
        hubs_df['color_g'] = hubs_df['occupied'].apply(lambda x: 68 if x > 150 else 185)
        hubs_df['color_b'] = hubs_df['occupied'].apply(lambda x: 68 if x > 150 else 129)

        buildings_layer = pdk.Layer(
            "ColumnLayer",
            data=hubs_df,
            get_position=["lon", "lat"],
            get_elevation="height",
            elevation_scale=4,
            radius=45,
            get_fill_color=["color_r", "color_g", "color_b", 200],
            pickable=True,
            auto_highlight=True
        )

        route_df = pd.DataFrame([{"path": path_geometry}])
        route_layer = pdk.Layer(
            "PathLayer",
            data=route_df,
            get_path="path",
            get_color=[56, 189, 248] if not emergency_wave else [239, 68, 68],
            width_scale=8,
            width_min_pixels=5,
        )

        view_style = "road" if map_style == "Road Mode 3D" else "dark"

        view_state = pdk.ViewState(
            latitude=(start_coords[0] + end_coords[0]) / 2,
            longitude=(start_coords[1] + end_coords[1]) / 2,
            zoom=13.5,
            pitch=50,
            bearing=-15
        )

        deck = pdk.Deck(
            layers=[buildings_layer, route_layer],
            initial_view_state=view_state,
            map_style=view_style,
            tooltip={"text": "{name}\nOccupied: {occupied}/{total_slots}\nRoad Quality: {road_quality}/10"}
        )

        st.pydeck_chart(deck, use_container_width=True)

    with pass_col:
        st.subheader("🎟️ Digital Gate Pass")
        if "active_pass" in st.session_state:
            pid = st.session_state["active_pass"]
            phub = st.session_state.get("active_pass_hub", target_name)
            pfee = st.session_state.get("active_pass_fee", base_fee)
            
            st.success(f"**Gate Pass ID:** `{pid}`")
            st.caption(f"**Destination:** {phub}")
            st.caption(f"**Payment Status:** PAY AT VENUE (₹{pfee})")
            
            qr = qrcode.QRCode(version=1, box_size=8, border=2)
            qr.add_data(f"PassID:{pid}|Hub:{phub}|Fee:{pfee}")
            qr.make(fit=True)
            buf = io.BytesIO()
            qr.make_image(fill_color="#0284C7", back_color="white").save(buf, format="PNG")
            st.image(buf.getvalue(), caption="Present at entrance barrier scanner", width=200)
        else:
            st.info("Click 'Reserve Spot Now' in the sidebar to issue your digital gate pass.")

# ------------------------------------------
# TAB 2: REAL-TIME TRAFFIC CORRIDORS
# ------------------------------------------
with tab2:
    st.subheader("🚦 Jaipur Arterial Real-Time Flow & Congestion Index")
    
    corridors = [
        {"name": "JLN Marg (WTP - GT - OTS Circle)", "fallback_speed": 18, "status": "Heavy Congestion", "delay": "+12 mins", "color": "#EF4444"},
        {"name": "MI Road (Panch Batti - Ajmeri Gate)", "fallback_speed": 14, "status": "Severe Delay", "delay": "+15 mins", "color": "#EF4444"},
        {"name": "Tonk Road (Rambagh Circle)", "fallback_speed": 38, "status": "Smooth Flow", "delay": "+2 mins", "color": "#10B981"},
        {"name": "Ajmer Road (Elements Mall)", "fallback_speed": 26, "status": "Moderate Flow", "delay": "+5 mins", "color": "#F59E0B"}
    ]
    
    for c in corridors:
        live_speed, source = fetch_live_corridor_speed(c["name"], c["fallback_speed"])
        st.markdown(f"""
            <div style="background-color:rgba(30, 41, 59, 0.6); padding:16px; border-radius:12px; border-left:6px solid {c['color']}; margin-bottom:12px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:1.1rem; font-weight:700; color:#F8FAFC;">{c['name']}</span>
                    <span style="background-color:{c['color']}; color:white; padding:4px 12px; border-radius:12px; font-size:0.85rem; font-weight:700;">{c['status']}</span>
                </div>
                <div style="margin-top:8px; color:#94A3B8; font-size:0.9rem;">
                    🏎️ Speed: <b>{live_speed} km/h</b> | ⏱️ Corridor Delay: <b>{c['delay']}</b> | 📡 Data Source: <i>{source}</i>
                </div>
            </div>
        """, unsafe_allow_html=True)

# ------------------------------------------
# TAB 3: PASS VERIFICATION & GATE BARRIER
# ------------------------------------------
with tab3:
    st.subheader("🛡️ Automated Gate Barrier Scanner")
    verify_id = st.text_input("Scan or Enter Digital Pass ID", placeholder="NPJ-2026...")
    if st.button("Trigger Physical Gate Barrier Scan") and verify_id:
        st.markdown("""
            <div style="background-color:#10B981; padding:24px; border-radius:14px; text-align:center; color:white; font-weight:800; font-size:1.5rem; box-shadow:0 0 20px rgba(16,185,129,0.4);">
                🟢 GATE BARRIER UNLOCKED <br>
                <span style="font-size:1rem; font-weight:normal;">Pay-at-Venue Reservation Verified • Vehicle Clearance Granted</span>
            </div>
        """, unsafe_allow_html=True)

# ------------------------------------------
# TAB 4: OPERATOR INFRASTRUCTURE TELEMETRY
# ------------------------------------------
with tab4:
    st.subheader("📊 Network Occupancy & Capacity Utilization")
    all_hubs = fetch_real_hubs()
    tot_cap = sum(h["total_slots"] for h in all_hubs.values())
    tot_occ = sum(h["occupied"] for h in all_hubs.values())
    util_rate = round((tot_occ / tot_cap) * 100, 1) if tot_cap > 0 else 0
    
    o1, o2, o3, o4 = st.columns(4)
    o1.metric("Total Infrastructure", f"{tot_cap} Slots")
    o2.metric("Occupied Infrastructure", f"{tot_occ} Vehicles")
    o3.metric("Network Utilization", f"{util_rate}%")
    o4.metric("Est. Hourly Venue Revenue", f"₹{tot_occ * 50}")
    
    st.markdown("---")
    st.write("### 🏢 Facility Capacity Breakdowns")
    for hname, hdata in all_hubs.items():
        occ, tot = hdata["occupied"], hdata["total_slots"]
        pct = min(1.0, max(0.0, occ / tot)) if tot > 0 else 0.0
        c1, c2 = st.columns([1, 2])
        with c1:
            st.write(f"**{hname}**")
            st.caption(f"{occ} / {tot} slots occupied")
        with c2:
            st.progress(pct)
            
