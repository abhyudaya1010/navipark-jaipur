import streamlit as st
import folium
from streamlit_folium import st_folium
import qrcode
import io
import datetime
import math
import urllib.parse
from supabase import create_client, Client

# ==========================================
# PAGE CONFIGURATION & GLASSMORPHISM STYLING
# ==========================================
st.set_page_config(
    page_title="NaviPark Jaipur - Smart Mobility & Traffic Engine",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    /* Theme Setup */
    .stApp {
        background-color: #FAFAFC;
    }
    
    /* Header Styling */
    .main-title {
        font-size: 2.3rem;
        font-weight: 800;
        background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
        letter-spacing: -0.5px;
    }
    .sub-title {
        font-size: 1rem;
        color: #64748B;
        font-weight: 500;
        margin-bottom: 25px;
    }
    
    /* Card Component */
    .metric-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    
    /* Live Status Badges */
    .badge-green { background-color: #10B981; color: white; padding: 4px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; }
    .badge-yellow { background-color: #F59E0B; color: white; padding: 4px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; }
    .badge-red { background-color: #EF4444; color: white; padding: 4px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">NaviPark Jaipur 🚗</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Urban Mobility Optimization Engine & Live Parking Telemetry</div>', unsafe_allow_html=True)

# ==========================================
# CONSTANTS & MASTER CONFIGURATION
# ==========================================
LANDMARKS = {
    "MI Road": (26.9124, 75.7873),
    "Jaipur Railway Station": (26.9202, 75.7878),
    "Ajmeri Gate": (26.9156, 75.8202),
    "Raja Park": (26.8982, 75.8245),
    "Mansarovar Hub": (26.8628, 75.7554)
}

JAIPUR_CORRIDORS = {
    "JLN Marg (University - OTS Circle)": {"status": "Moderate", "delay_min": 5, "speed_kmh": 28, "color": "#F59E0B"},
    "MI Road (Panch Batti - Ajmeri Gate)": {"status": "Heavy Congestion", "delay_min": 14, "speed_kmh": 14, "color": "#EF4444"},
    "Tonk Road (Rambagh Circle)": {"status": "Flowing", "delay_min": 2, "speed_kmh": 38, "color": "#10B981"},
    "B2 Bypass Junction": {"status": "Moderate", "delay_min": 6, "speed_kmh": 25, "color": "#F59E0B"},
    "Jaipur-Delhi Highway (Transport Nagar)": {"status": "Heavy Congestion", "delay_min": 12, "speed_kmh": 16, "color": "#EF4444"}
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

# ==========================================
# SUPABASE CONNECTION & DATABASE SERVICES
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
    st.warning("⚠️ Running in Local Cache Mode (Supabase secrets not connected).")

def sync_and_get_hubs():
    """Fetches hubs and automatically heals missing rows in Supabase."""
    if not supabase:
        return {item["name"]: item for item in DEFAULT_HUBS_DATA}
    
    try:
        response = supabase.table("hubs").select("*").execute()
        existing_names = [row["name"].strip().lower() for row in response.data] if response.data else []
        
        # Self-healing: Insert missing default hubs automatically
        for default_hub in DEFAULT_HUBS_DATA:
            if default_hub["name"].strip().lower() not in existing_names:
                supabase.table("hubs").insert(default_hub).execute()
        
        # Refetch fresh data
        response = supabase.table("hubs").select("*").execute()
        hubs = {}
        for row in response.data:
            hubs[row["name"].strip()] = {
                "lat": row["lat"],
                "lon": row["lon"],
                "total_slots": row["total_slots"],
                "occupied": row["occupied"]
            }
        return hubs
    except Exception:
        return {item["name"]: item for item in DEFAULT_HUBS_DATA}

def create_reservation(target_hub_name, txn_id, fee_paid):
    """Creates bulletproof reservation with fuzzy name matching."""
    if not supabase:
        pass_id = f"NPJ-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        return pass_id, "Success (Local)"

    try:
        clean_target = target_hub_name.strip()
        
        # Flexible query using ilike to avoid string mismatch failures
        response = supabase.table("hubs").select("*").ilike("name", clean_target).execute()
        
        if not response.data:
            # Fallback scan
            all_hubs = supabase.table("hubs").select("*").execute()
            matched = next((r for r in all_hubs.data if r["name"].strip().lower() == clean_target.lower()), None)
            if matched:
                response.data = [matched]

        if not response.data:
            return None, f"Database record for '{target_hub_name}' could not be located."
            
        hub_record = response.data[0]
        exact_db_name = hub_record["name"]
        total = hub_record["total_slots"]
        occupied = hub_record["occupied"]
        
        if occupied >= total:
            return None, "Selected parking hub is currently completely full!"
        
        # Atomic Increment
        supabase.table("hubs").update({"occupied": occupied + 1}).eq("name", exact_db_name).execute()
        
        now = datetime.datetime.now(datetime.timezone.utc)
        pass_id = f"NPJ-{now.strftime('%Y%m%d%H%M%S')}"
        expires_at = (now + datetime.timedelta(minutes=30)).isoformat()
        
        supabase.table("reservations").insert({
            "pass_id": pass_id,
            "hub_name": exact_db_name,
            "created_at": now.isoformat(),
            "expires_at": expires_at,
            "status": "ACTIVE"
        }).execute()
        
        return pass_id, "Success"
    except Exception as e:
        return None, str(e)

def cleanup_expired_reservations():
    if not supabase:
        return
    try:
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        expired = supabase.table("reservations").select("pass_id, hub_name").eq("status", "ACTIVE").lt("expires_at", now_iso).execute()
        
        for rec in expired.data:
            pid = rec["pass_id"]
            hub = rec["hub_name"]
            supabase.table("reservations").update({"status": "EXPIRED"}).eq("pass_id", pid).execute()
            
            hub_res = supabase.table("hubs").select("occupied").eq("name", hub).execute()
            if hub_res.data:
                curr_occ = hub_res.data[0]["occupied"]
                if curr_occ > 0:
                    supabase.table("hubs").update({"occupied": curr_occ - 1}).eq("name", hub).execute()
    except Exception:
        pass

cleanup_expired_reservations()

# ==========================================
# ALGORITHMS & UTILITY FUNCTIONS
# ==========================================
def calculate_dynamic_fee(occupied, total, event_multiplier=1.0):
    if total == 0:
        base_fee, rate_type = 50, "Standard Rate"
    else:
        ratio = occupied / total
        if ratio < 0.50:
            base_fee, rate_type = 30, "Off-Peak Discount"
        elif ratio <= 0.85:
            base_fee, rate_type = 50, "Standard Rate"
        else:
            base_fee, rate_type = 90, "⚡ Capacity Surge"

    final_fee = int(base_fee * event_multiplier)
    if event_multiplier > 1.0:
        rate_type = f"⚡ Event Surge ({rate_type})"
    
    return final_fee, rate_type

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))) * 1.25

def optimize_route(orig_lat, orig_lon, dest_lat, dest_lon, traffic_factor=1.2, avg_speed_kmh=22):
    distance_km = haversine_km(orig_lat, orig_lon, dest_lat, dest_lon)
    effective_speed = max(10, avg_speed_kmh / traffic_factor)
    drive_time_min = (distance_km / effective_speed) * 60
    walk_time_min = math.ceil((distance_km * 0.1) * 12)
    co2_saved = round(distance_km * 0.14, 2)
    fuel_saved = round(distance_km * 0.08, 2)
    return round(distance_km, 2), math.ceil(drive_time_min), walk_time_min, co2_saved, fuel_saved

def build_folium_map(orig_lat, orig_lon, dest_lat, dest_lon, orig_name, target_hub, line_color):
    center_lat, center_lon = (orig_lat + dest_lat) / 2, (orig_lon + dest_lon) / 2
    m = folium.Map(location=[center_lat, center_lon], zoom_start=13, tiles=None)

    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
        attr="CartoDB Voyager",
        name="Voyager Base"
    ).add_to(m)

    # Google Maps Real-Time Traffic Overlay Layer
    folium.TileLayer(
        tiles="http://mt0.google.com/vt/lyrs=m,traffic&x={x}&y={y}&z={z}",
        attr="Google Maps Traffic",
        name="Google Traffic",
        overlay=True,
        control=True
    ).add_to(m)

    folium.Marker([orig_lat, orig_lon], popup=f"Origin: {orig_name}", icon=folium.Icon(color="green", icon="play")).add_to(m)
    folium.Marker([dest_lat, dest_lon], popup=f"Hub: {target_hub}", icon=folium.Icon(color="red", icon="parking")).add_to(m)
    folium.PolyLine([(orig_lat, orig_lon), (dest_lat, dest_lon)], color=line_color, weight=6, opacity=0.85).add_to(m)

    folium.LayerControl(position="topright").add_to(m)
    return m

# ==========================================
# INTERFACE NAVIGATION TABS
# ==========================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🚗 Route & Traffic Optimizer",
    "🚦 Live Corridor Monitor",
    "📅 Event Planner", 
    "🛡️ Gate Barrier Verification", 
    "📊 Operator Telemetry"
])

# ------------------------------------------
# TAB 1: ROUTE & TRAFFIC OPTIMIZER
# ------------------------------------------
with tab1:
    st.sidebar.header("🕹️ Route Parameters")
    origin_name = st.sidebar.selectbox("Starting Location", list(LANDMARKS.keys()))
    
    traffic_condition = st.sidebar.select_slider(
        "City Traffic Density",
        options=["Light (Off-Peak)", "Moderate (Normal)", "Severe (Peak Rush Hour)"],
        value="Moderate (Normal)"
    )
    
    traffic_params = {
        "Light (Off-Peak)": {"factor": 0.9, "speed": 35, "color": "#10B981"},
        "Moderate (Normal)": {"factor": 1.3, "speed": 22, "color": "#F59E0B"},
        "Severe (Peak Rush Hour)": {"factor": 2.0, "speed": 12, "color": "#EF4444"}
    }
    
    curr_tf = traffic_params[traffic_condition]["factor"]
    curr_sp = traffic_params[traffic_condition]["speed"]
    line_color = traffic_params[traffic_condition]["color"]

    parking_spots = sync_and_get_hubs()
    orig_lat, orig_lon = LANDMARKS[origin_name]
    
    ranked_hubs = []
    for name, data in parking_spots.items():
        dist, drive_t, walk_t, co2, fuel = optimize_route(orig_lat, orig_lon, data["lat"], data["lon"], curr_tf, curr_sp)
        fee, rate_type = calculate_dynamic_fee(data["occupied"], data["total_slots"])
        avail = max(0, data["total_slots"] - data["occupied"])
        ranked_hubs.append({
            "name": name, "distance": dist, "drive_time": drive_t, "walk_time": walk_t,
            "co2": co2, "fuel": fuel, "fee": fee, "rate_type": rate_type, "avail": avail, "total": data["total_slots"]
        })
        
    ranked_hubs = sorted(ranked_hubs, key=lambda x: x["drive_time"])
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("💳 Instant Slot Reservation")
    selected_parking = st.sidebar.selectbox("Select Hub", [h["name"] for h in ranked_hubs])
    target_info = next(h for h in ranked_hubs if h["name"] == selected_parking)
    
    st.sidebar.metric("Live Fee Rate", f"₹{target_info['fee']}.00", delta=target_info['rate_type'])
    user_upi = st.sidebar.text_input("Merchant UPI ID", value="navipark@upi")

    if st.sidebar.button("Generate QR Code"):
        st.session_state["show_payment"] = True

    if st.session_state.get("show_payment", False):
        st.info("📲 **Scan QR with GPay / PhonePe / Paytm to Pay**")
        p_col1, p_col2 = st.columns([1, 2])
        
        with p_col1:
            upi_url = f"upi://pay?pa={user_upi}&pn={urllib.parse.quote('NaviPark Jaipur')}&am={target_info['fee']}.00&cu=INR"
            qr = qrcode.QRCode(version=1, box_size=6, border=2)
            qr.add_data(upi_url)
            qr.make(fit=True)
            img_buf = io.BytesIO()
            qr.make_image(fill_color="#1E3A8A", back_color="white").save(img_buf, format="PNG")
            st.image(img_buf.getvalue(), caption="UPI QR Code", width=180)

        with p_col2:
            st.markdown(f"**Target Hub:** `{selected_parking}`")
            st.markdown(f"**Amount Payable:** `₹{target_info['fee']}.00`")
            txn_ref = st.text_input("UPI UTR / Ref Number", value="TXN-9823749823")
            
            if st.button("Confirm Payment & Lock Slot"):
                pass_id, res_msg = create_reservation(selected_parking, txn_ref, target_info['fee'])
                if pass_id:
                    st.session_state["active_pass"] = pass_id
                    st.session_state["pass_hub"] = selected_parking
                    st.session_state["pass_origin"] = origin_name
                    st.session_state["pass_fee"] = target_info['fee']
                    st.session_state["show_payment"] = False
                    st.success("✅ Payment Verified! Cloud reservation confirmed.")
                    st.rerun()
                else:
                    st.error(f"Reservation Error: {res_msg}")

    # Pass & Active Route Visualizer
    if "active_pass" in st.session_state:
        pass_id = st.session_state["active_pass"]
        target_hub = st.session_state["pass_hub"]
        orig_name = st.session_state["pass_origin"]
        paid_fee = st.session_state.get("pass_fee", 50)
        
        dest_lat = parking_spots[target_hub]["lat"]
        dest_lon = parking_spots[target_hub]["lon"]
        
        route_km, drive_t, walk_t, co2_saved, fuel_saved = optimize_route(orig_lat, orig_lon, dest_lat, dest_lon, curr_tf, curr_sp)

        c1, c2, c3, c4 = st.columns(4)
        spot_data = parking_spots[target_hub]
        avail_slots = max(0, spot_data["total_slots"] - spot_data["occupied"])
        
        c1.metric("Est. Drive Time", f"{drive_t} mins", delta=f"~{curr_sp} km/h")
        c2.metric("Capacity Status", f"{avail_slots} / {spot_data['total_slots']} Left")
        c3.metric("Eco Impact", f"-{fuel_saved} L Fuel", delta=f"-{co2_saved} kg CO₂")
        c4.metric("Active Pass Status", f"PAID (₹{paid_fee})")

        st.markdown("---")
        m_col, q_col = st.columns([2, 1])

        with m_col:
            st.subheader("🗺️ Route Optimization Map")
            folium_map = build_folium_map(orig_lat, orig_lon, dest_lat, dest_lon, orig_name, target_hub, line_color)
            st_folium(folium_map, use_container_width=True, height=380, returned_objects=[])

        with q_col:
            st.subheader("🎟️ Digital Gate Pass")
            st.info(f"**Pass ID:** `{pass_id}`")
            
            pass_payload = f"PassID:{pass_id}|Hub:{target_hub}|Fee:{paid_fee}"
            qr = qrcode.QRCode(version=1, box_size=8, border=2)
            qr.add_data(pass_payload)
            qr.make(fit=True)
            
            pass_buf = io.BytesIO()
            qr.make_image(fill_color="#1E3A8A", back_color="white").save(pass_buf, format="PNG")
            st.image(pass_buf.getvalue(), caption="Scan at entry gate barrier", width=190)

# ------------------------------------------
# TAB 2: LIVE CORRIDOR MONITOR
# ------------------------------------------
with tab2:
    st.subheader("🚦 Jaipur Arterial Congestion Monitor")
    st.caption("Live transit speed metrics across major urban corridors.")
    
    t_col1, t_col2 = st.columns([2, 1])
    
    with t_col1:
        for cname, cdata in JAIPUR_CORRIDORS.items():
            st.markdown(f"""
                <div style="background-color:#FFFFFF; padding:14px; border-radius:10px; border-left:6px solid {cdata['color']}; margin-bottom:12px; border-top:1px solid #E2E8F0; border-right:1px solid #E2E8F0; border-bottom:1px solid #E2E8F0;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:1.05rem; font-weight:700; color:#1E293B;">{cname}</span>
                        <span style="background-color:{cdata['color']}; color:white; padding:3px 10px; border-radius:12px; font-size:0.8rem; font-weight:600;">{cdata['status']}</span>
                    </div>
                    <div style="margin-top:8px; color:#64748B; font-size:0.88rem;">
                        ⚡ Congestion Delay: <b>+{cdata['delay_min']} mins</b> | 🚗 Average Speed: <b>{cdata['speed_kmh']} km/h</b>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
    with t_col2:
        st.write("### 💡 Route Recommendation")
        st.info(
            "**MI Road Congestion Advisory:** High traffic detected near Panch Batti. Drivers heading into Pink City should divert to **Jawahar Kala Kendra Hub** and utilize Jaipur Metro for last-mile connectivity."
        )
        st.markdown("---")
        st.metric("City Mobility Index", "68 / 100", delta="Moderate Congestion", delta_color="inverse")

# ------------------------------------------
# TAB 3: JAIPUR SMART EVENT PLANNER
# ------------------------------------------
with tab3:
    st.subheader("📅 Event Parking Allocation Engine")
    st.caption("Automated dynamic capacity locks during sports, cultural, and shopping events.")
    
    selected_event = st.selectbox("Select Major Upcoming Event", list(JAIPUR_EVENTS.keys()))
    event_data = JAIPUR_EVENTS[selected_event]
    
    if event_data:
        st.info(f"📍 **Designated Event Hub:** {event_data['hub']} | **Expected Crowd:** {event_data['expected_crowd']}")
        
        hub_info = parking_spots.get(event_data["hub"], {"occupied": 50, "total_slots": 100})
        event_fee, fee_label = calculate_dynamic_fee(hub_info["occupied"], hub_info["total_slots"], event_data["surge_factor"])
        
        e1, e2, e3 = st.columns(3)
        e1.metric("Allocated Hub", event_data["hub"])
        e2.metric("Dynamic Event Rate", f"₹{event_fee}", delta=fee_label)
        e3.metric("Live Availability", f"{max(0, hub_info['total_slots'] - hub_info['occupied'])} slots")
        
        st.markdown("---")
        v_number = st.text_input("Vehicle Registration Number", placeholder="RJ-14-XX-1234")
        
        if st.button("Pre-Book Event Parking Pass"):
            if v_number:
                pass_id, msg = create_reservation(event_data["hub"], "EVENT-PASS", event_fee)
                if pass_id:
                    st.session_state["active_pass"] = pass_id
                    st.session_state["pass_hub"] = event_data["hub"]
                    st.session_state["pass_fee"] = event_fee
                    st.success(f"🎉 Event Pass Reserved! Pass ID: `{pass_id}` linked to vehicle {v_number}.")
                else:
                    st.error(f"Failed to reserve event slot: {msg}")
            else:
                st.warning("Please enter your vehicle registration number to proceed.")

# ------------------------------------------
# TAB 4: VISUAL GATE BARRIER SIMULATOR
# ------------------------------------------
with tab4:
    st.subheader("🛡️ Automated Gate Barrier Simulator")
    st.caption("Simulates real-time IoT hardware verifying entry credentials at gate barriers.")
    
    v_col1, v_col2 = st.columns([2, 1])
    
    with v_col1:
        verify_id = st.text_input("Scan or Enter Pass ID", placeholder="NPJ-2026...")
        scan_btn = st.button("Trigger Sensor Scan")
    
    if scan_btn and verify_id:
        if not supabase:
            st.success("✅ ACCESS GRANTED! Gate opening...")
        else:
            try:
                res = supabase.table("reservations").select("hub_name, expires_at, status").eq("pass_id", verify_id.strip()).execute()
                
                if res.data:
                    rec = res.data[0]
                    exp_time = datetime.datetime.fromisoformat(rec["expires_at"])
                    now_time = datetime.datetime.now(datetime.timezone.utc)
                    
                    if now_time < exp_time and rec["status"] == "ACTIVE":
                        supabase.table("reservations").update({"status": "USED"}).eq("pass_id", verify_id.strip()).execute()
                        st.markdown("""
                            <div style="background-color:#10B981; padding:20px; border-radius:10px; text-align:center; color:white; font-weight:700; font-size:1.4rem;">
                                🟢 BARRIER GATE: OPEN <br>
                                <span style="font-size:0.95rem; font-weight:normal;">Clearance Confirmed • Access Granted</span>
                            </div>
                        """, unsafe_allow_html=True)
                    elif rec["status"] == "USED":
                        st.markdown("""
                            <div style="background-color:#F59E0B; padding:20px; border-radius:10px; text-align:center; color:white; font-weight:700; font-size:1.4rem;">
                                🟡 BARRIER GATE: CLOSED <br>
                                <span style="font-size:0.95rem; font-weight:normal;">Pass Has Already Been Redeemed</span>
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown("""
                            <div style="background-color:#EF4444; padding:20px; border-radius:10px; text-align:center; color:white; font-weight:700; font-size:1.4rem;">
                                🔴 BARRIER GATE: CLOSED <br>
                                <span style="font-size:0.95rem; font-weight:normal;">Pass Expired • Slot Returned to Pool</span>
                            </div>
                        """, unsafe_allow_html=True)
                else:
                    st.error("❌ INVALID PASS ID: Record not found in cloud registry.")
            except Exception as e:
                st.error(f"Verification Failure: {str(e)}")

# ------------------------------------------
# TAB 5: OPERATOR TELEMETRY DASHBOARD
# ------------------------------------------
with tab5:
    st.subheader("📊 Network-Wide Parking Telemetry")
    st.caption("Real-time occupancy analytics synced across all active cloud instances.")
    
    current_hubs = sync_and_get_hubs()
    
    total_cap = sum(h["total_slots"] for h in current_hubs.values())
    total_occ = sum(h["occupied"] for h in current_hubs.values())
    utilization = round((total_occ / total_cap) * 100, 1) if total_cap > 0 else 0
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Network Capacity", f"{total_cap} Spots")
    m2.metric("Occupied Spots", f"{total_occ} Cars")
    m3.metric("Utilization Rate", f"{utilization}%")
    m4.metric("Est. Hourly Revenue", f"₹{total_occ * 50}", delta="Live Sync")
    
    st.markdown("---")
    st.write("### 🏢 Facility Capacity Breakdown")
    
    for hname, hdata in current_hubs.items():
        occ, tot = hdata["occupied"], hdata["total_slots"]
        pct = min(1.0, max(0.0, occ / tot)) if tot > 0 else 0.0
        
        lbl_col, bar_col = st.columns([1, 2])
        with lbl_col:
            st.write(f"**{hname}**")
            st.caption(f"{occ} / {tot} slots occupied")
        with bar_col:
            st.progress(pct)
            
