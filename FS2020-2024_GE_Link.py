import os, sys, time, math, keyboard
from SimConnect import SimConnect, AircraftRequests

# --- DIRECTORY SETUP ---
if getattr(sys, 'frozen', False): 
    BASE_DIR = os.path.dirname(sys.executable)
else: 
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- CONFIGURATION LOADING ---
def load_altitudes():
    config_path = os.path.join(BASE_DIR, "config.txt")
    default_alts =  [219000, 27359, 54718, 109436]
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                content = f.read().strip()
                if content:
                    return [float(x.strip()) for x in content.split(",") if x.strip()]
        except: pass
    if not os.path.exists(config_path):
        with open(config_path, "w") as f:
            f.write(", ".join(map(str, default_alts)))
    return default_alts

# Global Config
CAM_ALTITUDES = load_altitudes()
TRAIL_MAX_POINTS = math.inf
REFRESH_RATE = 0.1
PATHS = {
    "link": os.path.join(BASE_DIR, "FS2020_GE_Link.kml"),
    "cam":  os.path.join(BASE_DIR, "Moving Map.kml"),
    "pos":  os.path.join(BASE_DIR, "Aircraft_position.kml"),
    "lab":  os.path.join(BASE_DIR, "Telemetry.kml"),
    "trl":  os.path.join(BASE_DIR, "Flight Trail.kml") 
}
ARCHIVE_DIR = os.path.join(BASE_DIR, "Archived_Trails")
KML_WRAP = '<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document>{}</Document></kml>'

def write_kml(file_path, content):
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(KML_WRAP.format(content))
    except Exception as e:
        print(f"\n[FILE ERROR] {os.path.basename(file_path)}: {e}")

def update_master_link(lat, lon, hdg, alt_range):
    # Rewriting the master link with the new LookAt forces GE to update the view
    master_link = f'''<name>FS2020 Live Tracker</name>
        <visibility>1</visibility><open>1</open>
        <LookAt><longitude>{lon}</longitude><latitude>{lat}</latitude><range>{alt_range}</range><heading>{hdg}</heading></LookAt>
        <NetworkLink><name>Moving Map (Auto-Zoom)</name><visibility>1</visibility><flyToView>1</flyToView>
            <Link><href>Moving Map.kml</href> <refreshMode>onInterval</refreshMode><refreshInterval>0.5</refreshInterval></Link></NetworkLink>
        <NetworkLink><name>Flight Trail</name><visibility>1</visibility>
            <Link><href>Flight Trail.kml</href> <refreshMode>onInterval</refreshMode><refreshInterval>.5</refreshInterval></Link></NetworkLink>
        <NetworkLink><name>Position Icon</name><visibility>1</visibility>
            <Link><href>Aircraft_position.kml</href><refreshMode>onInterval</refreshMode><refreshInterval>0.5</refreshInterval></Link></NetworkLink>
        <NetworkLink><name>Telemetry </name><visibility>0</visibility>
            <Link><href>Telemetry.kml</href><refreshMode>onInterval</refreshMode><refreshInterval>1</refreshInterval></Link></NetworkLink>'''
    write_kml(PATHS["link"], master_link)

def main():
    sm = None
    while not sm:
        try: 
            sm = SimConnect(); aq = AircraftRequests(sm, _time=1)
            print("CONNECTED - Waiting for GPS...")
        except: 
            print("Waiting for MSFS..."); time.sleep(3)

    lat, lon, hdg_raw = None, None, None
    while any(v is None for v in [lat, lon, hdg_raw]):
        lat, lon, hdg_raw = aq.get("PLANE_LATITUDE"), aq.get("PLANE_LONGITUDE"), aq.get("PLANE_HEADING_DEGREES_TRUE")
        time.sleep(0.5)

    hdg = math.degrees(hdg_raw) % 360
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    for key in ["cam", "pos", "lab", "trl"]: write_kml(PATHS[key], "")
    
    update_master_link(lat, lon, hdg, CAM_ALTITUDES[0])
    os.startfile(PATHS["link"])

    trail, alt_idx, last_key_time = [], 0, 0
    try:
        while True:
            lat, lon, alt_ft, hdg_raw, gs_raw = aq.get("PLANE_LATITUDE"), aq.get("PLANE_LONGITUDE"), aq.get("PLANE_ALTITUDE"), aq.get("PLANE_HEADING_DEGREES_TRUE"), aq.get("GPS_GROUND_SPEED")

            if any(v is None for v in [lat, lon, alt_ft, hdg_raw, gs_raw]):
                time.sleep(0.1); continue

            hdg = math.degrees(hdg_raw) % 360
            gs_kts = gs_raw * 1.94384

            if keyboard.is_pressed('p') and (time.time() - last_key_time > 1.0):
                alt_idx = (alt_idx + 1) % len(CAM_ALTITUDES)
                last_key_time = time.time()
                update_master_link(lat, lon, hdg, CAM_ALTITUDES[alt_idx])
                print(f"\n[ZOOM] New Range: {CAM_ALTITUDES[alt_idx]}m")

            # Camera KML update
            write_kml(PATHS["cam"], f'<LookAt><longitude>{lon}</longitude><latitude>{lat}</latitude><heading>{hdg}</heading><tilt>0</tilt><range>{CAM_ALTITUDES[alt_idx]}</range><altitudeMode>relativeToGround</altitudeMode></LookAt>')
            
            # Icon and Label updates
            write_kml(PATHS["pos"], f'<Style id="p"><IconStyle><heading>{hdg}</heading><Icon><href>root://icons/palette-2.png?x=64&amp;y=0</href></Icon></IconStyle></Style><Placemark><styleUrl>#p</styleUrl><Point><altitudeMode>relativeToGround</altitudeMode><coordinates>{lon},{lat},30</coordinates></Point></Placemark>')
            write_kml(PATHS["lab"], f'<Style id="h"><IconStyle><scale>0</scale></IconStyle></Style><Placemark><name>{gs_kts:.0f} kts | {alt_ft:.0f} ft</name><styleUrl>#h</styleUrl><Point><altitudeMode>relativeToGround</altitudeMode><coordinates>{lon},{lat},40</coordinates></Point></Placemark>')
            
            trail.append(f"{lon:.7f},{lat:.7f},5")
            
            write_kml(PATHS["trl"], f'<Style id="t"><LineStyle><color>ff00ffff</color><width>3</width></LineStyle></Style><Placemark><styleUrl>#t</styleUrl><LineString><altitudeMode>relativeToGround</altitudeMode><coordinates>{" ".join(trail)}</coordinates></LineString></Placemark>')

            print(f"\rLAT: {lat:.4f} LON: {lon:.4f} | ZOOM: {CAM_ALTITUDES[alt_idx]}m", end="")
            time.sleep(REFRESH_RATE)
            
    except KeyboardInterrupt:
        print("\n\n--- STOPPED ---")
        save_choice = input("Save trail? (y/n): ").lower()
        if save_choice == 'y':
            name = input("Name: ").strip() or f"Trail_{time.strftime('%H%M%S')}"
            if os.path.exists(PATHS["trl"]):
                os.rename(PATHS["trl"], os.path.join(ARCHIVE_DIR, f"{name}.kml"))
        sys.exit(0)

if __name__ == "__main__":
    main()