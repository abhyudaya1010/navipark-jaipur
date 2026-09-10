import streamlit as st
import networkx as nx
import osmnx as ox
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import qrcode
from PIL import Image
import io
import sqlite3
import datetime

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

# App Title Header
st.markdown('<div class="main-title">NaviPark Jaipur 🚗</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Smart Urban Mobility & Dynamic Parking Allocation Engine</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# DATABASE INITIALIZATION
# ---------------------------------------------------------
def init_db():
    conn = sqlite3.connect("navipark.db")
    c = conn.cursor()
    # Table to track real-time parking slot availability
    c.execute('''CREATE TABLE IF NOT EXISTS hubs 
                 (name TEXT PRIMARY KEY, lat REAL, lon REAL, total_slots INTEGER, occupied INTEGER)''')
    # Table to track active digital passes
    c.execute('''CREATE TABLE IF NOT EXISTS reservations 
                 (pass_id TEXT PRIMARY KEY, hub_name TEXT, created_at TEXT, expires_at TEXT, status TEXT)''')
    
    # Populate default parking hubs if table is empty
    c.execute("SELECT COUNT(*) FROM hubs")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO hubs VALUES (?, ?, ?, ?, ?)", [
            ("Ram Niwas Garden Parking", 26.9152, 75.8198, 120, 85),
            ("Bapu Bazaar Underground Parking", 26.9180, 75.8230, 80, 72),
            ("Jawahar Kala Kendra Parking", 26.8800, 75.8080, 150, 40),
            ("Pink City Central Hub", 26.9239, 75.8267, 100, 92)
        ])
    conn.commit()
    conn.close()

init_db()

# Transactional Helper to Reserve Spot
def create_reservation(hub_name):
    conn = sqlite3.connect("navipark.db")
    c = conn.cursor()
    
    c.execute("SELECT total_slots, occupied FROM hubs WHERE name = ?", (hub_name,))
    row = c.fetchone()
    if not row:
        conn.close()
        return None, "Hub not found!"
        
    total, occupied = row
    if occupied >= total:
        conn.close()
        return None, "Hub is completely full!"
    
    # Increment occupied slot count
    c.execute("UPDATE hubs SET occupied = occupied + 1 WHERE name = ?", (hub_name,))
    
    # Generate Unique Pass
    now = datetime.datetime.now()
    pass_id = f"NPJ-{now.strftime('%Y%m%d%H%M%S')}"
    created_at = now.isoformat()
    expires_at = (now + datetime.timedelta(minutes=30)).isoformat()
    
    c.execute("INSERT INTO reservations VALUES (?, ?, ?, ?, ?)",
              (pass_id, hub_name, created_at, expires_at, "ACTIVE"))
    
    conn.commit()
    conn.close()
    return pass_id, "Success"

# Cached Graph Loader (Optimized bounding box for central Jaipur)
@st.cache_data(show_spinner=False)
def load_street_graph():
    north, south, east, west = 26.9400, 26.8700, 75.8400, 75.7700
    return ox.graph_from_bbox(bbox=(north, south, east, west), network_type="drive")

# Fetch Current Hub Data
def get_hubs():
    conn = sqlite3.connect("navipark.db")
    c = conn.cursor()
    c.execute("SELECT name, lat, lon, total_slots, occupied FROM hubs")
    rows = c.fetchall()
    conn.close()
    hubs = {}
    for name, lat, lon, total, occupied in rows:
        hubs[name] = {"lat": lat, "lon": lon, "total_slots": total, "occupied": occupied}
    return hubs

# ---------------------------------------------------------
# UI TABS SETUP
# ---------------------------------------------------------
tab1, tab2 = st.tabs(["🚗 Driver Route & Booking", "🛡️ Gate Verification Scanner"])

# ---------------------------------------------------------
# TAB 1: DRIVER ROUTING & REAL RESERVATION
# ---------------------------------------------------------
with tab1:
    st.sidebar.header("📍 Route Settings")
    origin_address = st.sidebar.text_input("Origin Address / Landmark", "MI Road, Jaipur")
    
    parking_spots = get_hubs()
    selected_parking = st.sidebar.selectbox("Select Parking Destination", list(parking_spots.keys()))

    if st.sidebar.button("Calculate Route & Reserve Slot"):
        # Reserve slot in DB
        pass_id, res_message = create_reservation(selected_parking)
        
        if not pass_id:
            st.error(f"Reservation Failed: {res_message}")
        else:
            with st.spinner("Fetching map network and computing optimal Dijkstra path..."):
                try:
                    # Refresh Hub Data after reservation
                    parking_spots = get_hubs()
                    
                    # Geocoding Origin
                    geolocator = Nominatim(user_agent="navipark_jaipur_app")
                    loc_origin = geolocator.geocode(origin_address + ", Jaipur, India")
                    
                    if loc_origin:
                        orig_lat, orig_lon = loc_origin.latitude, loc_origin.longitude
                    else:
                        orig_lat, orig_lon = 26.9124, 75.7873  # Fallback location

                    dest_lat = parking_spots[selected_parking]["lat"]
                    dest_lon = parking_spots[selected_parking]["lon"]

                    # Load Map Network & Run Dijkstra
                    G = load_street_graph()
                    orig_node = ox.distance.nearest_nodes(G, orig_lon, orig_lat)
                    dest_node = ox.distance.nearest_nodes(G, dest_lon, dest_lat)

                    route = nx.shortest_path(G, orig_node, dest_node, weight="length")
                    route_length_m = nx.shortest_path_length(G, orig_node, dest_node, weight="length")
                    route_km = route_length_m / 1000.0
                    co2_saved_kg = round(route_km * 0.12, 2)

                    # Display Metrics
                    col1, col2, col3, col4 = st.columns(4)
                    spot_data = parking_spots[selected_parking]
                    avail_slots = spot_data["total_slots"] - spot_data["occupied"]
                    
                    col1.metric("Distance", f"{route_km:.2f} km")
                    col2.metric("Available Slots", f"{avail_slots} / {spot_data['total_slots']}")
                    col3.metric("Est. CO₂ Offset", f"{co2_saved_kg} kg")
                    col4.metric("Spot Status", "Reserved", delta_color="normal")

                    st.markdown("---")

                    map_col, pass_col = st.columns([2, 1])

                    with map_col:
                        st.subheader("🗺️ Optimal Route Visualization")
                        m = folium.Map(location=[orig_lat, orig_lon], zoom_start=13, tiles="CartoDB positron")
                        folium.Marker([orig_lat, orig_lon], popup="Origin", icon=folium.Icon(color="green", icon="play")).add_to(m)
                        folium.Marker([dest_lat, dest_lon], popup=selected_parking, icon=folium.Icon(color="red", icon="parking")).add_to(m)

                        route_coords = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in route]
                        folium.PolyLine(route_coords, color="#1E3A8A", weight=5, opacity=0.8).add_to(m)
                        st_folium(m, width=700, height=450)

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
                        st.success("Slot locked in database for 30 minutes!")

                except Exception as e:
                    st.error(f"Error processing route calculation: {str(e)}")
    else:
        st.info("👈 Set your origin and parking hub in the sidebar, then click **Calculate Route & Reserve Slot**.")

# ---------------------------------------------------------
# TAB 2: GATE VERIFICATION SCANNER
# ---------------------------------------------------------
with tab2:
    st.subheader("🛡️ Automated Entry Gate Verification")
    st.write("Simulate scanning or entering a pass ID at the physical entrance barrier.")
    
    verify_id = st.text_input("Enter Pass ID to Validate (e.g., NPJ-2026...)")
    
    if st.button("Verify Pass at Gate"):
        if verify_id:
            conn = sqlite3.connect("navipark.db")
            c = conn.cursor()
            c.execute("SELECT hub_name, expires_at, status FROM reservations WHERE pass_id = ?", (verify_id.strip(),))
            record = c.fetchone()
            
            if record:
                hub, expires, status = record
                exp_time = datetime.datetime.fromisoformat(expires)
                
                if datetime.datetime.now() < exp_time and status == "ACTIVE":
                    st.success(f"✅ PASS VALID! Access Granted for **{hub}**.")
                    # Mark pass as used
                    c.execute("UPDATE reservations SET status = 'USED' WHERE pass_id = ?", (verify_id.strip(),))
                    conn.commit()
                elif status == "USED":
                    st.warning("⚠️ PASS ALREADY USED! Access Denied.")
                else:
                    st.error("❌ PASS EXPIRED! Access Denied.")
            else:
                st.error("❌ INVALID PASS ID! Record not found in database.")
            conn.close()
        else:
            st.warning("Please enter a valid Pass ID.")
