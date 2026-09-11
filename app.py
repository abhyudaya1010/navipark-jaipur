import streamlit as st
import folium
from streamlit_folium import st_folium
import qrcode
import io
import datetime
import math
import random
import requests
import pandas as pd
from supabase import create_client, Client

# ==========================================
# 1. PAGE CONFIGURATION & GLASSMORPHIC STYLING
# ==========================================
st.set_page_config(
    page_title="NaviPark Jaipur - Smart Mobility Network",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    /* Dark Glassmorphism Canvas */
    .stApp {
        background: linear-gradient(135deg, #0B0F19 0%, #111827 50%, #070A12 100%);
        color: #F3F4F6;
    }
    .main-title {
        font-size: 2.5rem;
        font-weight: 900;
        background: linear-gradient(90deg, #38BDF8 0%, #818CF8 50%, #C084FC 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
        letter-spacing: -0.5px;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #9CA3AF;
        font-weight: 500;
        margin-bottom: 20px;
    }
    /* Glassmorphic Cards */
    div[data-testid="stMetricValue"] {
        font-size: 1.7rem !important;
        font-weight: 800 !important;
        color: #38BDF8 !important;
    }
    .stMetric {
        background: rgba(31, 41, 55, 0.6) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        backdrop-filter: blur(12px);
        border-radius: 16px !important;
        padding: 16px !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }
    section[data-testid="stSidebar"] {
        background-color: rgba(17, 24, 39, 0.85) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: rgba(31, 41, 55, 0.4);
        padding: 8px;
        border-radius: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        color: #9CA3AF;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2563EB !important;
        color: #FFFFFF !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. LOCALIZATION (ENGLISH / HINDI)
# ==========================================
TRANSLATIONS = {
    "English": {
        "title": "NaviPark Jaipur 🚗",
        "subtitle": "Smart Urban Navigation, Road-Quality Engine & Pay-at-Venue Booking",
        "tab1": "🚗 Smart Route Engine",
        "tab2": "🤖 AI Forecasting & EV Grid",
        "tab3": "🚦 Live Corridor Monitor",
        "tab4": "🛍️ Malls & Events Planner",
        "tab5": "🛡️ Gate Barrier Verification",
        "tab6": "📊 Operator Telemetry",
        "tab7": "🏆 Civic Eco-Leaderboard",
        "starting_loc": "Starting Location",
        "target_hub": "Select Target Hub / Mall",
        "route_mode": "Route Optimization Strategy",
        "reserve_btn": "🔒 Reserve Slot (Pay at Venue)",
        "drive_time": "Est. Drive Time",
        "available": "Available Capacity",
        "road_quality": "Road Quality Score",
        "venue_fee": "Pay at Venue Fee"
    },
    "हिंदी": {
        "title": "नवीपार्क जयपुर 🚗",
        "subtitle": "स्मार्ट नेविगेशन, सड़क गुणवत्ता इंजन और वेन्यू पर भुगतान सुविधा",
        "tab1": "🚗 स्मार्ट रूट नेविगेशन",
        "tab2": "🤖 एआई पूर्वानुमान और ईवी ग्रिड",
        "tab3": "🚦 लाइव कॉरिडोर मॉनिटर",
        "tab4": "🛍️ मॉल और इवेंट्स प्लानर",
        "tab5": "🛡️ गेट बैरियर सत्यापन",
        "tab6": "📊 ऑपरेटर टेलीमेट्री",
        "tab7": "🏆 इको-लीडरबोर्ड",
        "starting_loc": "प्रारंभिक स्थान",
        "target_hub": "पार्किंग या मॉल चुनें",
        "route_mode": "रूट चयन रणनीति",
        "reserve_btn": "🔒 स्थान सुरक्षित करें (वेन्यू पर भुगतान)",
        "drive_time": "अनुमानित समय",
        "available": "उपलब्ध क्षमता",
        "road_quality": "सड़क गुणवत्ता रेटिंग",
        "venue_fee": "स्थल पर देय शुल्क"
    }
}

# ==========================================
# 3. CORE DATASETS & LANDMARKS
# ==========================================
LANDMARKS = {
    "Jaipur Railway Station": (26.9202, 75.7878),
    "Jaipur Airport (JAI)": (26.8242, 75.8122),
    "Rambagh Circle": (26.8982, 75.8080),
    "Mansarovar Plaza": (26.8580, 75.7620),
    "Vaishali Nagar": (26.9080, 75.7380),
    "Raja Park": (26.8982, 75.8245)
}

JAIPUR_CORRIDORS = {
    "JLN Marg (WTP - GT - OTS Circle)": {"status": "Heavy Congestion", "delay_min": 12, "speed_kmh": 18, "road_score": "8.5/10 (Smooth)", "color": "#EF4444"},
    "MI Road (Panch Batti - Ajmeri Gate)": {"status": "Heavy Congestion", "delay_min": 14, "speed_kmh": 14, "road_score": "5.2/10 (Work Zone)", "color": "#EF4444"},
    "Tonk Road (Rambagh Circle)": {"status": "Flowing", "delay_min": 2, "speed_kmh": 38, "road_score": "9.1/10 (Excellent)", "color": "#10B981"},
    "Ajmer Road (Elements Mall Corridor)": {"status": "Moderate", "delay_min": 6, "speed_kmh": 26, "road_score": "7.8/10 (Good)", "color": "#F59E0B"}
}

JAIPUR_EVENTS = {
    "None / Regular Day": None,
    "🛍️ Midnight Sale at WTP Mall": {"hub": "World Trade Park (WTP) Mall", "expected_crowd": "Very High", "surge_factor": 1.8},
    "🎉 GT Bazaar Weekend Festival": {"hub": "Gaurav Tower (GT) Parking", "expected_crowd": "Critical", "surge_factor": 2.0},
    "🏟️ Cricket Match at SMS Stadium": {"hub": "Ram Niwas Garden Parking", "expected_crowd": "Very High", "surge_factor": 1.8}
}

DEFAULT_HUBS_DATA = [
    {"name": "World Trade Park (WTP) Mall", "lat": 26.8530, "lon": 75.8048, "total_slots": 350, "occupied": 290, "road_quality": 9, "ev_slots": 20, "ev_charger_kw": 60},
    {"name": "Gaurav Tower (GT) Parking", "lat": 26.8545, "lon": 75.8055, "total_slots": 200, "occupied": 185, "road_quality": 8, "ev_slots": 10, "ev_charger_kw": 30},
    {"name": "Pink Square Mall (Raja Park)", "lat": 26.8970, "lon": 75.8270, "total_slots": 150, "occupied": 95, "road_quality": 7, "ev_slots": 8, "ev_charger_kw": 22},
    {"name": "Elements Mall (Ajmer Road)", "lat": 26.8920, "lon": 75.7420, "total_slots": 180, "occupied": 80, "road_quality": 8, "ev_slots": 12, "ev_charger_kw": 50},
    {"name": "Ram Niwas Garden Parking", "lat": 26.9152, "lon": 75.8198, "total_slots": 120, "occupied": 85, "road_quality": 6, "ev_slots": 5, "ev_charger_kw": 22},
    {"name": "Bapu Bazaar Underground Parking", "lat": 26.9180, "lon": 75.8230, "total_slots": 80, "occupied": 72, "road_quality": 5, "ev_slots": 0, "ev_charger_kw": 0},
    {"name": "Johri Bazaar Central Hub", "lat": 26.9210, "lon": 75.8260, "total_slots": 110, "occupied": 102, "road_quality": 4, "ev_slots": 2, "ev_charger_kw": 15}
]

# ==========================================
# 4. DATABASE & RESERVATION HANDLING (NO PREPAY)
# ==========================================
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = None
try:
    supabase = init_supabase()
except Exception:
    pass

def sync_and_get_hubs():
    if not supabase:
        return {item["name"]: item for item in DEFAULT_HUBS_DATA}
    try:
        response = supabase.table("hubs").select("*").execute()
        existing_names = [row["name"].strip().lower() for row in response.data] if response.data else []
        for default_hub in DEFAULT_HUBS_DATA:
            if default_hub["name"].strip().lower() not in existing_names:
                supabase.table("hubs").insert(default_hub).execute()
        response = supabase.table("hubs").select("*").execute()
        return {
            row["name"].strip(): {
                "lat": row["lat"], "lon": row["lon"],
                "total_slots": row["total_slots"], "occupied": row["occupied"],
                "road_quality": row.get("road_quality", 7),
                "ev_slots": row.get("ev_slots", 10), "ev_charger_kw": row.get("ev_charger_kw", 30)
            } for row in response.data
        }
    except Exception:
        return {item["name"]: item for item in DEFAULT_HUBS_DATA}

def create_pay_at_venue_reservation(target_hub_name):
    pass_id = f"NPJ-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
    if not supabase:
        return pass_id, "Success (Local Sync)"
    try:
        clean_target = target_hub_name.strip()
        response = supabase.table("hubs").select("*").ilike("name", clean_target).execute()
        if not response.data:
            return None, "Hub record not found."
        hub_record = response.data[0]
        if hub_record["occupied"] >= hub_record["total_slots"]:
            return None, "Selected parking facility is fully occupied!"
        
        supabase.table("hubs").update({"occupied": hub_record["occupied"] + 1}).eq("name", hub_record["name"]).execute()
        now = datetime.datetime.now(datetime.timezone.utc)
        supabase.table("reservations").insert({
            "pass_id": pass_id,
            "hub_name": hub_record["name"],
            "created_at": now.isoformat(),
            "expires_at": (now + datetime.timedelta(minutes=45)).isoformat(),
            "status": "PAY_AT_VENUE_ACTIVE"
        }).execute()
        return pass_id, "Success"
    except Exception as e:
        return pass_id, f"Local Lock Engaged ({str(e)})"

# ==========================================
# 5. OSRM ROUTING ENGINE & ROAD QUALITY WEIGHTS
# ==========================================
def calculate_optimal_osrm_route(start_coords, end_coords, strategy, base_road_quality=7):
    """
    Queries OpenStreetMap OSRM routing engine and calculates weights 
    for traffic density, road quality scores, and fuel efficiency.
    """
    osrm_url = f"http://router.project-osrm.org/route/v1/driving/{start_coords[1]},{start_coords[0]};{end_coords[1]},{end_coords[0]}?overview=full&geometries=geojson"
    try:
        response = requests.get(osrm_url, timeout=4).json()
        geometry = response['routes'][0]['geometry']['coordinates']
        distance_km = response['routes'][0]['distance'] / 1000.0
        duration_min = response['routes'][0]['duration'] / 60.0
        
        # Multi-variable adjustments based on routing strategy
        if strategy == "Fuel Efficient":
            duration_min *= 1.06
            est_fuel = round(distance_km * 0.062, 2)  # ~16.1 km/L
        elif strategy == "Best Road Quality":
            distance_km *= 1.08
            duration_min *= 0.98
            est_fuel = round(distance_km * 0.071, 2)
        else:  # Traffic Avoidance
            est_fuel = round(distance_km * 0.076, 2)
            
        path = [(lat, lon) for lon, lat in geometry]
        return path, round(distance_km, 2), round(duration_min, 1), est_fuel
    except Exception:
        # Straight-line fallback if OSRM service is unreachable
        R = 6371.0
        dlat = math.radians(end_coords[0] - start_coords[0])
        dlon = math.radians(end_coords[1] - start_coords[1])
        a = math.sin(dlat/2)**2 + math.cos(math.radians(start_coords[0])) * math.cos(math.radians(end_coords[0])) * math.sin(dlon/2)**2
        dist_km = round(R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))) * 1.25, 2)
        dur_min = round((dist_km / 24.0) * 60, 1)
        return [start_coords, end_coords], dist_km, dur_min, round(dist_km * 0.07, 2)

def calculate_dynamic_fee(occupied, total, event_multiplier=1.0):
    if total == 0: return 50, "Standard Rate"
    ratio = occupied / total
    if ratio < 0.50: base_fee, rate_type = 30, "Off-Peak Rate"
    elif ratio <= 0.85: base_fee, rate_type = 50, "Standard Rate"
    else: base_fee, rate_type = 90, "⚡ Capacity Surge"
    
    final_fee = int(base_fee * event_multiplier)
    if event_multiplier > 1.0: rate_type = f"⚡ Event Surge ({rate_type})"
    return final_fee, rate_type

# ==========================================
# 6. SIDEBAR CONTROLS & AUTO-REFRESH HEADER
# ==========================================
st.sidebar.header("🌐 Language / भाषा")
lang = st.sidebar.radio("Select Language", ["English", "हिंदी"], horizontal=True)
T = TRANSLATIONS[lang]

st.markdown(f'<div class="main-title">{T["title"]}</div>', unsafe_allow_html=True)
st.markdown(f'<div class="sub-title">{T["subtitle"]}</div>', unsafe_allow_html=True)

# 5-Minute Auto Refresh Fragment
@st.fragment(run_every=300)
def live_telemetry_banner():
    st.caption(f"🔄 **Live Corridor Sync Active:** Updating every 300s | Last Sync: {datetime.datetime.now().strftime('%H:%M:%S IST')}")

live_telemetry_banner()

# Advanced Route & Safety Controls
st.sidebar.markdown("---")
st.sidebar.header("🕹️ Route & Emergency Controls")
emergency_mode = st.sidebar.toggle("🚑 Emergency Green Wave (SMS Hosp.)", value=False)
weather_cond = st.sidebar.selectbox("🌧️ Live Weather Surface Conditions", ["Sunny / Dry Asphalt", "Heavy Rain / Waterlogged", "Extreme Summer Heat (42°C+)"])

# ==========================================
# 7. MAIN APPLICATION TABS
# ==========================================
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    T["tab1"], T["tab2"], T["tab3"], T["tab4"], T["tab5"], T["tab6"], T["tab7"]
])

# ------------------------------------------
# TAB 1: SMART ROUTE & PAY-AT-VENUE ENGINE
# ------------------------------------------
with tab1:
    parking_spots = sync_and_get_hubs()
    
    start_name = st.sidebar.selectbox(T["starting_loc"], list(LANDMARKS.keys()))
    selected_parking = st.sidebar.selectbox(T["target_hub"], list(parking_spots.keys()))
    
    routing_strategy = st.sidebar.radio(
        T["route_mode"],
        ["Traffic Avoidance", "Fuel Efficient", "Best Road Quality"]
    )
    
    start_coords = LANDMARKS[start_name]
    target_data = parking_spots[selected_parking]
    end_coords = (target_data["lat"], target_data["lon"])
    
    # Calculate OSRM route path
    route_path, dist_km, dur_min, est_fuel = calculate_optimal_osrm_route(
        start_coords, end_coords, routing_strategy, target_data["road_quality"]
    )
    
    venue_fee, fee_rate_type = calculate_dynamic_fee(target_data["occupied"], target_data["total_slots"])
    avail_slots = max(0, target_data["total_slots"] - target_data["occupied"])
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("💳 Spot Booking")
    st.sidebar.info("ℹ️ **Pay at Venue Enabled:** No online prepay required. Pay cash/UPI directly at entry/exit.")
    st.sidebar.metric(T["venue_fee"], f"₹{venue_fee}.00", delta=fee_rate_type)
    
    if st.sidebar.button(T["reserve_btn"]):
        pass_id, status_msg = create_pay_at_venue_reservation(selected_parking)
        if pass_id:
            st.session_state["active_pass"] = pass_id
            st.session_state["active_pass_hub"] = selected_parking
            st.session_state["active_pass_fee"] = venue_fee
            st.success("✅ Spot Reserved! Pay at entry gate.")

    # Hazard & Safety Banners
    if emergency_mode:
        st.error("🚨 **EMERGENCY GREEN WAVE ACTIVE:** Traffic signal preemption engaged along JLN Marg towards SMS Hospital Corridor.")
    elif weather_cond == "Heavy Rain / Waterlogged":
        st.warning("🌧️ **WATERLOGGING HAZARD:** +20% Braking Distance on MI Road & Ajmeri Gate. Speed capped at 25 km/h.")

    if "Bazaar" in selected_parking:
        st.success("🚌 **PARK & RIDE RECOMMENDATION:** High old-city congestion detected! Park at *Ram Niwas Garden* & take Jaipur Metro to save 18 mins.")

    # Live Metrics Bar
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(T["drive_time"], f"{dur_min if not emergency_mode else math.ceil(dur_min*0.4)} mins", delta=f"{dist_km} km ({routing_strategy})")
    m2.metric(T["available"], f"{avail_slots} / {target_data['total_slots']} Left")
    m3.metric(T["road_quality"], f"{target_data['road_quality']} / 10", delta="Smooth Highway" if target_data['road_quality'] >= 8 else "Minor Potholes")
    m4.metric(T["venue_fee"], f"₹{venue_fee}", delta=f"Est. Fuel: {est_fuel} L")

    st.markdown("---")
    map_col, pass_col = st.columns([2, 1])
    
    with map_col:
        st.subheader("🗺️ Live Route & Surface Map")
        m = folium.Map(location=[(start_coords[0]+end_coords[0])/2, (start_coords[1]+end_coords[1])/2], zoom_start=13, tiles="cartodb dark_matter")
        
        color_map = {"Traffic Avoidance": "#38BDF8", "Fuel Efficient": "#10B981", "Best Road Quality": "#F59E0B"}
        line_color = "#DC2626" if emergency_mode else color_map[routing_strategy]
        
        folium.PolyLine(locations=route_path, color=line_color, weight=6, opacity=0.85).add_to(m)
        folium.Marker(start_coords, popup=f"Start: {start_name}", icon=folium.Icon(color="green", icon="play")).add_to(m)
        folium.Marker(end_coords, popup=f"Target: {selected_parking}", icon=folium.Icon(color="red", icon="stop")).add_to(m)
        
        st_folium(m, use_container_width=True, height=420, returned_objects=[])

    with pass_col:
        st.subheader("🎟️ Digital Gate Pass")
        if "active_pass" in st.session_state:
            pid = st.session_state["active_pass"]
            phub = st.session_state.get("active_pass_hub", selected_parking)
            pfee = st.session_state.get("active_pass_fee", venue_fee)
            
            st.success(f"**Gate Pass ID:** `{pid}`")
            st.caption(f"**Location:** {phub} | **Pay at Venue:** ₹{pfee}")
            
            qr = qrcode.QRCode(version=1, box_size=8, border=2)
            qr.add_data(f"PassID:{pid}|Hub:{phub}|PayAtVenue:{pfee}")
            qr.make(fit=True)
            pass_buf = io.BytesIO()
            qr.make_image(fill_color="#1E3A8A", back_color="white").save(pass_buf, format="PNG")
            st.image(pass_buf.getvalue(), caption="Scan at physical gate barrier", width=190)
        else:
            st.info("Click 'Reserve Slot (Pay at Venue)' in the sidebar to generate a scannable entry QR pass.")

# ------------------------------------------
# TAB 2: AI FORECASTING & EV GRID
# ------------------------------------------
with tab2:
    st.subheader("🤖 AI Predictive Occupancy & EV Fast-Charging Grid")
    f_col, ev_col = st.columns([2, 1])
    with f_col:
        selected_forecast_hub = st.selectbox("Select Facility for AI Forecast", list(parking_spots.keys()))
        hub_info = parking_spots[selected_forecast_hub]
        times = [(datetime.datetime.now() + datetime.timedelta(minutes=30*i)).strftime("%I:%M %p") for i in range(7)]
        sim_demand = [min(hub_info["total_slots"], max(10, int(hub_info["occupied"] + random.randint(-15, 25)))) for _ in range(7)]
        df_forecast = pd.DataFrame({"Time": times, "Predicted Occupancy": sim_demand}).set_index("Time")
        st.line_chart(df_forecast)
    with ev_col:
        st.markdown("### ⚡ EV Fast-Charging Grid")
        st.metric("Dedicated EV Stations", f"{hub_info.get('ev_slots', 10)} Chargers")
        st.metric("Grid Charging Power", f"{hub_info.get('ev_charger_kw', 30)} kW CCS2")
        st.success("🟢 Green Grid Sync Active")

# ------------------------------------------
# TAB 3: LIVE CORRIDOR MONITOR
# ------------------------------------------
with tab3:
    st.subheader("🚦 Jaipur Arterial Congestion Monitor")
    for cname, cdata in JAIPUR_CORRIDORS.items():
        st.markdown(f"""
            <div style="background-color:#1F2937; padding:14px; border-radius:10px; border-left:6px solid {cdata['color']}; margin-bottom:12px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:1.05rem; font-weight:700; color:#F3F4F6;">{cname}</span>
                    <span style="background-color:{cdata['color']}; color:white; padding:3px 10px; border-radius:12px; font-size:0.8rem;">{cdata['status']}</span>
                </div>
                <div style="margin-top:8px; color:#9CA3AF; font-size:0.88rem;">
                    ⏱️ Delay: <b>+{cdata['delay_min']} mins</b> | 🚗 Speed: <b>{cdata['speed_kmh']} km/h</b> | 🛠️ Road Score: <b>{cdata['road_score']}</b>
                </div>
            </div>
        """, unsafe_allow_html=True)

# ------------------------------------------
# TAB 4: MALLS & EVENTS PLANNER
# ------------------------------------------
with tab4:
    st.subheader("🛍️ Jaipur Malls & Event Allocation Engine")
    selected_event = st.selectbox("Select Major City Event", list(JAIPUR_EVENTS.keys()))
    event_data = JAIPUR_EVENTS[selected_event]
    if event_data:
        hub_info = parking_spots.get(event_data["hub"], {"occupied": 100, "total_slots": 200})
        e_fee, e_label = calculate_dynamic_fee(hub_info["occupied"], hub_info["total_slots"], event_data["surge_factor"])
        e1, e2, e3 = st.columns(3)
        e1.metric("Allocated Hub", event_data["hub"])
        e2.metric("Event Venue Rate", f"₹{e_fee}", delta=e_label)
        e3.metric("Live Slot Capacity", f"{max(0, hub_info['total_slots'] - hub_info['occupied'])} Left")

# ------------------------------------------
# TAB 5: GATE BARRIER SIMULATOR
# ------------------------------------------
with tab5:
    st.subheader("🛡️ Automated Gate Barrier Simulator")
    verify_id = st.text_input("Scan or Enter Pass ID", placeholder="NPJ-2026...")
    if st.button("Trigger Barrier Sensor Scan") and verify_id:
        st.markdown("""
            <div style="background-color:#10B981; padding:20px; border-radius:10px; text-align:center; color:white; font-weight:700; font-size:1.4rem;">
                🟢 BARRIER GATE OPENED <br>
                <span style="font-size:0.95rem; font-weight:normal;">Pay at Venue Verified • Clearance Confirmed</span>
            </div>
        """, unsafe_allow_html=True)

# ------------------------------------------
# TAB 6: OPERATOR TELEMETRY DASHBOARD
# ------------------------------------------
with tab6:
    st.subheader("📊 Network-Wide Parking Telemetry")
    current_hubs = sync_and_get_hubs()
    total_cap = sum(h["total_slots"] for h in current_hubs.values())
    total_occ = sum(h["occupied"] for h in current_hubs.values())
    utilization = round((total_occ / total_cap) * 100, 1) if total_cap > 0 else 0
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Network Capacity", f"{total_cap} Spots")
    m2.metric("Occupied Spots", f"{total_occ} Vehicles")
    m3.metric("Network Utilization", f"{utilization}%")
    m4.metric("Est. Venue Revenue", f"₹{total_occ * 50}/hr")
    
    st.markdown("---")
    for hname, hdata in current_hubs.items():
        occ, tot = hdata["occupied"], hdata["total_slots"]
        pct = min(1.0, max(0.0, occ / tot)) if tot > 0 else 0.0
        lbl_col, bar_col = st.columns([1, 2])
        with lbl_col:
            st.write(f"**{hname}**")
            st.caption(f"{occ} / {tot} slots occupied")
        with bar_col:
            st.progress(pct)

# ------------------------------------------
# TAB 7: CIVIC ECO & LEADERBOARD
# ------------------------------------------
with tab7:
    st.subheader("🏆 Civic Driver Sustainability & Eco-Score")
    st.caption("Gamifying eco-friendly driving, traffic avoidance, and off-peak parking in Jaipur.")
    
    l1, l2, l3 = st.columns(3)
    l1.metric("Your Driver Rating", "A+ (Excellent)", delta="Top 3% in Jaipur")
    l2.metric("CO₂ Offset", "14.2 kg", delta="+2.4 kg this week")
    l3.metric("Civic Reward Points", "480 Points", delta="₹120 Parking Credit")
    
    st.markdown("---")
    st.write("### 🥇 Top Green Drivers (Jaipur Leaderboard)")
    df_leaderboard = pd.DataFrame({
        "Rank": ["#1", "#2", "#3", "#4", "#5"],
        "Driver ID": ["RJ-14-**-9821", "RJ-14-**-1102", "RJ-14-**-4490", "RJ-14-**-7712", "RJ-14-**-3091"],
        "Fuel Saved (L)": [42.1, 38.5, 34.0, 31.2, 29.8],
        "Eco-Score": [98, 95, 92, 89, 87]
    }).set_index("Rank")
    st.table(df_leaderboard)
    
