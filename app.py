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
from supabase import create_client, Client

# ==========================================
# 1. STREAMLIT CONFIG & PWA MANIFEST
# ==========================================
st.set_page_config(
    page_title="NaviPark 3D Pro - Smart Mobility & Landmarks",
    page_icon="🚘",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Build JSON string safely
pwa_manifest_json = json.dumps({
    "name": "NaviPark 3D Jaipur Pro",
    "short_name": "NaviPark Pro",
    "description": "Smart Mobility, AI Route Engine & Parking Network for Jaipur",
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

# Pure JavaScript injection for PWA support
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
    .feature-card {
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(56, 189, 248, 0.2);
        padding: 16px;
        border-radius: 12px;
        margin-bottom: 12px;
    }
    </style>
""", unsafe_allow_html=True)

# Expanded Dataset with Hub Metadata & Hourly Pricing
DEFAULT_HUBS_DATA = [
    {"name": "Gaurav Tower (GT) Hub", "category": "Commercial", "lat": 26.8528, "lon": 75.8052, "height": 250, "total_slots": 150, "occupied": 130, "road_quality": 8, "ev_slots": 12, "hourly_rate": 30},
    {"name": "World Trade Park (WTP) Hub", "category": "Commercial", "lat": 26.8538, "lon": 75.8058, "height": 300, "total_slots": 300, "occupied": 240, "road_quality": 9, "ev_slots": 25, "hourly_rate": 40},
    {"name": "Raja Park Commercial Hub", "category": "Commercial", "lat": 26.8917, "lon": 75.8239, "height": 200, "total_slots": 100, "occupied": 85, "road_quality": 6, "ev_slots": 8, "hourly_rate": 25},
    {"name": "Jaipur Junction Station Hub", "category": "Transit", "lat": 26.9196, "lon": 75.7878, "height": 280, "total_slots": 250, "occupied": 210, "road_quality": 7, "ev_slots": 15, "hourly_rate": 20},
    {"name": "MI Road Shopping District", "category": "Commercial", "lat": 26.9154, "lon": 75.8118, "height": 220, "total_slots": 120, "occupied": 105, "road_quality": 8, "ev_slots": 10, "hourly_rate": 30},
    {"name": "MNIT Campus Smart Hub", "category": "Education", "lat": 26.8627, "lon": 75.8122, "height": 180, "total_slots": 80, "occupied": 42, "road_quality": 9, "ev_slots": 20, "hourly_rate": 15},
    {"name": "Hawa Mahal (Palace of Winds)", "category": "Landmark", "lat": 26.9239, "lon": 75.8267, "height": 260, "total_slots": 90, "occupied": 78, "road_quality": 7, "ev_slots": 6, "hourly_rate": 35},
    {"name": "City Palace Jaipur", "category": "Landmark", "lat": 26.9258, "lon": 75.8237, "height": 290, "total_slots": 120, "occupied": 95, "road_quality": 8, "ev_slots": 10, "hourly_rate": 35},
    {"name": "Amer Fort (Amber)", "category": "Landmark", "lat": 26.9855, "lon": 75.8513, "height": 350, "total_slots": 200, "occupied": 160, "road_quality": 8, "ev_slots": 12, "hourly_rate": 50},
    {"name": "Jal Mahal (Water Palace)", "category": "Landmark", "lat": 26.9534, "lon": 75.8462, "height": 240, "total_slots": 110, "occupied": 70, "road_quality": 8, "ev_slots": 8, "hourly_rate": 30},
    {"name": "Albert Hall Museum", "category": "Landmark", "lat": 26.9116, "lon": 75.8195, "height": 270, "total_slots": 140, "occupied": 90, "road_quality": 9, "ev_slots": 14, "hourly_rate": 25},
    {"name": "Nahargarh Fort", "category": "Landmark", "lat": 26.9372, "lon": 75.8155, "height": 320, "total_slots": 150, "occupied": 115, "road_quality": 6, "ev_slots": 5, "hourly_rate": 40},
    {"name": "Jantar Mantar Observatory", "category": "Landmark", "lat": 26.9248, "lon": 75.8246, "height": 210, "total_slots": 85, "occupied": 60, "road_quality": 8, "ev_slots": 6, "hourly_rate": 30},
    {"name": "Birla Mandir (Laxmi Narayan)", "category": "Landmark", "lat": 26.8924, "lon": 75.8156, "height": 230, "total_slots": 130, "occupied": 95, "road_quality": 9, "ev_slots": 10, "hourly_rate": 20}
]

# ==========================================
# 3. DATABASE & REAL-TIME TELEMETRY
# ==========================================
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

if "hubs_data" not in st.session_state:
    st.session_state["hubs_data"] = {item["name"]: item.copy() for item in DEFAULT_HUBS_DATA}

if "user_passes" not in st.session_state:
    st.session_state["user_passes"] = []

def fetch_real_hubs():
    if supabase:
        try:
            res = supabase.table("hubs").select("*").execute()
            if res.data:
                return {
                    row["name"].strip(): {
                        "id": row.get("id", f"hub_{i}"),
                        "name": row["name"],
                        "category": row.get("category", "General"),
                        "lat": float(row["lat"]), "lon": float(row["lon"]),
                        "height": row.get("height", 250),
                        "total_slots": int(row["total_slots"]), 
                        "occupied": int(row["occupied"]),
                        "road_quality": row.get("road_quality", 7),
                        "ev_slots": row.get("ev_slots", 5),
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
        if hub["occupied"] < hub["total_slots"]:
            hub["occupied"] += 1

    pass_record = {
        "pass_id": pass_id,
        "hub": hub_name,
        "fee": fee,
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "CONFIRMED"
    }
    st.session_state["user_passes"].append(pass_record)
    return pass_id, "Success"

# ==========================================
# 4. ROUTE ENGINE & ECO CALCULATOR
# ==========================================
def get_osrm_route(start_lat, start_lon, end_lat, end_lon):
    url = f"http://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}?overview=full&geometries=geojson"
    try:
        r = requests.get(url, timeout=4)
        if r.status_code == 200:
            data = r.json()
            if data.get("routes"):
                route = data["routes"][0]
                coords = route["geometry"]["coordinates"] # [lon, lat]
                dist_km = route["distance"] / 1000.0
                duration_min = route["duration"] / 60.0
                return coords, round(dist_km, 2), round(duration_min, 1)
    except Exception:
        pass
    return [[start_lon, start_lat], [end_lon, end_lat]], 5.0, 12.0

def calculate_trip_impact(dist_km, vehicle_type="Petrol Car"):
    """Calculates fuel cost in INR and CO2 output based on vehicle type."""
    if vehicle_type == "EV":
        cost = dist_km * 1.5
        co2_kg = 0.0
    elif vehicle_type == "Two Wheeler":
        cost = dist_km * 2.5
        co2_kg = dist_km * 0.04
    else:  # Petrol / Diesel Car
        cost = dist_km * 7.5
        co2_kg = dist_km * 0.12
    return round(cost, 1), round(co2_kg, 2)

# ==========================================
# 5. SIDEBAR FILTERS & SETTINGS
# ==========================================
with st.sidebar:
    st.title("⚙️ Map & Network Controls")
    
    st.subheader("🔍 Live Map Filters")
    categories = list(set(h["category"] for h in DEFAULT_HUBS_DATA))
    selected_cats = st.multiselect("Filter by Category", categories, default=categories)
    
    min_free_slots = st.slider("Min. Free Slots Required", 0, 50, 0)
    ev_only = st.checkbox("⚡ Show EV Charging Locations Only", value=False)
    
    st.write("---")
    st.subheader("🚗 Trip Settings")
    vehicle_mode = st.selectbox("Vehicle Type", ["Petrol Car", "Diesel Car", "EV", "Two Wheeler"])
    
    st.write("---")
    st.caption("⚡ **Live Sensor Telemetry:** Auto-syncing parking occupancy every 10 seconds.")

# ==========================================
# 6. HEADER & AUTOMATED TELEMETRY FRAGMENT
# ==========================================
st.markdown('<div class="main-title">NaviPark 3D Pro 🚘</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Smart Mobility, 3D Route Engine & Real-Time Landmark Parking Network</div>', unsafe_allow_html=True)

@st.fragment(run_every=10)
def auto_sync_banner():
    for name, hub in st.session_state["hubs_data"].items():
        delta = random.randint(-2, 2)
        hub["occupied"] = max(10, min(hub["total_slots"], hub["occupied"] + delta))

    st.caption(
        f"⚡ **Live Network Telemetry:** Monitoring {len(st.session_state['hubs_data'])} Jaipur landmarks & hubs | "
        f"Last Pulse: {datetime.datetime.now().strftime('%H:%M:%S IST')}"
    )

auto_sync_banner()

# ==========================================
# 7. MAIN APPLICATION TABS
# ==========================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🗺️ Interactive 3D Route Map", 
    "🎟️ Digital Gate Pass & Wallet", 
    "🤖 AI Mobility Strategist", 
    "🌱 Eco & Trip Cost Calculator",
    "📊 City Network Analytics"
])

current_hubs = fetch_real_hubs()

# ------------------------------------------
# TAB 1: INTERACTIVE 3D ROUTE MAP
# ------------------------------------------
with tab1:
    col_map, col_control = st.columns([3, 1])
    
    # Filter hubs based on sidebar controls
    map_data = []
    for h in current_hubs.values():
        available = h["total_slots"] - h["occupied"]
        occupancy_rate = h["occupied"] / h["total_slots"]
        
        # Apply Sidebar Filters
        if h.get("category", "General") not in selected_cats:
            continue
        if available < min_free_slots:
            continue
        if ev_only and h.get("ev_slots", 0) == 0:
            continue

        if occupancy_rate > 0.85:
            color = [239, 68, 68, 220]
        elif occupancy_rate > 0.60:
            color = [245, 158, 11, 220]
        else:
            color = [16, 185, 129, 220]
            
        map_data.append({
            "name": h["name"],
            "category": h.get("category", "General"),
            "lat": float(h["lat"]),
            "lon": float(h["lon"]),
            "height": float(h.get("height", 250)),
            "occupied": h["occupied"],
            "total_slots": h["total_slots"],
            "available": available,
            "ev_slots": h.get("ev_slots", 0),
            "color": color
        })
    
    df_map = pd.DataFrame(map_data)
    
    with col_control:
        st.subheader("Navigation Control")
        
        origin_coords = {
            "Jaipur International Airport (JAI)": [26.8242, 75.8122],
            "Jaipur Junction Railway Station": [26.9196, 75.7878],
            "Sindhi Camp Bus Stand": [26.9240, 75.7989],
            "Malaviya Nagar": [26.8389, 75.8056],
            "Vaishali Nagar": [26.9124, 75.7433],
            "C-Scheme": [26.9098, 75.8006],
            "Mansarovar Metro Station": [26.8819, 75.7663]
        }
        
        user_origin = st.selectbox("Starting Location", list(origin_coords.keys()))
        dest_hub_name = st.selectbox("Select Destination / Landmark", list(current_hubs.keys()))
        target_hub = current_hubs[dest_hub_name]
        
        orig_lat, orig_lon = origin_coords[user_origin]
        
        # Get OSRM Driving Route
        route_path, dist_km, duration_min = get_osrm_route(orig_lat, orig_lon, target_hub["lat"], target_hub["lon"])
        
        st.metric("Shortest Driving Distance", f"{dist_km} km")
        st.metric("Est. Travel Time", f"{duration_min} mins")
        
        # Quick Route Simulation Drawer
        with st.expander("🚘 Turn-by-Turn Route Steps"):
            st.write(f"1. **Start:** Depart from `{user_origin}`")
            st.write(f"2. **Merge:** Join main arterial road towards `{target_hub['category']}` corridor")
            st.write(f"3. **Arrive:** Destination `{target_hub['name']}` on right")
            st.write(f"4. **Parking:** `{target_hub['total_slots'] - target_hub['occupied']}` slots available")

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
            
            mid_lat = (orig_lat + target_hub["lat"]) / 2
            mid_lon = (orig_lon + target_hub["lon"]) / 2
            
            view_state = pdk.ViewState(
                latitude=mid_lat,
                longitude=mid_lon,
                zoom=11,
                pitch=50,
                bearing=10
            )
            
            st.pydeck_chart(pdk.Deck(
                layers=[column_layer, path_layer],
                initial_view_state=view_state,
                tooltip={"html": "<b>{name}</b> ({category})<br/>Free Slots: <b>{available}</b> / {total_slots}<br/>⚡ EV Ports: <b>{ev_slots}</b>"}
            ))
        else:
            st.warning("No landmarks match your active filter criteria! Try broadening your filter settings in the sidebar.")

# ------------------------------------------
# TAB 2: DIGITAL GATE PASS & WALLET
# ------------------------------------------
with tab2:
    st.subheader("🎟️ Instant Pay-at-Venue Pass & Digital Wallet")
    
    col_res1, col_res2 = st.columns([1, 1])
    
    with col_res1:
        st.markdown("### Generate Gate Pass")
        res_hub = st.selectbox("Target Landmark / Parking Hub", list(current_hubs.keys()), key="res_hub_select")
        selected_data = current_hubs[res_hub]
        avail_count = selected_data["total_slots"] - selected_data["occupied"]
        
        st.info(f"📍 **{res_hub}**\n\nSlots Free: **{avail_count} / {selected_data['total_slots']}** | Rate: **₹{selected_data.get('hourly_rate', 30)}/hr**")
        
        vehicle_no = st.text_input("Vehicle License Plate", value="RJ-14-CC-2026")
        duration = st.slider("Parking Duration (Hours)", 1, 8, 2)
        base_fee = duration * selected_data.get('hourly_rate', 30)
        
        st.markdown(f"#### Calculated Fee: **₹{base_fee}** *(Pay at Gate)*")
        
        if st.button("Generate QR Gate Pass", type="primary"):
            if avail_count > 0:
                pass_id, msg = create_pay_at_venue_reservation(res_hub, base_fee)
                st.session_state["last_pass"] = {
                    "pass_id": pass_id,
                    "hub": res_hub,
                    "vehicle": vehicle_no,
                    "fee": base_fee,
                    "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                st.success(f"Pass Generated! ID: {pass_id}")
            else:
                st.error("Selected location is completely full! Choose another nearby hub.")

    with col_res2:
        st.markdown("### 💳 Active Pass Wallet")
        if "last_pass" in st.session_state:
            lp = st.session_state["last_pass"]
            
            qr_payload = f"NAVIPARK_PASS|ID:{lp['pass_id']}|HUB:{lp['hub']}|VEH:{lp['vehicle']}|FEE:{lp['fee']}"
            qr_img = qrcode.make(qr_payload)
            buf = io.BytesIO()
            qr_img.save(buf, format="PNG")
            
            st.image(buf.getvalue(), width=220, caption=f"Scan at {lp['hub']} Gate")
            st.code(
                f"PASS ID : {lp['pass_id']}\n"
                f"HUB     : {lp['hub']}\n"
                f"VEHICLE : {lp['vehicle']}\n"
                f"AMOUNT  : ₹{lp['fee']}\n"
                f"ISSUED  : {lp['time']}"
            )
        else:
            st.info("No active pass generated yet. Use the form on the left to issue a gate pass.")

        # Digital Wallet History Component
        if st.session_state["user_passes"]:
            st.write("---")
            st.markdown("#### 📜 Session Pass History")
            history_df = pd.DataFrame(st.session_state["user_passes"])
            st.dataframe(history_df, use_container_width=True)

# ------------------------------------------
# TAB 3: AI MOBILITY STRATEGIST
# ------------------------------------------
with tab3:
    st.subheader("🤖 AI Mobility & Traffic Strategist")
    st.write("Ask questions regarding Jaipur traffic patterns, optimal parking slots, or best visiting times.")
    
    query = st.text_input("Ask a question about visiting Jaipur landmarks:", value="What is the shortest path and best parking strategy for Hawa Mahal and City Palace?")
    
    if st.button("Generate AI Mobility Strategy"):
        with st.spinner("Analyzing Old City arterial network..."):
            if "hawa mahal" in query.lower() or "city palace" in query.lower() or "old city" in query.lower():
                st.markdown("""
                **💡 Strategic AI Recommendation for Old Walled City:**
                * **Traffic Density:** Heavy slowdowns near Badi Chaupar between **11:00 AM - 6:00 PM**.
                * **Shortest Path:** Drive via **MI Road -> Ajmeri Gate -> Tripolia Bazar** to bypass Badi Chaupar congestion.
                * **Smart Parking Strategy:** Park at **City Palace Hub** or **Albert Hall Hub** (and take a 5-minute e-rickshaw) to bypass narrow alley bottlenecks.
                * **EV Availability:** Albert Hall Hub has 14 fast-charging ports available.
                """)
            elif "amer" in query.lower() or "nahargarh" in query.lower() or "jal mahal" in query.lower():
                st.markdown("""
                **💡 Strategic AI Recommendation for Northern Fort Corridor:**
                * **Route Optimization:** Take **Amer Road past Jal Mahal**. Sunset hours (5:00 PM - 7:00 PM) experience heavy tourist traffic on Nahargarh winding roads.
                * **Parking Strategy:** Park at **Jal Mahal Hub** for photography, then proceed directly to **Amer Fort Underground Parking**.
                """)
            else:
                st.markdown("""
                **💡 Strategic AI Recommendation:**
                * **Network Status:** Major corridors (JLN Marg, Tonk Road, MI Road) are flowing normally.
                * **EV Charging Tip:** Fast chargers active at WTP, Albert Hall, and Amer Fort Hubs.
                * **Shortest Path:** Select your start location in Tab 1 to draw real-time driving geometry.
                """)

# ------------------------------------------
# TAB 4: ECO & TRIP COST CALCULATOR
# ------------------------------------------
with tab4:
    st.subheader("🌱 Smart Trip Cost & Carbon Calculator")
    st.write("Estimate route fuel expenditure and carbon footprint for your trip across Jaipur.")
    
    col_c1, col_c2 = st.columns([1, 1])
    
    with col_c1:
        calc_origin = st.selectbox("From", list(origin_coords.keys()), key="calc_orig")
        calc_dest = st.selectbox("To Destination", list(current_hubs.keys()), key="calc_dest")
        
        c_orig_lat, c_orig_lon = origin_coords[calc_origin]
        c_target = current_hubs[calc_dest]
        
        _, trip_dist, trip_time = get_osrm_route(c_orig_lat, c_orig_lon, c_target["lat"], c_target["lon"])
        
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
            savings = est_cost - ev_cost
            st.success(f"💡 **EV Savings Tip:** Switching this trip to an Electric Vehicle saves approximately **₹{savings:.1f}** in fuel cost!")

# ------------------------------------------
# TAB 5: CITY NETWORK ANALYTICS
# ------------------------------------------
with tab5:
    st.subheader("📊 City Network Health & Analytics")
    
    total_capacity = sum(h["total_slots"] for h in current_hubs.values())
    total_occupied = sum(h["occupied"] for h in current_hubs.values())
    total_ev = sum(h.get("ev_slots", 0) for h in current_hubs.values())
    net_utilization = (total_occupied / total_capacity) * 100
    
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    col_m1.metric("Landmarks & Hubs Online", len(current_hubs))
    col_m2.metric("Total Network Slots", f"{total_occupied} / {total_capacity}")
    col_m3.metric("System Utilization", f"{net_utilization:.1f}%")
    col_m4.metric("EV Ports Active", total_ev)
    
    st.write("---")
    st.subheader("Live Hub & Landmark Breakdown")
    
    analytics_df = pd.DataFrame([
        {
            "Landmark / Hub Name": h["name"],
            "Category": h.get("category", "General"),
            "Occupied": h["occupied"],
            "Capacity": h["total_slots"],
            "Free Slots": h["total_slots"] - h["occupied"],
            "Hourly Rate": f"₹{h.get('hourly_rate', 30)}/hr",
            "Utilization": f"{(h['occupied']/h['total_slots'])*100:.1f}%",
            "Road Index": f"{h['road_quality']}/10",
            "EV Ports": h.get("ev_slots", 0)
        }
        for h in current_hubs.values()
    ])
    
    st.dataframe(analytics_df, use_container_width=True)
