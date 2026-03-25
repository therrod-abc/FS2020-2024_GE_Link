import os, sys, time, math, threading, requests, configparser, logging, keyboard, shutil
from flask import Flask, request, send_from_directory
from SimConnect import SimConnect, AircraftRequests

# --- 1. SETUP & PATHS ---
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

LOCAL_DIR = os.path.join(BASE_DIR, "Local_Files")
REMOTE_DIR = os.path.join(BASE_DIR, "Remote_Files")
ARCHIVE_DIR = os.path.join(BASE_DIR, "Archived_Trails")
for d in [LOCAL_DIR, REMOTE_DIR, ARCHIVE_DIR]: os.makedirs(d, exist_ok=True)

# --- 2. CONFIG & ALTITUDE FILE MGMT ---
CONFIG_PATH = os.path.join(BASE_DIR, "config.ini")
ALT_CFG_PATH = os.path.join(BASE_DIR, "AltitudeCfg.txt")

def initialize_altitude_file():
    default_alts = [450000, 219000, 27359, 54718, 109436]
    if not os.path.exists(ALT_CFG_PATH):
        with open(ALT_CFG_PATH, "w") as f:
            f.write("\n".join(map(str, default_alts)))
        return default_alts
    with open(ALT_CFG_PATH, "r") as f:
        user_alts = [int(line.strip()) for line in f if line.strip().isdigit()]
        return user_alts if user_alts else default_alts

def initialize_config():
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_PATH):
        is_h = input("Is this machine SERVER? (y/n): ").lower().strip() == 'y'
        tip = "127.0.0.1" if is_h else input("Enter Server IP: ").strip()
        prt = input("Port (80): ").strip() or "80"
        config['SETTINGS'] = {'IS_HOST': str(is_h), 'HOST_IP': tip, 'PORT': prt}
        with open(CONFIG_PATH, "w") as f: config.write(f)
    config.read(CONFIG_PATH)
    return config.getboolean('SETTINGS', 'IS_HOST'), config.get('SETTINGS', 'HOST_IP'), config.getint('SETTINGS', 'PORT')

IS_HOST, HOST_IP, PORT = initialize_config()
CAM_ALTS = initialize_altitude_file() 
KML_WRAP = '<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document>\n{}\n</Document></kml>'

# --- 3. MATH UTILS ---
def haversine(lat1, lon1, lat2, lon2):
    R = 3440.065 
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))

# --- 4. KML ENGINE ---
def write_kml(folder, filename, body):
    try:
        with open(os.path.join(folder, filename), "w", encoding="utf-8") as f:
            f.write(KML_WRAP.format(body))
    except: pass

def init_master_link():
    master_path = os.path.join(BASE_DIR, "FS_Network_Master.kml")
    content = f'''<name>FS Network Sync ({'Host' if IS_HOST else 'Guest'})</name> <open>1</open>
        <Folder><name>My Aircraft</name><open>1</open>
            <NetworkLink><name>1. Moving Map (Auto-Zoom)</name><visibility>1</visibility><flyToView>1</flyToView>
                <Link><href>Local_Files/cam.kml</href><refreshMode>onInterval</refreshMode><refreshInterval>0.5</refreshInterval></Link></NetworkLink>
            <NetworkLink><name>2. Position Icon</name><visibility>1</visibility>
                <Link><href>Local_Files/pos.kml</href><refreshMode>onInterval</refreshMode><refreshInterval>0.5</refreshInterval></Link></NetworkLink>
            <NetworkLink><name>3. Flight Trail</name><visibility>1</visibility>
                <Link><href>Local_Files/trl.kml</href><refreshMode>onInterval</refreshMode><refreshInterval>0.5</refreshInterval></Link></NetworkLink>
            <NetworkLink><name>4. Telemetry</name><visibility>1</visibility>
                <Link><href>Local_Files/lab.kml</href><refreshMode>onInterval</refreshMode><refreshInterval>1</refreshInterval></Link></NetworkLink>
        </Folder>
        <Folder><name>Partner</name><open>1</open>
            <NetworkLink><name>Remote Plane</name><Link><href>Remote_Files/Remote_Pos.kml</href><refreshMode>onInterval</refreshMode><refreshInterval>0.5</refreshInterval></Link></NetworkLink>
        </Folder>'''
    with open(master_path, "w") as f: f.write(KML_WRAP.format(content))
    os.startfile(master_path)

# --- 5. NETWORKING ---
app = Flask(__name__)
@app.route('/upload', methods=['POST'])
def upload():
    request.files['file'].save(os.path.join(REMOTE_DIR, "Remote_Pos.kml"))
    return "OK"

@app.route('/download')
def download():
    return send_from_directory(LOCAL_DIR, "pos.kml")

def network_worker():
    if IS_HOST: return
    url = f"http://{HOST_IP}:{PORT}"
    while True:
        try:
            with open(os.path.join(LOCAL_DIR, "pos.kml"), 'rb') as f:
                requests.post(f"{url}/upload", files={'file': f}, timeout=1)
            r = requests.get(f"{url}/download", timeout=1)
            if r.status_code == 200:
                with open(os.path.join(REMOTE_DIR, "Remote_Pos.kml"), "w") as f: f.write(r.text)
        except: pass
        time.sleep(0.5)

# --- 6. MAIN ---
def main():
    init_master_link()
    if IS_HOST:
        threading.Thread(target=lambda: app.run(host='0.0.0.0', port=PORT), daemon=True).start()
    else:
        threading.Thread(target=network_worker, daemon=True).start()

    sm = None
    alt_idx, last_key = 0, 0

    while True:
        trail, total_dist, last_pos = [], 0.0, None
        print("\n[SYSTEM] Ready for new flight tracking...")

        try:
            while True:
                try:
                    if not sm:
                        try: 
                            sm = SimConnect(); aq = AircraftRequests(sm, _time=1)
                            print("\nCONNECTED TO MSFS")
                        except: time.sleep(2); continue

                    lat, lon, alt = aq.get("PLANE_LATITUDE"), aq.get("PLANE_LONGITUDE"), aq.get("PLANE_ALTITUDE")
                    hdg = math.degrees(aq.get("PLANE_HEADING_DEGREES_TRUE") or 0) % 360
                    gs = (aq.get("GPS_GROUND_SPEED") or 0) * 1.94384

                    if lat and lon:
                        if last_pos:
                            total_dist += haversine(last_pos[0], last_pos[1], lat, lon)
                        last_pos = (lat, lon)

                        if keyboard.is_pressed('p') and (time.time() - last_key > 1.0):
                            alt_idx = (alt_idx + 1) % len(CAM_ALTS)
                            last_key = time.time()
                            print(f"\n[ZOOM] {CAM_ALTS[alt_idx]}m")

                        write_kml(LOCAL_DIR, "cam.kml", f'<LookAt>\n<longitude>{lon}</longitude>\n<latitude>{lat}</latitude>\n<heading>{hdg}</heading>\n<tilt>0</tilt>\n<range>{CAM_ALTS[alt_idx]}</range>\n<altitudeMode>relativeToGround</altitudeMode>\n</LookAt>')
                        write_kml(LOCAL_DIR, "pos.kml", f'<Style id="p"><IconStyle><heading>{hdg}</heading><Icon><href>root://icons/palette-2.png?x=64&amp;y=0</href></Icon></IconStyle></Style>\n<Placemark><styleUrl>#p</styleUrl><Point><altitudeMode>relativeToGround</altitudeMode><coordinates>{lon},{lat},30</coordinates></Point></Placemark>')
                        write_kml(LOCAL_DIR, "lab.kml", f'<Style id="h"><IconStyle><scale>0</scale></IconStyle></Style>\n<Placemark><name>{gs:.0f} kts | {alt:.0f} ft | {total_dist:.1f} nm</name><styleUrl>#h</styleUrl><Point><altitudeMode>relativeToGround</altitudeMode><coordinates>{lon},{lat},40</coordinates></Point></Placemark>')
                        
                        trail.append(f"{lon:.7f},{lat:.7f},10")
                        # Join with \n so trl.kml is readable in Notepad++
                        formatted_trail = "\n".join(trail)
                        write_kml(LOCAL_DIR, "trl.kml", f'<Style id="t"><LineStyle><color>ff00ffff</color><width>3</width></LineStyle></Style>\n<Placemark><styleUrl>#t</styleUrl><LineString><altitudeMode>relativeToGround</altitudeMode><coordinates>\n{formatted_trail}\n</coordinates></LineString></Placemark>')
                        
                        print(f"\rFLYING: {lat:.4f}, {lon:.4f} | {total_dist:.1f}nm | ZOOM: {CAM_ALTS[alt_idx]}m", end="")
                    time.sleep(0.1)
                except Exception:
                    sm = None; time.sleep(1)

        except KeyboardInterrupt:
            print("\n\n--- INTERRUPT DETECTED ---")
            
            if input("Save current track? (y/n): ").lower().strip() == 'y':
                def_name = f"Flight_{time.strftime('%Y%m%d_%H%M%S')}"
                name = input(f"Enter Name (Default: {def_name}): ").strip() or def_name
                
                # Create final readable KML with metadata
                formatted_coords = "\n".join(trail)
                final_body = (
                    f'<Style id="t"><LineStyle><color>ff00ffff</color><width>3</width></LineStyle></Style>\n'
                    f'<Placemark>\n'
                    f'  <name>{name}</name>\n'
                    f'  <description>Distance: {total_dist:.2f} nm</description>\n'
                    f'  <styleUrl>#t</styleUrl>\n'
                    f'  <LineString>\n'
                    f'    <altitudeMode>relativeToGround</altitudeMode>\n'
                    f'    <coordinates>\n{formatted_coords}\n</coordinates>\n'
                    f'  </LineString>\n'
                    f'</Placemark>'
                )
                with open(os.path.join(ARCHIVE_DIR, f"{name}.kml"), "w", encoding="utf-8") as f:
                    f.write(KML_WRAP.format(final_body))
                print(f"Saved: {name}.kml")

            if input("Do you wish to start a new track? (y/n): ").lower().strip() == 'y':
                continue
            else:
                print("Exiting...")
                sys.exit(0)

if __name__ == "__main__":
    main()