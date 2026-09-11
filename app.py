import streamlit as st
import folium
from streamlit_folium import st_folium
import qrcode
import io
import datetime
import math
import urllib.parse
from supabase import create_client, Client

# Page Configuration
st.set_page_config(
    page_title="NaviPark Jaipur - Smart Mobility",
    page_icon="🚗",
    layout="wide"
)

# Custom Styling
st.markdown("""
    <style>
    .main-title { font-size: 2.2rem; font-weight: 700; color: #1E3A8A; margin-bottom: 0px; }
    .sub-title { font-size: 1rem; color: #4B5563; margin-bottom: 25px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">NaviPark Jaipur 🚗</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Smart Route Optimizer & Event-Driven Parking Engine</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# SUPABASE CLOUD CONNECTION
# ---------------------------------------------------------
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase = init_supabase()
except Exception as e:
    st.error(f"Failed to initialize Supabase client: {str(e)}")

LANDMARKS = {
    "MI Road": (26.9124, 75.7873),
    "Jaipur Railway Station": (26.9202, 75.7878),
    "Ajmeri Gate": (26.9156, 75.8202),
    "Raja Park": (26.8982, 75.8245),
    "Mansarovar Hub": (26.8628, 75.7554)
}

JAIPUR_EVENTS = {
    "None / Regular Day": None,
    "🎨 Art Exhibition at Jawahar Kala Kendra": {"hub": "Jawahar Kala Kendra Parking", "expected_crowd": "High", "surge_factor": 1.4},
    "🏟️ Cricket Match at SMS Stadium": {"hub": "Ram Niwas Garden Parking", "expected_crowd": "Very High", "surge_factor": 1.8},
    "🛍️ Weekend Shopping Fest at Bapu Bazaar": {"hub": "Bapu Bazaar Underground Parking", "expected_crowd": "Critical", "surge_factor": 2.0},
    "🏛️ Night Tourism at Albert Hall": {"hub": "Ram Niwas Garden Parking", "expected_crowd": "Moderate", "surge_factor": 1.2}
}

DEFAULT_HUBS_DATA = [
    {"name": "Ram Niwas Garden Parking", "lat": 26.9152, "lon": 75.8198, "total_slots": 120, "occupied": 85},
    {"name": "Bapu Bazaar Underground Parking", "lat": 26.9180, "lon": 75.8230, "total_slots": 80, "occupied": 72},
    {"name": "Jawahar Kala Kendra Parking", "lat": 26.8800, "lon": 75.8080, "total_slots": 150, "occupied": 40},
    {"name": "Pink City Central Hub", "lat": 26.9239, "lon": 75.8267, "total_slots": 100, "occupied": 92}
]

def get_hubs():
    try:
        response = supabase.table("hubs").select("*").execute()
        if not response.data:
            supabase.table("hubs").insert(DEFAULT_HUBS_DATA).execute()
            response = supabase.table("hubs").select("*").execute()

        hubs = {}
        for row in response.data:
            hubs[row["name"]] = {
                "lat": row["lat"],
                "lon": row["lon"],
                "total_slots": row["total_slots"],
                "occupied": row["occupied"]
            }
        return hubs
    except Exception:
        hubs = {}
        for item in DEFAULT_HUBS_DATA:
            hubs[item["name"]] = {
                "lat": item["lat"],
                "lon": item["lon"],
                "total_slots": item["total_slots"],
                "occupied": item["occupied"]
            }
        return hubs

def calculate_dynamic_fee(occupied, total, event_multiplier=1.0):
    if total == 0:
        base_fee = 50
    else:
        ratio = occupied / total
        if ratio < 0.50:
            base_fee = 30
        elif ratio <= 0.85:
            base_fee = 50
        else:
            base_fee = 90
            
    final_fee = int(base_fee * event_multiplier)
    rate_type = "Standard" if event_multiplier == 1.0 else "⚡ Event Surge Rate"
    return final_fee, rate_type

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c * 1.25

# Route Optimizer: Calculates travel times considering city congestion
def optimize_route(orig_lat, orig_lon, dest_lat, dest_lon, traffic_factor=1.2):
    distance_km = haversine_km(orig_lat, orig_lon, dest_lat, dest_lon)
    # Average speed in Jaipur traffic ~ 25 km/h
    base_drive_time_min = (distance_km / 25) * 60 * traffic_factor
    walk_time_min = math.ceil((distance_km * 0.1) * 12)  # Last-mile walk estimate
    co2_saved = round(distance_km * 0.12, 2)
    return round(distance_km, 2), math.ceil(base_drive_time_min), walk_time_min, co2_saved

# ---------------------------------------------------------
# INTERFACE TABS
# ---------------------------------------------------------
tab1, tab2, tab3 = st.tabs([
    "📍 Route Optimizer & Booking", 
    "📅 Jaipur Event Planner", 
    "🛡️ Gate Scanner & Admin"
])

# ---------------------------------------------------------
# TAB 1: ROUTE OPTIMIZER & BOOKING
# ---------------------------------------------------------
with tab1:
    st.sidebar.header("🗺️ Route & Traffic Settings")
    origin_name = st.sidebar.selectbox("Starting Location", list(LANDMARKS.keys()))
    traffic_condition = st.sidebar.select_slider(
        "Current Traffic Density",
        options=["Low (Night)", "Moderate (Normal)", "Heavy (Peak Hours)"],
        value="Moderate (Normal)"
    )
    
    traffic_multipliers = {"Low (Night)": 0.9, "Moderate (Normal)": 1.2, "Heavy (Peak Hours)": 1.7}
    current_traffic_factor = traffic_multipliers[traffic_condition]

    parking_spots = get_hubs()
    
    if parking_spots:
        orig_lat, orig_lon = LANDMARKS[origin_name]
        
        # Rank hubs by travel time
        ranked_hubs = []
        for name, data in parking_spots.items():
            dist, drive_t, walk_t, co2 = optimize_route(orig_lat, orig_lon, data["lat"], data["lon"], current_traffic_factor)
            fee, _ = calculate_dynamic_fee(data["occupied"], data["total_slots"])
            avail = data["total_slots"] - data["occupied"]
            ranked_hubs.append({
                "name": name,
                "distance": dist,
                "drive_time": drive_t,
                "walk_time": walk_t,
                "fee": fee,
                "avail": avail,
                "total": data["total_slots"]
            })
            
        ranked_hubs = sorted(ranked_hubs, key=lambda x: x["drive_time"])
        
        st.subheader("🚀 Optimized Parking Recommendations")
        st.caption("Sorted by fastest arrival time based on live congestion models.")
        
        col_list, col_map = st.columns([1, 1])
        
        with col_list:
            selected_hub_name = st.radio(
                "Select Best Parking Option:",
                [f"{h['name']} — {h['drive_time']} mins ({h['distance']} km) | ₹{h['fee']}" for h in ranked_hubs]
            ).split(" — ")[0]
            
            chosen_hub = next(h for h in ranked_hubs if h["name"] == selected_hub_name)
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Est. Drive Time", f"{chosen_hub['drive_time']} mins")
            c2.metric("Available Spots", f"{chosen_hub['avail']} / {chosen_hub['total']}")
            c3.metric("Parking Fee", f"₹{chosen_hub['fee']}")
            
            if st.button("Proceed to Fast Checkout"):
                st.session_state["active_pass"] = f"NPJ-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                st.session_state["pass_hub"] = chosen_hub["name"]
                st.session_state["pass_fee"] = chosen_hub["fee"]
                st.success("✅ Slot reserved successfully!")

        with col_map:
            dest_lat = parking_spots[selected_hub_name]["lat"]
            dest_lon = parking_spots[selected_hub_name]["lon"]
            m = folium.Map(location=[(orig_lat + dest_lat)/2, (orig_lon + dest_lon)/2], zoom_start=13, tiles="CartoDB positron")
            folium.Marker([orig_lat, orig_lon], popup=f"Origin: {origin_name}", icon=folium.Icon(color="green")).add_to(m)
            folium.Marker([dest_lat, dest_lon], popup=selected_hub_name, icon=folium.Icon(color="red", icon="parking")).add_to(m)
            folium.PolyLine([(orig_lat, orig_lon), (dest_lat, dest_lon)], color="#1E3A8A", weight=4).add_to(m)
            st_folium(m, use_container_width=True, height=350, returned_objects=[])

# ---------------------------------------------------------
# TAB 2: JAIPUR EVENT PLANNER
# ---------------------------------------------------------
with tab2:
    st.subheader("📅 Event-Driven Parking & Crowd Planner")
    st.write("Plan parking in advance for major cultural, sports, and festival events across Jaipur.")
    
    selected_event = st.selectbox("Select Upcoming Event in Jaipur", list(JAIPUR_EVENTS.keys()))
    
    event_data = JAIPUR_EVENTS[selected_event]
    
    if event_data:
        st.info(f"📍 **Target Venue Hub:** {event_data['hub']} | **Expected Traffic:** {event_data['expected_crowd']}")
        
        hub_info = parking_spots.get(event_data["hub"])
        if hub_info:
            event_fee, fee_label = calculate_dynamic_fee(hub_info["occupied"], hub_info["total_slots"], event_data["surge_factor"])
            
            e_col1, e_col2, e_col3 = st.columns(3)
            e_col1.metric("Recommended Parking", event_data["hub"])
            e_col2.metric("Event Dynamic Fee", f"₹{event_fee}", delta=fee_label)
            e_col3.metric("Available Capacity", f"{hub_info['total_slots'] - hub_info['occupied']} slots")
            
            st.markdown("---")
            st.write("### 🎟️ Pre-Book Event Parking Pass")
            driver_name = st.text_input("Driver / Vehicle Number", placeholder="RJ-14-XX-1234")
            
            if st.button("Reserve Event Spot Now"):
                if driver_name:
                    event_pass_id = f"EVT-{datetime.datetime.now().strftime('%M%S')}"
                    st.success(f"🎉 Event Parking Locked! Pass Code: `{event_pass_id}` for {driver_name}")
                else:
                    st.warning("Please enter your vehicle number to complete event booking.")
    else:
        st.write("Select an event above to view real-time venue parking allocations.")

# ---------------------------------------------------------
# TAB 3: GATE SCANNER & ADMIN
# ---------------------------------------------------------
with tab3:
    st.subheader("🛡️ Gate Operations & Analytics")
    st.write("Operator view for validating pass codes at entry barriers.")
    
    scan_code = st.text_input("Scan or Enter Pass Code")
    if st.button("Verify Entry"):
        if scan_code.startswith("NPJ-") or scan_code.startswith("EVT-"):
            st.success("🟢 BARRIER OPEN: Valid Pass Detected!")
        else:
            st.error("🔴 BARRIER CLOSED: Invalid or Expired Pass!")
            
            
