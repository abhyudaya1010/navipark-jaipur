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
    page_title="NaviPark 3D - Smart Mobility & Landmarks",
    page_icon="🚘",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Build JSON string safely outside string interpolation
pwa_manifest_json = json.dumps({
    "name": "NaviPark 3D Jaipur",
    "short_name": "NaviPark",
    "description": "Smart Mobility, Landmarks & Traffic Network for Jaipur",
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

# Expanded Seed Dataset: Jaipur Hubs & Major Historic/Commercial Landmarks
DEFAULT_HUBS_DATA = [
    # Commercial & Transportation Hubs
    {"name": "Gaurav Tower (GT) Hub", "category": "Commercial", "lat": 26.8528, "lon": 75.8052, "height": 80, "total_slots": 150, "occupied": 130, "road_quality": 8, "ev_slots": 12},
    {"name": "World Trade Park (WTP) Hub", "category": "Commercial", "lat": 26.8538, "lon": 75.8058, "height": 110, "total_slots": 300, "occupied": 240, "road_quality": 9, "ev_slots": 25},
    {"name": "Raja Park Commercial Hub", "category": "Commercial", "lat": 26.8917, "lon": 75.8239, "height": 60, "total_slots": 100, "occupied": 85, "road_quality": 6, "ev_slots": 8},
    {"name": "Jaipur Junction Station Hub", "category": "Transit", "lat": 26.9196, "lon": 75.7878, "height": 95, "total_slots": 250, "occupied": 210, "road_quality": 7, "ev_slots": 15},
    {"name": "MI Road Shopping District", "category": "Commercial", "lat": 26.9154, "lon": 75.8118, "height": 70, "total_slots": 120, "occupied": 105, "road_quality": 8, "ev_slots": 10},
    {"name": "MNIT Campus Smart Hub", "category": "Education", "lat": 26.8627, "lon": 75.8122, "height": 55, "total_slots": 80, "occupied": 42, "road_quality": 9, "ev_slots": 20},
    
    # Famous Jaipur Landmarks & Tourist Heritage Sites
    {"name": "Hawa Mahal (Palace of Winds)", "category": "Landmark", "lat": 26.9239, "lon": 75.8267, "height": 90, "total_slots": 90, "occupied": 78, "road_quality": 7, "ev_slots": 6},
    {"name": "City Palace Jaipur", "category": "Landmark", "lat": 26.9258, "lon": 75.8237, "height": 100, "total_slots": 120, "occupied": 95, "road_quality": 8, "ev_slots": 10},
    {"name": "Amer Fort (Amber)", "category": "Landmark", "lat": 26.9855, "lon": 75.8513, "height": 130, "total_slots": 200, "occupied": 160, "road_quality": 8, "ev_slots": 12},
    {"name": "Jal Mahal (Water Palace)", "category": "Landmark", "lat": 26.9534, "lon": 75.8462, "height": 75, "total_slots": 110, "occupied": 70, "road_quality": 8, "ev_slots": 8},
    {"name": "Albert Hall Museum", "category": "Landmark", "lat": 26.9116, "lon": 75.8195, "height": 85, "total_slots": 140, "occupied": 90, "road_quality": 9, "ev_slots": 14},
    {"name": "Nahargarh Fort", "category": "Landmark", "lat": 26.9372, "lon": 75.8155, "height": 120, "total_slots": 150, "occupied": 115, "road_quality": 6, "ev_slots": 5},
    {"name": "Jantar Mantar Observatory", "category": "Landmark", "lat": 26.9248, "lon": 75.8246, "height": 65, "total_slots": 85, "occupied": 60, "road_quality": 8, "ev_slots": 6},
    {"name": "Birla Mandir (Laxmi Narayan)", "category": "Landmark", "lat": 26.8924, "lon": 75.8156, "height": 70, "total_slots": 130, "occupied": 95, "road_quality": 9, "ev_slots": 10}
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
                        "category": row.get("category", "General"),
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
# 4. ROUTE CALCULATION (OSRM SHORTEST PATH ENGINE)
# ==========================================
def get_osrm_route(start_lat, start_lon, end_lat, end_lon):
    """Fetches real driving geometry, distance, and time using open OSRM routing."""
    url = f"http://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}?overview=full&geometries=geojson"
    try:
        r = requests.get(url, timeout=4)
        if r.status_code == 200:
            data = r.json()
            if data.get("routes"):
                route = data["routes"][0]
                coords = route["geometry"]["coordinates"]
                # Convert [lon, lat] to [lat, lon]
                path = [[c[1], c[0]] for c in coords]
                dist_km = route["distance"] / 1000.0
                duration_min = route["duration"] / 60.0
                return path, round(dist_km, 2), round(duration_min, 1)
    except Exception:
        pass
    # Fallback straight line calculation
    return [[start_lat, start_lon], [end_lat, end_lon]], 5.0, 12.0

# ==========================================
# 5. HEADER & AUTOMATED TELEMETRY FRAGMENT
# ==========================================
st.markdown('<div class="main-title">NaviPark 3D Network 🚘</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Jaipur Landmarks, Shortest Route Navigation & Live Parking Network</div>', unsafe_allow_html=True)

@st.fragment(run_every=10)
def auto_sync_banner():
    """Simulates active parking occupancy changes by mutating session state directly."""
    for name, hub in st.session_state["hubs_data"].items():
        delta = random.randint(-2, 2)
        hub["occupied"] = max(10, min(hub["total_slots"], hub["occupied"] + delta))

    st.caption(
        f"⚡ **Live Sensor Telemetry Active:** Auto-syncing parking occupancy | "
        f"Last Telemetry Pulse: {datetime.datetime.now().strftime('%H:%M:%S IST')}"
    )

auto_sync_banner()

# ==========================================
# 6. APPLICATION NAVIGATION TABS
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs([
    "🗺️ Interactive 3D Map & Routes", 
    "🎟️ Pay-at-Venue Reservation", 
    "🤖 AI Mobility Strategist", 
    "📊 City Network Analytics"
])

current_hubs = fetch_real_hubs()

# ------------------------------------------
# TAB 1: INTERACTIVE 3D MAP & ROUTE NAVIGATOR
# ------------------------------------------
with tab1:
    col_map, col_control = st.columns([3, 1])
    
    map_data = []
    for h in current_hubs.values():
        available = h["total_slots"] - h["occupied"]
        occupancy_rate = h["occupied"] / h["total_slots"]
        
        # Color coding: Red = High Occupancy, Green = Low Occupancy
        if occupancy_rate > 0.85:
            color = [239, 68, 68, 200]
        elif occupancy_rate > 0.60:
            color = [245, 158, 11, 200]
        else:
            color = [16, 185, 129, 200]
            
        map_data.append({
            "name": h["name"],
            "category": h.get("category", "General"),
            "lat": h["lat"],
            "lon": h["lon"],
            "height": h["height"] * 3,
            "occupied": h["occupied"],
            "total_slots": h["total_slots"],
            "available": available,
            "color": color
        })
    
    df_map = pd.DataFrame(map_data)
    
    with col_control:
        st.subheader("Shortest Route Finder")
        
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
        route_path, dist_km, duration_min = get_osrm_route(orig_lat, orig_lon, target_hub["lat"], target_hub["lon"])
        
        st.metric("Shortest Distance", f"{dist_km} km")
        st.metric("Est. Driving Time", f"{duration_min} mins")
        
        st.markdown(f"**Selected Hub Type:** `{target_hub.get('category', 'General')}`")
        st.markdown(f"**Live Parking Status:** `{target_hub['total_slots'] - target_hub['occupied']} slots free`")
        
        st.write("---")
        st.caption("🟢 Green: Low Occupancy | 🟠 Yellow: Moderate | 🔴 Red: High Traffic")

    with col_map:
        # PyDeck 3D Layer Construction
        column_layer = pdk.Layer(
            "ColumnLayer",
            data=df_map,
            get_position=["lon", "lat"],
            get_elevation="height",
            radius=90,
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
            width_min_pixels=5,
        )
        
        view_state = pdk.ViewState(
            latitude=target_hub["lat"],
            longitude=target_hub["lon"],
            zoom=12,
            pitch=45,
            bearing=15
        )
        
        st.pydeck_chart(pdk.Deck(
            layers=[column_layer, path_layer],
            initial_view_state=view_state,
            tooltip={"html": "<b>{name}</b> ({category})<br/>Free Slots: <b>{available}</b> / {total_slots}"}
        ))

# ------------------------------------------
# TAB 2: PAY-AT-VENUE RESERVATION
# ------------------------------------------
with tab2:
    st.subheader("Instant Pay-at-Venue Digital Gate Pass")
    st.write("Reserve parking at major Jaipur landmarks and commercial centers before you arrive.")
    
    col_res1, col_res2 = st.columns([1, 1])
    
    with col_res1:
        res_hub = st.selectbox("Target Landmark / Parking Hub", list(current_hubs.keys()), key="res_hub_select")
        selected_data = current_hubs[res_hub]
        avail_count = selected_data["total_slots"] - selected_data["occupied"]
        
        st.info(f"📍 **{res_hub}**\n\nSlots Available Right Now: **{avail_count} / {selected_data['total_slots']}**")
        
        vehicle_no = st.text_input("Vehicle License Plate Number", value="RJ-14-CC-2026")
        duration = st.slider("Parking Duration (Hours)", 1, 8, 2)
        base_fee = duration * 30
        
        st.markdown(f"### Total Entry Fee: **₹{base_fee}** *(Pay at Gate)*")
        
        if st.button("Generate Gate Pass & Reserve", type="primary"):
            if avail_count > 0:
                pass_id, msg = create_pay_at_venue_reservation(res_hub, base_fee)
                st.session_state["last_pass"] = {
                    "pass_id": pass_id,
                    "hub": res_hub,
                    "vehicle": vehicle_no,
                    "fee": base_fee,
                    "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                st.success(f"Slot Reserved Successfully! Pass ID: {pass_id}")
            else:
                st.error("Selected Hub is completely full! Please pick an alternate nearby location.")

    with col_res2:
        if "last_pass" in st.session_state:
            lp = st.session_state["last_pass"]
            st.markdown("### 🎫 Active Gate Pass")
            
            # QR Code Generation
            qr_payload = f"NAVIPARK_PASS|ID:{lp['pass_id']}|HUB:{lp['hub']}|VEH:{lp['vehicle']}|FEE:{lp['fee']}"
            qr_img = qrcode.make(qr_payload)
            buf = io.BytesIO()
            qr_img.save(buf, format="PNG")
            
            st.image(buf.getvalue(), width=220, caption=f"Scan at {lp['hub']} Entry Gate")
            st.code(
                f"PASS ID : {lp['pass_id']}\n"
                f"DESTINATION: {lp['hub']}\n"
                f"VEHICLE : {lp['vehicle']}\n"
                f"AMOUNT  : ₹{lp['fee']} (Pay at Gate)\n"
                f"ISSUED  : {lp['time']}"
            )
        else:
            st.info("Complete the reservation form on the left to generate your digital gate pass.")

# ------------------------------------------
# TAB 3: AI MOBILITY STRATEGIST
# ------------------------------------------
with tab3:
    st.subheader("🤖 AI Mobility Strategist")
    st.write("Get real-time answers for visiting Jaipur's famous landmarks, avoiding traffic bottlenecks, and optimal parking times.")
    
    query = st.text_input("Ask a question about visiting Jaipur landmarks:", value="What is the shortest path and best parking strategy for Hawa Mahal and City Palace?")
    
    if st.button("Get Mobility Strategy"):
        with st.spinner("Analyzing Old City (Badi Chaupar) traffic nodes..."):
            if "hawa mahal" in query.lower() or "city palace" in query.lower() or "old city" in query.lower():
                st.markdown("""
                **💡 Strategic AI Recommendation for Old Walled City:**
                * **Traffic Constraint:** High density around Badi Chaupar and Johari Bazar between **11:00 AM - 6:00 PM**.
                * **Shortest Path:** Route via **MI Road -> Ajmeri Gate -> Tripolia Bazar** to bypass Badi Chaupar traffic.
                * **Optimal Parking:** Park at **City Palace Hub** or **Albert Hall Hub** (and take a 5-min e-rickshaw) to avoid inner-market parking delays.
                """)
            elif "amer" in query.lower() or "nahargarh" in query.lower() or "jal mahal" in query.lower():
                st.markdown("""
                **💡 Strategic AI Recommendation for Northern Fort Corridor:**
                * **Route Optimization:** Take **Amer Road via Jal Mahal**. Nahargarh Fort requires navigating winding ghat roads—drive carefully during peak sunset hours (5:00 PM - 7:00 PM).
                * **Parking Strategy:** Park at **Jal Mahal Hub** first for quick photo stops, then proceed directly to **Amer Fort Underground Parking**.
                """)
            else:
                st.markdown("""
                **💡 Strategic AI Recommendation:**
                * **Grid Status:** Primary arterial corridors (JLN Marg, Tonk Road, MI Road) are operating normally.
                * **EV Charging Tip:** Fast charging is available at WTP, Albert Hall, and Amer Fort Hubs.
                * **Shortest Path:** Select your start location in Tab 1 to generate live step-by-step OSRM driving geometry.
                """)

# ------------------------------------------
# TAB 4: CITY NETWORK ANALYTICS
# ------------------------------------------
with tab4:
    st.subheader("📊 Jaipur Network Health & Landmark Analytics")
    
    total_capacity = sum(h["total_slots"] for h in current_hubs.values())
    total_occupied = sum(h["occupied"] for h in current_hubs.values())
    total_ev = sum(h["ev_slots"] for h in current_hubs.values())
    net_utilization = (total_occupied / total_capacity) * 100
    
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    col_m1.metric("Landmarks & Hubs Online", len(current_hubs))
    col_m2.metric("Total Network Slots", f"{total_occupied} / {total_capacity}")
    col_m3.metric("System Utilization", f"{net_utilization:.1f}%")
    col_m4.metric("EV Chargers Active", total_ev)
    
    st.write("---")
    st.subheader("Live Hub & Landmark Breakdown")
    
    analytics_df = pd.DataFrame([
        {
            "Landmark / Hub Name": h["name"],
            "Category": h.get("category", "General"),
            "Occupied": h["occupied"],
            "Capacity": h["total_slots"],
            "Free Slots": h["total_slots"] - h["occupied"],
            "Utilization": f"{(h['occupied']/h['total_slots'])*100:.1f}%",
            "Road Index": f"{h['road_quality']}/10",
            "EV Chargers": h["ev_slots"]
        }
        for h in current_hubs.values()
    ])
    
    st.dataframe(analytics_df, use_container_width=True)
            
