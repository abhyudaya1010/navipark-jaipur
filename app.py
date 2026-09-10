import streamlit as st
import folium
from streamlit_folium import st_folium
import qrcode
import io
import sqlite3
import datetime
import math

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
# DATABASE INITIALIZATION
# ---------------------------------------------------------
def init_db():
    conn = sqlite3.connect("navipark.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS hubs 
                 (name TEXT PRIMARY KEY, lat REAL, lon REAL, total_slots INTEGER, occupied INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS reservations 
                 (pass_id TEXT PRIMARY KEY, hub_name TEXT, created_at TEXT, expires_at TEXT, status TEXT)''')
    
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

# Pre-set landmarks to avoid slow external API geocoding
LANDMARKS = {
    "MI Road": (26.9124, 75.7873),
    "Jaipur Railway Station": (26.9202, 75.7878),
    "Ajmeri Gate": (26.9156, 75.8202),
    "Raja Park": (26.8982, 75.8245),
    "Mansarovar Hub": (26.8628, 75.7554)
}

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
    
    c.execute("UPDATE hubs SET occupied = occupied + 1 WHERE name = ?", (hub_name,))
    now = datetime.datetime.now()
    pass_id = f"NPJ-{now.strftime('%Y%m%d%H%M%S')}"
    created_at = now.isoformat()
    expires_at = (now + datetime.timedelta(minutes=30)).isoformat()
    
    c.execute("INSERT INTO reservations VALUES (?, ?, ?, ?, ?)",
              (pass_id, hub_name, created_at, expires_at, "ACTIVE"))
    
    conn.commit()
    conn.close()
    return pass_id, "Success"

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

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c * 1.25

# ---------------------------------------------------------
# UI TABS
# ---------------------------------------------------------
tab1, tab2 = st.tabs(["🚗 Driver Route & Booking", "🛡️ Gate Verification Scanner"])

with tab1:
    st.sidebar.header("📍 Route Settings")
    origin_name = st.sidebar.selectbox("Select Starting Point", list(LANDMARKS.keys()))
    
    parking_spots = get_hubs()
    selected_parking = st.sidebar.selectbox("Select Parking Destination", list(parking_spots.keys()))

    if st.sidebar.button("Calculate Route & Reserve Slot"):
        pass_id, res_message = create_reservation(selected_parking)
        
        if not pass_id:
            st.error(f"Reservation Failed: {res_message}")
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
            col4.metric("Spot Status", "Reserved", delta_color="normal")

            st.markdown("---")

            map_col, pass_col = st.columns([2, 1])

            with map_col:
                st.subheader("🗺️ Dynamic Route Map")
                m = folium.Map(location=[(orig_lat + dest_lat)/2, (orig_lon + dest_lon)/2], zoom_start=13, tiles="CartoDB positron")
                folium.Marker([orig_lat, orig_lon], popup=f"Origin: {origin_name}", icon=folium.Icon(color="green", icon="play")).add_to(m)
                folium.Marker([dest_lat, dest_lon], popup=selected_parking, icon=folium.Icon(color="red", icon="parking")).add_to(m)
                folium.PolyLine([(orig_lat, orig_lon), (dest_lat, dest_lon)], color="#1E3A8A", weight=5, opacity=0.8).add_to(m)
                
                # Render Folium without user interaction callback lag
                st_folium(m, width=700, height=400, returned_objects=[])

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
    else:
        st.info("👈 Set your origin and parking hub in the sidebar, then click **Calculate Route & Reserve Slot**.")

with tab2:
    st.subheader("🛡️ Automated Entry Gate Verification")
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
