import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, "router"))

import streamlit as st
import folium
from streamlit_folium import st_folium
import osmnx as ox
import networkx as nx
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

from router.graph_loader import load_street_graph
from router.parking_sim import generate_parking_zones
from custom_astar import find_smart_parking_route

# ---------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="Smart Parking & GIS Route Planner",
    layout="wide",
    page_icon="🅿️",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# Custom UI Styling (CSS Injection)
# ---------------------------------------------------------
st.markdown("""
<style>
    /* Main App Background & Font */
    .stApp {
        background-color: #0f172a;
        color: #f8fafc;
        font-family: 'Inter', sans-serif;
    }
    
    /* Header Container Styling */
    .main-header {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        padding: 1.5rem 2rem;
        border-radius: 16px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        margin-bottom: 2rem;
    }
    .main-header h1 {
        color: #38bdf8;
        font-weight: 700;
        margin: 0;
        font-size: 2.2rem;
    }
    .main-header p {
        color: #94a3b8;
        margin-top: 0.5rem;
        font-size: 1rem;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #1e293b !important;
        border-right: 1px solid #334155;
    }
    
    /* Metric Card Custom Styling */
    div[data-testid="stMetric"] {
        background: #1e293b;
        border: 1px solid #334155;
        padding: 1rem 1.25rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    div[data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
        font-size: 0.875rem !important;
        font-weight: 600 !important;
    }
    div[data-testid="stMetricValue"] {
        color: #38bdf8 !important;
        font-size: 1.6rem !important;
        font-weight: 700 !important;
    }

    /* Map Box Styling */
    .element-container:has(iframe) {
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid #334155;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Title Banner
# ---------------------------------------------------------
st.markdown("""
<div class="main-header">
    <h1>🅿️ GIS Smart Parking & Navigation Router</h1>
    <p>Multi-objective spatial routing engine for central Jaipur, balancing driving duration, walk distances, traffic density, and real-time spot availability risk.</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Data Loading
# ---------------------------------------------------------
@st.cache_resource
def get_map_data():
    G = load_street_graph()
    parking_df = generate_parking_zones(G)
    return G, parking_df

with st.spinner("Initializing Jaipur GIS Network..."):
    G, parking_df = get_map_data()

geolocator = Nominatim(user_agent="smart_parking_jaipur_app_v10")

# ---------------------------------------------------------
# Sidebar Controls
# ---------------------------------------------------------
st.sidebar.markdown("### 📍 Location Search")
start_address = st.sidebar.text_input("Origin Point", value="Albert Hall Museum, Jaipur")
dest_address = st.sidebar.text_input("Destination Point", value="Ajmeri Gate, Jaipur")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🚦 Navigation Mode")
routing_mode = st.sidebar.radio(
    "Select Routing Engine:",
    ["Smart Parking Search", "Direct Shortest Path"],
    label_visibility="collapsed"
)

if routing_mode == "Smart Parking Search":
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⚙️ Optimization Weights")
    drive_priority = st.sidebar.slider("🚗 Drive Speed Preference", 0.0, 5.0, 1.0, 0.1)
    walk_priority = st.sidebar.slider("🚶 Short Walk Preference", 0.0, 5.0, 2.5, 0.1)
    parking_risk = st.sidebar.slider("🛡️ Guaranteed Spot Priority", 0.0, 30.0, 15.0, 1.0)

# ---------------------------------------------------------
# Geocoding & Node Matching
# ---------------------------------------------------------
@st.cache_data(show_spinner=False)
def geocode_location(address_text):
    try:
        loc = geolocator.geocode(address_text, timeout=10)
        if loc:
            return (loc.latitude, loc.longitude), loc.address
    except Exception:
        pass
    return None, None

coords_start, _ = geocode_location(start_address)
coords_dest, _ = geocode_location(dest_address)

if coords_start is None:
    st.error(f"Could not locate starting point: '{start_address}'. Try adding ', Jaipur' to your query.")
    st.stop()

if coords_dest is None:
    st.error(f"Could not locate destination point: '{dest_address}'. Try adding ', Jaipur' to your query.")
    st.stop()

# Snap to initial nearest nodes
origin_node = ox.distance.nearest_nodes(G, X=coords_start[1], Y=coords_start[0])
dest_node = ox.distance.nearest_nodes(G, X=coords_dest[1], Y=coords_dest[0])

# Validate Distance to Graph Edge
dest_lat = G.nodes[dest_node]['y']
dest_lon = G.nodes[dest_node]['x']
dest_gap = geodesic(coords_dest, (dest_lat, dest_lon)).meters

if dest_gap > 500:
    st.warning(f"Note: Destination is ~{int(dest_gap)} meters from the nearest driving road in the graph.")

# Render Folium Base Map
mid_lat = (coords_start[0] + coords_dest[0]) / 2.0
mid_lon = (coords_start[1] + coords_dest[1]) / 2.0
m = folium.Map(location=[mid_lat, mid_lon], zoom_start=14, tiles="CartoDB dark_matter")

folium.Marker(
    coords_start, 
    popup=f"Origin: {start_address}", 
    icon=folium.Icon(color="blue", icon="play", prefix="fa")
).add_to(m)

folium.Marker(
    coords_dest, 
    popup=f"Destination: {dest_address}", 
    icon=folium.Icon(color="red", icon="flag", prefix="fa")
).add_to(m)

# Route Weight Preference Fallback
weight_attribute = "adjusted_travel_time" if nx.get_edge_attributes(G, "adjusted_travel_time") else "travel_time"

# ---------------------------------------------------------
# Path Engine Execution
# ---------------------------------------------------------
if routing_mode == "Direct Shortest Path":
    try:
        # Verify node connection within main graph; if disconnected, fallback to largest connected subgraph
        if not nx.has_path(G, origin_node, dest_node):
            largest_cc = max(nx.strongly_connected_components(G), key=len)
            G_sub = G.subgraph(largest_cc).copy()
            origin_node = ox.distance.nearest_nodes(G_sub, X=coords_start[1], Y=coords_start[0])
            dest_node = ox.distance.nearest_nodes(G_sub, X=coords_dest[1], Y=coords_dest[0])
            direct_path = nx.shortest_path(G_sub, origin_node, dest_node, weight=weight_attribute)
            drive_time_sec = nx.shortest_path_length(G_sub, origin_node, dest_node, weight=weight_attribute)
        else:
            direct_path = nx.shortest_path(G, origin_node, dest_node, weight=weight_attribute)
            drive_time_sec = nx.shortest_path_length(G, origin_node, dest_node, weight=weight_attribute)
        
        col1, col2 = st.columns(2)
        col1.metric("Routing Engine", "Direct Shortest Path")
        col2.metric("Traffic-Adjusted Drive Time", f"{round(drive_time_sec / 60.0, 1)} mins")

        route_coords = [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in direct_path]
        folium.PolyLine(route_coords, color="#38bdf8", weight=6, opacity=0.9, popup="Direct Path").add_to(m)
    except Exception:
        st.error("No valid driving road path connects these locations in the loaded graph. Try selecting a major nearby landmark.")

else:
    result = find_smart_parking_route(
        G, origin_node, coords_dest, parking_df, 
        alpha=drive_priority, beta=walk_priority, gamma=parking_risk
    )

    if result:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Selected Lot", f"{result['parking_zone']['zone_id']}")
        col2.metric("Drive Time", f"{result['drive_time_mins']} mins")
        col3.metric("Walk Time", f"{result['walk_time_mins']} mins")
        col4.metric("Spot Confidence", f"{int(result['availability_prob'] * 100)}%")

        path_nodes = result["drive_path"]
        route_coords = [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in path_nodes]
        
        # Driving Route Segment (Cyan)
        folium.PolyLine(route_coords, color="#38bdf8", weight=5, opacity=0.8, popup="Drive Path").add_to(m)

        # Walking Route Segment (Dashed Green)
        park_loc = (result["parking_zone"]["lat"], result["parking_zone"]["lon"])
        folium.PolyLine([park_loc, coords_dest], color="#4ade80", weight=4, opacity=0.9, dash_array="6, 8", popup="Walk Path").add_to(m)

        # Parking Destination Marker
        folium.Marker(
            park_loc, 
            popup=f"Parking Lot: {result['parking_zone']['zone_id']}", 
            icon=folium.Icon(color="purple", icon="square-parking", prefix="fa")
        ).add_to(m)
    else:
        st.error("Could not determine an optimal parking lot for this route within the graph radius.")

# ---------------------------------------------------------
# Dynamic Map Display
# ---------------------------------------------------------
st_folium(m, width=1300, height=560, key=f"map_{start_address}_{dest_address}_{routing_mode}")
