import os
import requests
import pandas as pd
from datetime import datetime

LAT_MIN, LAT_MAX = 32.00, 32.04
LON_MIN, LON_MAX = 34.75, 34.81
CSV_FILE = "flights_holon.csv"

def main():
    if not os.path.exists(CSV_FILE) or os.stat(CSV_FILE).st_size == 0:
        pd.DataFrame(columns=["Timestamp", "ICAO24", "Callsign", "Origin_Country", "Longitude", "Latitude", "Altitude_m", "Velocity_kmh"]).to_csv(CSV_FILE, index=False)

    try:
        response = requests.get("https://opensky-network.org/api/states/all", params={"lamin": LAT_MIN, "lamax": LAT_MAX, "lomin": LON_MIN, "lomax": LON_MAX}, timeout=15)
        states = response.json().get("states", []) if response.status_code == 200 else []
    except Exception:
        states = []
    
    if not states:
        print("No flights over Holon right now.")
        return
        
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_records = [[current_time, s[0], (s[1].strip() if s[1] else "UNKNOWN"), s[2], s[5], s[6], (s[7] if s[7] else 0), ((s[9] * 3.6) if s[9] else 0)] for s in states]
    
    df_combined = pd.concat([pd.read_csv(CSV_FILE), pd.DataFrame(new_records, columns=["Timestamp", "ICAO24", "Callsign", "Origin_Country", "Longitude", "Latitude", "Altitude_m", "Velocity_kmh"])], ignore_index=True)
    df_combined.to_csv(CSV_FILE, index=False)
    print(f"Added {len(new_records)} records.")

if __name__ == "__main__":
    main()
