import time
import os
import requests
import pandas as pd
from datetime import datetime

LAT_MIN, LAT_MAX = 32.00, 32.04
LON_MIN, LON_MAX = 34.75, 34.81
CSV_FILE = "flights_holon.csv"

# השרת יישאר ער לדקה אחת (60 שניות) בכל הפעלה, וידגום כל 5 שניות
RUN_DURATION = 60 
INTERVAL = 5 

processed_flights = {}

def get_full_track(icao24):
    try:
        response = requests.get(f"https://opensky-network.org/api/tracks/all", params={"icao24": icao24, "time": 0}, timeout=10)
        return response.json().get("path", []) if response.status_code == 200 else []
    except Exception:
        return []

def main():
    if not os.path.exists(CSV_FILE) or os.stat(CSV_FILE).st_size == 0:
        columns = ["Detection_Time", "ICAO24", "Callsign", "Track_Point_Time", "Latitude", "Longitude", "Altitude_m"]
        pd.DataFrame(columns=columns).to_csv(CSV_FILE, index=False)

    start_time = time.time()
    print("Starting precision tracking session (60 seconds)...")

    while (time.time() - start_time) < RUN_DURATION:
        current_time_epoch = int(time.time())
        states = []
        
        try:
            response = requests.get("https://opensky-network.org/api/states/all", params={"lamin": LAT_MIN, "lamax": LAT_MAX, "lomin": LON_MIN, "lomax": LON_MAX}, timeout=8)
            if response.status_code == 200:
                states = response.json().get("states", [])
        except Exception:
            pass

        new_rows = []
        if states:
            for s in states:
                icao24 = s[0]
                callsign = s[1].strip() if s[1] else "UNKNOWN"

                # מניעת כפילויות: אם כבר שמרנו את המטוס הזה בדקה האחרונה, נדלג
                if icao24 in processed_flights and (current_time_epoch - processed_flights[icao24]) < 60:
                    continue

                print(f"🎯 Target spotted: {callsign}. Extracting 20-second window path...")
                full_path = get_full_track(icao24)
                
                detection_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if full_path:
                    for point in full_path:
                        p_time, p_lat, p_lon, p_alt = point[0], point[1], point[2], point[3]
                        
                        # ה-מלכוד המדויק: שומר רק נקודות שבין 20 שניות לפני ל-20 שניות אחרי המעבר
                        if abs(current_time_epoch - p_time) <= 20:
                            p_time_str = datetime.fromtimestamp(p_time).strftime("%Y-%m-%d %H:%M:%S")
                            new_rows.append([detection_time, icao24, callsign, p_time_str, p_lat, p_lon, (p_alt if p_alt else 0)])

                processed_flights[icao24] = current_time_epoch

        if new_rows:
            df_combined = pd.concat([pd.read_csv(CSV_FILE), pd.DataFrame(new_rows, columns=["Detection_Time", "ICAO24", "Callsign", "Track_Point_Time", "Latitude", "Longitude", "Altitude_m"])], ignore_index=True)
            df_combined.to_csv(CSV_FILE, index=False)
            print(f"Added {len(new_rows)} precision points to CSV.")

        time.sleep(INTERVAL)

    print("Session finished safely.")

if __name__ == "__main__":
    main()
