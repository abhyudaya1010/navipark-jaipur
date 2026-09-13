# ai_mobility_strategist.py
def generate_mobility_strategy(hub_telemetry: dict, hour: int, day_of_week: int) -> dict:
    """
    Synthesizes global corridor telemetry into actionable urban mobility intelligence.
    """
    total_cap = sum(d["cap"] for d in hub_telemetry.values())
    total_occ = sum(d["occ"] for d in hub_telemetry.values())
    global_load = round((total_occ / total_cap) * 100, 1) if total_cap > 0 else 0
    
    critical_hubs = [k.replace("_", " ") for k, v in hub_telemetry.items() if v["pct"] >= 85]
    heavy_hubs = [k.replace("_", " ") for k, v in hub_telemetry.items() if 65 <= v["pct"] < 85]
    
    actions = []
    
    if critical_hubs:
        actions.append({
            "vector": "SURGE & RELIEF",
            "priority": "CRITICAL",
            "scope": ", ".join(critical_hubs),
            "directive": "Deploy dynamic overflow pricing (+40%), activate JDA feeder micro-shuttles, push VMS diversion routing."
        })
    elif heavy_hubs:
        actions.append({
            "vector": "LOAD BALANCING",
            "priority": "ELEVATED",
            "scope": ", ".join(heavy_hubs),
            "directive": "Adjust green-wave signal offsets on adjacent corridors by +15s to throttle inbound inflow."
        })
    else:
        actions.append({
            "vector": "NOMINAL FLOW",
            "priority": "OPTIMAL",
            "scope": "Jaipur Urban Grid",
            "directive": "Standard adaptive signal phasing active. Maintain baseline eco-routing profiles."
        })
        
    if 8 <= hour <= 10 or 17 <= hour <= 20:
        actions.append({
            "vector": "PEAK WINDOW",
            "priority": "ADVISORY",
            "scope": "Commuter Arterials",
            "directive": "Peak traffic inflection window. Increase incentive weighting for Sindhi Camp / JLN metro transfer lots."
        })
    elif 0 <= hour <= 5:
        actions.append({
            "vector": "MAINTENANCE WINDOW",
            "priority": "INFO",
            "scope": "All Nodes",
            "directive": "Low-occupancy window optimal for automated LiDAR calibration and deep-cleaning cycles."
        })

    grid_status = "CRITICAL" if critical_hubs else ("HEAVY" if heavy_hubs else "OPTIMAL")
    
    return {
        "global_load_factor": global_load,
        "grid_status": grid_status,
        "active_advisories": actions
    }
