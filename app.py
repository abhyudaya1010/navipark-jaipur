import streamlit as st
import networkx as nx
import osmnx as ox
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import qrcode
from PIL import Image
import io

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
    .metric-card { background-color: #F3F4F6; padding: 15px; border-radius: 10px; text-align: center; }
    </style>
""", unsafe_allow_html=True)

# App Title Header
st.markdown('<div class="main-title">NaviPark Jaipur 🚗</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Smart Urban Mobility & Dynamic Parking Allocation Engine</div>', unsafe_allow_html=True)

# Cached Graph Loader
@st.cache_data(show_spinner=False)
def load_street_graph(place_name="Jaipur, Rajasthan, India"):
    # Load driveable road network for Jaipur
    return ox.graph_from_place(place_name, network_type="drive")

# Sidebar - User Inputs
st.sidebar.header("📍 Route & Parking Settings")

origin_address = st.sidebar.text_input("Origin Address / Landmark", "MI Road, Jaipur")
destination_address = st.sidebar.text_input("Destination Landmark", "Hawa Mahal, Jaipur")

parking_spots = {
    "Ram Niwas Garden Parking": {"lat": 26.9152, "lon": 75.8198, "total_slots": 120, "occupied": 85},
    "Bapu Bazaar Underground Parking": {"lat": 26.9180, "lon": 75.8230, "total_slots": 80, "occupied": 72},
    "Jawahar Kala Kendra Parking": {"lat": 26.8800, "lon": 75.8080, "total_slots": 150, "occupied": 40},
    "Pink City Central Hub": {"lat": 26.9239, "lon": 75.8267, "total_slots": 100, "occupied": 92}
}

selected_parking = st.sidebar.selectbox("Select Parking Destination", list(parking_spots.keys()))

st.sidebar.markdown("---")
ev_required = st.sidebar.checkbox("Require EV Charging Station")
accessible_required = st.sidebar.checkbox("Wheelchair Accessible")

# Main Action Button
if st.sidebar.button("Calculate Route & Reserve Slot"):
    with st.spinner("Fetching map network and computing optimal Dijkstra path..."):
        try:
            # Geocoding Origin
            geolocator = Nominatim(user_agent="navipark_jaipur_app")
            loc_origin = geolocator.geocode(origin_address + ", Jaipur, India")
            
            if loc_origin:
                orig_lat, orig_lon = loc_origin.latitude, loc_origin.longitude
            else:
                orig_lat, orig_lon = 26.9124, 75.7873 # Fallback location

            dest_lat = parking_spots[selected_parking]["lat"]
            dest_lon = parking_spots[selected_parking]["lon"]

            # Load Map Network
            G = load_street_graph()

            # Find nearest graph nodes
            orig_node = ox.distance.nearest_nodes(G, orig_lon, orig_lat)
            dest_node = ox.distance.nearest_nodes(G, dest_lon, dest_lat)

            # Compute Shortest Path via Dijkstra
            route = nx.shortest_path(G, orig_node, dest_node, weight="length")
            route_length_m = nx.shortest_path_length(G, orig_node, dest_node, weight="length")
            route_km = route_length_m / 1000.0

            # Estimate CO2 Savings vs. Cruising Loops (Avg 0.12 kg CO2 saved per km optimized)
            co2_saved_kg = round(route_km * 0.12, 2)

            # Metrics Row
            col1, col2, col3, col4 = st.columns(4)
            
            spot_data = parking_spots[selected_parking]
            avail_slots = spot_data["total_slots"] - spot_data["occupied"]
            
            col1.metric("Distance", f"{route_km:.2f} km")
            col2.metric("Available Slots", f"{avail_slots} / {spot_data['total_slots']}")
            col3.metric("Est. CO₂ Offset", f"{co2_saved_kg} kg")
            col4.metric("Spot Status", "Available" if avail_slots > 5 else "Limited", delta_color="normal")

            st.markdown("---")

            # Layout Split: Map vs. Pass Generator
            map_col, pass_col = st.columns([2, 1])

            with map_col:
                st.subheader("🗺️ Optimal Route Visualization")
                
                # Render Folium Map
                m = folium.Map(location=[orig_lat, orig_lon], zoom_start=13, tiles="CartoDB positron")

                # Add Origin & Destination Markers
                folium.Marker([orig_lat, orig_lon], popup="Origin", icon=folium.Icon(color="green", icon="play")).add_to(m)
                folium.Marker([dest_lat, dest_lon], popup=selected_parking, icon=folium.Icon(color="red", icon="parking")).add_to(m)

                # Route Coordinates
                route_coords = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in route]
                folium.PolyLine(route_coords, color="#1E3A8A", weight=5, opacity=0.8).add_to(m)

                st_folium(m, width=700, height=450)

            with pass_col:
                st.subheader("🎟️ Digital Entry Pass")
                
                pass_data = f"NaviPark Jaipur\nHub: {selected_parking}\nPass ID: NPJ-{hash(selected_parking) % 100000}\nStatus: Reserved"
                
                qr = qrcode.QRCode(version=1, box_size=8, border=2)
                qr.add_data(pass_data)
                qr.make(fit=True)
                
                qr_img = qr.make_image(fill_color="#1E3A8A", back_color="white")
                buf = io.BytesIO()
                qr_img.save(buf, format="PNG")
                
                st.image(buf.getvalue(), caption="Scan at entry gate", width=200)
                st.success("Slot successfully held for 30 minutes!")

        except Exception as e:
            st.error(f"Error processing route calculation: {str(e)}")

else:
    st.info("👈 Set your origin and parking hub in the sidebar, then click **Calculate Route & Reserve Slot**.")
