# FS2020-2024_Google Earth
merges FS2020-2024 with Google Earth. 

🌎 MSFS Geography Flight Sync
A high-frequency telemetry exchange for Microsoft Flight Simulator (2020/2024).

This utility creates a synchronized flight environment between a Host (Server) and a Guest (Client). Unlike standard one-way trackers, this program uses a bidirectional "Push/Pull" architecture to ensure both users are visible in a shared Google Earth workspace.

⚙️ The "Push/Pull" Architecture
The program operates on a Server-Client model designed for low-latency geography visualization:

The Host (The Server): * Acts as the central data hub.

Maintains a persistent Flask-based registry of flight coordinates.

Hosts the Master KML file that Google Earth monitors.

The Guest (The Active Link):

Pulls: Constantly fetches the Host's live altitude, heading, and coordinates.

Pushes: Uploads its own live telemetry to the Host's server.

Result: Both aircraft appear in real-time on the same Google Earth map, allowing for formation flying and guided geography tours.

🚀 Key Features
Bidirectional Synchronization: See the Host and the Guest simultaneously.

Google Earth Pro Integration:  3D aircraft icons and live-updating flight trails. Flight trails can be turned on or off, always recording.  
Can save a track at any point, and start a new one. 

Automated Config: The .bat launcher handles the network handshake—no coding required.

Telemetry Overlay: Real-time HUD data (Airspeed, Altitude) displayed directly in Google Earth.

📥 Getting Started
Download & Extract: Get the Geography_Sync.zip from the Releases page.

Launch: Run Start_Flight.bat.

Choose Role: * Host: Select this if you are the primary server .

Guest: Select this to connect to a Host. Enter the Host's IP address when prompted.

Sync: Ensure Google Earth Pro is open; the "Network Link" will automatically begin fetching the shared flight data.

📂 File Inventory
NS2.exe: The compiled Python engine (Flask/SimConnect).

Start_Flight.bat: The "Smart Launcher" for IP configuration.

simconnect.dll: The internal bridge to Microsoft Flight Simulator.
