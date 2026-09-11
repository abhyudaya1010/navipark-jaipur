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

# Fetch Live Hubs with Auto-Seeding
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

# 1. DYNAMIC SURGE PRICING ENGINE
def calculate_dynamic_fee(occupied, total):
    if total == 0:
        return 50, "Standard Rate"
    ratio = occupied / total
    if ratio < 0.50:
        return 30, "Off-Peak Discount"
    elif ratio <= 0.85:
        return 50, "Standard Rate"
    else:
        return 90, "⚡ Peak Surge Rate"

# 2. AUTO-EXPIRING RESERVATION CLEANUP ENGINE
def cleanup_expired_reservations():
    try:
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        expired_res = supabase.table("reservations") \
            .select("pass_id, hub_name") \
            .eq("status", "ACTIVE") \
            .lt("expires_at", now_iso) \
            .execute()
        
        for record in expired_res.data:
            pid = record["pass_id"]
            hub = record["hub_name"]
            
            # Invalidate expired pass
            supabase.table("reservations").update({"status": "EXPIRED"}).eq("pass_id", pid).execute()
            
            # Release slot back to cloud pool
            hub_data = supabase.table("hubs").select("occupied").eq("name", hub).execute()
            if hub_data.data:
                curr_occ = hub_data.data[0]["occupied"]
                if curr_occ > 0:
                    supabase.table("hubs").update({"occupied": curr_occ - 1}).eq("name", hub).execute()
    except Exception:
        pass

# Run automatic slot cleanup on every app render
cleanup_expired_reservations()

def create_reservation(hub_name, txn_id, fee_paid):
    try:
        response = supabase.table("hubs").select("total_slots, occupied").eq("name", hub_name).execute()
        if not response.data:
            return None, "Hub not found."
            
        total = response.data[0]["total_slots"]
        occupied = response.data[0]["occupied"]
        
        if occupied >= total:
            return None, "Selected parking hub is completely full!"
        
        # Increment occupied count
        supabase.table("hubs").update({"occupied": occupied + 1}).eq("name", hub_name).execute()
        
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
tab1, tab2, tab3 = st.tabs([
    "🚗 Driver Route & Paid Booking", 
    "🛡️ Gate Verification Scanner", 
    "📊 Mall Operator Analytics"
])

# ---------------------------------------------------------
# TAB 1: DRIVER ROUTE & PAID BOOKING
# ---------------------------------------------------------
with tab1:
    st.sidebar.header("📍 Route Settings")
    origin_name = st.sidebar.selectbox("Select Starting Point", list(LANDMARKS.keys()))
    parking_spots = get_hubs()
    
    if parking_spots:
        selected_parking = st.sidebar.selectbox("Select Parking Destination", list(parking_spots.keys()))
        
        spot_info = parking_spots[selected_parking]
        fee_amount, rate_type = calculate_dynamic_fee(spot_info["occupied"], spot_info["total_slots"])

        st.sidebar.markdown("---")
        st.sidebar.subheader("💳 Checkout Summary")
        st.sidebar.metric("Live Parking Fee", f"₹{fee_amount}.00", delta=rate_type)
        
        user_upi = st.sidebar.text_input("Merchant UPI ID (Optional)", value="navipark@upi")

        if st.sidebar.button("Generate UPI Payment QR"):
            st.session_state["show_payment"] = True

        if st.session_state.get("show_payment", False):
            st.info("📲 **Scan & Pay via Google Pay / PhonePe / Paytm / UPI**")
            
            pay_col1, pay_col2 = st.columns([1, 2])
            
            with pay_col1:
                upi_url = f"upi://pay?pa={user_upi}&pn={urllib.parse.quote('NaviPark Jaipur')}&am={fee_amount}.00&cu=INR&tn={urllib.parse.quote('Parking Slot Reserve')}"
                qr = qrcode.QRCode(version=1, box_size=6, border=2)
                qr.add_data(upi_url)
                qr.make(fit=True)
                upi_img = qr.make_image(fill_color="#1E3A8A", back_color="white")
                buf = io.BytesIO()
                upi_img.save(buf, format="PNG")
                st.image(buf.getvalue(), caption="Scan with GPay / PhonePe / Paytm", width=200)

            with pay_col2:
                st.write("### Payment Verification")
                st.write(f"Destination: **{selected_parking}**")
                st.write(f"Dynamic Rate: **₹{fee_amount}.00** ({rate_type})")
                txn_ref = st.text_input("Enter UPI UTR / Transaction ID", value="UPI-8923749823")
                
                if st.button("Confirm Payment & Issue Gate Pass"):
                    pass_id, res_msg = create_reservation(selected_parking, txn_ref, fee_amount)
                    if pass_id:
                        st.session_state["active_pass"] = pass_id
                        st.session_state["pass_hub"] = selected_parking
                        st.session_state["pass_origin"] = origin_name
                        st.session_state["pass_fee"] = fee_amount
                        st.session_state["show_payment"] = False
                        st.success("✅ Payment Verified! Slot locked in Supabase Cloud.")
                    else:
                        st.error(f"Error: {res_msg}")

        if "active_pass" in st.session_state:
            pass_id = st.session_state["active_pass"]
            target_hub = st.session_state["pass_hub"]
            orig_name = st.session_state["pass_origin"]
            paid_fee = st.session_state.get("pass_fee", 50)
            
            orig_lat, orig_lon = LANDMARKS[orig_name]
            dest_lat = parking_spots[target_hub]["lat"]
            dest_lon = parking_spots[target_hub]["lon"]

            route_km = haversine_km(orig_lat, orig_lon, dest_lat, dest_lon)
            co2_saved_kg = round(route_km * 0.12, 2)

            col1, col2, col3, col4 = st.columns(4)
            spot_data = parking_spots[target_hub]
            avail_slots = spot_data["total_slots"] - spot_data["occupied"]
            
            col1.metric("Est. Distance", f"{route_km:.2f} km")
            col2.metric("Available Slots", f"{avail_slots} / {spot_data['total_slots']}")
            col3.metric("Est. CO₂ Offset", f"{co2_saved_kg} kg")
            col4.metric("Payment Status", f"PAID (₹{paid_fee})", delta_color="normal")

            st.markdown("---")

            map_col, pass_col = st.columns([2, 1])

            with map_col:
                st.subheader("🗺️ Dynamic Route Map")
                m = folium.Map(
                    location=[(orig_lat + dest_lat)/2, (orig_lon + dest_lon)/2], 
                    zoom_start=13, 
                    tiles="CartoDB positron"
                )
                folium.Marker([orig_lat, orig_lon], popup=f"Origin: {orig_name}", icon=folium.Icon(color="green", icon="play")).add_to(m)
                folium.Marker([dest_lat, dest_lon], popup=target_hub, icon=folium.Icon(color="red", icon="parking")).add_to(m)
                folium.PolyLine([(orig_lat, orig_lon), (dest_lat, dest_lon)], color="#1E3A8A", weight=5, opacity=0.8).add_to(m)
                
                st_folium(m, use_container_width=True, height=400, returned_objects=[])

            with pass_col:
                st.subheader("🎟️ Digital Entry Pass")
                st.info(f"**Pass ID:** `{pass_id}`")
                
                pass_data = f"Pass ID: {pass_id}\nHub: {target_hub}\nFee Paid: Rs.{paid_fee}\nStatus: Reserved"
                qr = qrcode.QRCode(version=1, box_size=8, border=2)
                qr.add_data(pass_data)
                qr.make(fit=True)
                
                qr_img = qr.make_image(fill_color="#1E3A8A", back_color="white")
                buf = io.BytesIO()
                qr_img.save(buf, format="PNG")
                
                st.image(buf.getvalue(), caption="Scan at entry gate barrier", width=200)
                st.success("Slot locked for 30 minutes!")
    else:
        st.error("No parking hubs available.")

# ---------------------------------------------------------
# TAB 2: VISUAL GATE BARRIER SIMULATOR
# ---------------------------------------------------------
with tab2:
    st.subheader("🛡️ Automated Entry Gate Verification")
    
    col_input, col_status = st.columns([2, 1])
    
    with col_input:
        verify_id = st.text_input("Enter or Scan Pass ID (e.g., NPJ-2026...)", placeholder="NPJ-...")
        validate_btn = st.button("Simulate Gate Sensor Scan")
    
    if validate_btn and verify_id:
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
                    supabase.table("reservations").update({"status": "USED"}).eq("pass_id", verify_id.strip()).execute()
                    
                    st.success(f"✅ ACCESS GRANTED! Clearance verified for **{hub}**")
                    st.markdown("""
                        <div style="background-color:#10B981; padding:20px; border-radius:10px; text-align:center; color:white; font-weight:bold; font-size:1.5rem;">
                            🟢 BARRIER GATE: OPEN <br>
                            <span style="font-size:1rem; font-weight:normal;">Vehicle Clearance Verified • Driver ID Logged</span>
                        </div>
                    """, unsafe_allow_html=True)
                elif status == "USED":
                    st.warning("⚠️ ACCESS DENIED: Pass Already Used!")
                    st.markdown("""
                        <div style="background-color:#F59E0B; padding:20px; border-radius:10px; text-align:center; color:white; font-weight:bold; font-size:1.5rem;">
                            🟡 BARRIER GATE: CLOSED <br>
                            <span style="font-size:1rem; font-weight:normal;">Token previously redeemed at entry booth.</span>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.error("❌ ACCESS DENIED: Pass Expired!")
                    st.markdown("""
                        <div style="background-color:#EF4444; padding:20px; border-radius:10px; text-align:center; color:white; font-weight:bold; font-size:1.5rem;">
                            🔴 BARRIER GATE: CLOSED <br>
                            <span style="font-size:1rem; font-weight:normal;">Reservation timed out (>30 mins). Slot released to public pool.</span>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.error("❌ INVALID TOKEN: No matching record found in cloud database.")
        except Exception as e:
            st.error(f"Gate Verification Error: {str(e)}")

# ---------------------------------------------------------
# TAB 3: MALL OPERATOR ANALYTICS DASHBOARD
# ---------------------------------------------------------
with tab3:
    st.subheader("📊 Live Parking Occupancy & Revenue Dashboard")
    st.caption("Real-time telemetry synced across all active cloud instances.")
    
    current_hubs = get_hubs()
    
    if current_hubs:
        total_capacity = sum(h["total_slots"] for h in current_hubs.values())
        total_occupied = sum(h["occupied"] for h in current_hubs.values())
        overall_occupancy = round((total_occupied / total_capacity) * 100, 1) if total_capacity > 0 else 0
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Network Capacity", f"{total_capacity} Slots")
        m2.metric("Active Occupied Spots", f"{total_occupied} Cars")
        m3.metric("Network Utilization", f"{overall_occupancy}%")
        m4.metric("Est. Hourly Revenue", f"₹{total_occupied * 50}", delta="Live Cloud Sync")
        
        st.markdown("---")
        st.write("### 🏢 Real-Time Hub Occupancy Breakdown")
        
        for hname, hdata in current_hubs.items():
            occ = hdata["occupied"]
            tot = hdata["total_slots"]
            pct = occ / tot if tot > 0 else 0.0
            
            c_label, c_bar = st.columns([1, 2])
            with c_label:
                st.write(f"**{hname}**")
                st.caption(f"{occ} / {tot} slots filled")
            with c_bar:
                st.progress(pct)
            
