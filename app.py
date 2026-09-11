import streamlit as st
import folium
from streamlit_folium import st_folium
import qrcode
import io
import datetime
import math
from supabase import create_client, Client

# Page Configuration
st.set_page_config(
    page_title="NaviPark Jaipur",
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
st.markdown('<div class="sub-title">Smart Urban Mobility & Dynamic Parking Allocation Engine</div>', unsafe_allow_html=True)

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

# Preset Starting Locations
LANDMARKS = {
    "MI Road": (26.9124, 75.7873),
    "Jaipur Railway Station": (26.9202, 75.7878),
    "Ajmeri Gate": (26.9156, 75.8202),
    "Raja Park": (26.8982, 75.8245),
    "Mansarovar Hub": (26.8628, 75.7554)
}

DEFAULT_HUBS_DATA = [
    {"name": "Ram Niwas Garden Parking", "lat": 26.9152, "lon": 75.8198, "total_slots": 120, "occupied": 85},
    {"name": "Bapu Bazaar Underground Parking", "lat": 26.9180, "lon": 75.8230, "total_slots": 80, "occupied": 72},
    {"name": "Jawahar Kala Kendra Parking", "lat": 26.8800, "lon": 75.8080, "total_slots": 150, "occupied": 40},
    {"name": "Pink City Central Hub", "lat": 26.9239, "lon": 75.8267, "total_slots": 100, "occupied": 92}
]

# Fetch Live Hubs with Automatic Seeding & Error Recovery
def get_hubs():
    try:
        response = supabase.table("hubs").select("*").execute()
        
        # If database returns empty array, auto-seed the default hubs into Supabase Cloud
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
    except Exception as e:
        # Emergency local fallback if cloud network/RLS issues occur
        hubs = {}
        for item in DEFAULT_HUBS_DATA:
            hubs[item["name"]] = {
                "lat": item["lat"],
                "lon": item["lon"],
                "total_slots": item["total_slots"],
                "occupied": item["occupied"]
            }
        return hubs

# Real-Time Cloud Reservation
def create_reservation(hub_name):
    try:
        response = supabase.table("hubs").select("total_slots, occupied").eq("name", hub_name).execute()
        if not response.data:
            return None, "Hub not found in cloud database."
            
        total = response.data[0]["total_slots"]
        occupied = response.data[0]["occupied"]
        
        if occupied >= total:
            return None, "Selected parking hub is completely full!"
        
        # Increment occupied slot count in Supabase
        supabase.table("hubs").update({"occupied": occupied + 1}).eq("name", hub_name).execute()
        
        # Generate pass token
        now = datetime.datetime.now(datetime.timezone.utc)
        pass_id = f"NPJ-{now.strftime('%Y%m%d%H%M%S')}"
        expires_at = (now + datetime.timedelta(minutes=30)).isoformat()
        
        supabase.table("reservations").insert({
            "pass_id": pass_id,
            "hub_name": hub_name,
            "created_at": now.isoformat(),
            "expires_at": expires_at,
            "status": "ACTIVE"
        }).execute()
        
        return pass_id, "Success"
    except Exception as e:
        return None, str(e)

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c * 1.25

# ---------------------------------------------------------
# INTERFACE TABS
# ---------------------------------------------------------
tab1, tab2 = st.tabs(["🚗 Driver Route & Booking", "🛡️ Gate Verification Scanner"])

with tab1:
    st.sidebar.header("📍 Route Settings")
    origin_name = st.sidebar.selectbox("Select Starting Point", list(LANDMARKS.keys()))
    
    parking_spots = get_hubs()
    
    if parking_spots:
        selected_parking = st.sidebar.selectbox("Select Parking Destination", list(parking_spots.keys()))

        if st.sidebar.button("Calculate Route & Reserve Slot"):
            pass_id, res_message = create_reservation(selected_parking)
            
            if not pass_id:
                st.error(f"Reservation Error: {res_message}")
            else:
                parking_spots = get_hubs()
                orig_lat, orig_lon = LANDMARKS[origin_name]
                dest_lat = parking_spots[selected_parking]["lat"]
                dest_lon = parking_spots[selected_parking]["lon"]

                route_km = haversine_km(orig_lat, orig_lon, dest_lat, dest_lon)
                co2_saved_kg = round(route_km * 0.12, 2)

                col1, col2, col3, col4 = st.columns(4)
                spot_data = parking_spots[selected_parking]
                avail_slots = spot_data["total_slots"] - spot_data["occupied"]
                
                col1.metric("Est. Distance", f"{route_km:.2f} km")
                col2.metric("Available Slots", f"{avail_slots} / {spot_data['total_slots']}")
                col3.metric("Est. CO₂ Offset", f"{co2_saved_kg} kg")
                col4.metric("Pass Status", "Active Lock", delta_color="normal")

                st.markdown("---")

                map_col, pass_col = st.columns([2, 1])

                with map_col:
                    st.subheader("🗺️ Dynamic Route Map")
                    m = folium.Map(
                        location=[(orig_lat + dest_lat)/2, (orig_lon + dest_lon)/2], 
                        zoom_start=13, 
                        tiles="CartoDB positron"
                    )
                    folium.Marker([orig_lat, orig_lon], popup=f"Origin: {origin_name}", icon=folium.Icon(color="green", icon="play")).add_to(m)
                    folium.Marker([dest_lat, dest_lon], popup=selected_parking, icon=folium.Icon(color="red", icon="parking")).add_to(m)
                    folium.PolyLine([(orig_lat, orig_lon), (dest_lat, dest_lon)], color="#1E3A8A", weight=5, opacity=0.8).add_to(m)
                    
                    st_folium(m, use_container_width=True, height=400, returned_objects=[])

                with pass_col:
                    st.subheader("🎟️ Digital Entry Pass")
                    st.info(f"**Pass ID:** `{pass_id}`")
                    
                    pass_data = f"Pass ID: {pass_id}\nHub: {selected_parking}\nStatus: Reserved"
                    qr = qrcode.QRCode(version=1, box_size=8, border=2)
                    qr.add_data(pass_data)
                    qr.make(fit=True)
                    
                    qr_img = qr.make_image(fill_color="#1E3A8A", back_color="white")
                    buf = io.BytesIO()
                    qr_img.save(buf, format="PNG")
                    
                    st.image(buf.getvalue(), caption="Scan at entry gate", width=200)
                    st.success("Slot synced across all active clients!")
        else:
            st.info("👈 Choose your starting origin and target hub from the sidebar, then click **Calculate Route & Reserve Slot**.")
    else:
        st.error("No parking hubs available.")

with tab2:
    st.subheader("🛡️ Gate Verification Scanner")
    verify_id = st.text_input("Enter Pass ID (e.g. NPJ-2026...)")
    
    if st.button("Validate Pass"):
        if verify_id:
            try:
                response = supabase.table("reservations").select("hub_name, expires_at, status").eq("pass_id", verify_id.strip()).execute()
                
                if response.data:
                    record = response.data[0]
                    hub = record["hub_name"]
                    expires = record["expires_at"]
                    status = record["status"]
                    
                    exp_time = datetime.datetime.fromisoformat(expires)
                    now_time = datetime.datetime.now(datetime.timezone.utc)
                    
                    if now_time < exp_time and status == "ACTIVE":
                        st.success(f"✅ ACCESS GRANTED! Gate opening for **{hub}**.")
                        supabase.table("reservations").update({"status": "USED"}).eq("pass_id", verify_id.strip()).execute()
                    elif status == "USED":
                        st.warning("⚠️ ACCESS DENIED! Pass has already been used.")
                    else:
                        st.error("❌ ACCESS DENIED! Reservation expired.")
                else:
                    st.error("❌ INVALID PASS! ID not found in database.")
            except Exception as e:
                st.error(f"Verification Error: {str(e)}")
        else:
            st.warning("Please input a valid Pass ID.")
            
