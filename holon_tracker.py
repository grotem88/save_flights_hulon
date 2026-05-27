import time
import os
import requests
import pandas as pd
from datetime import datetime

LAT_MIN, LAT_MAX = 32.00, 32.04
LON_MIN, LON_MAX = 34.75, 34.81
CSV_FILE = "flights_holon.csv"

# משך זמן הריצה בכל הפעלה (600 שניות = 10 דקות של מעקב רציף)
RUN_DURATION_SECONDS = 600 
INTERVAL_SECONDS = 30

processed_flights = {}

def get_full_track(icao24):
    try:
        response = requests.get(f"https://opensky-network.org/api/tracks/all", params={"icao24": icao24, "time": 0}, timeout=10)
        if response.status_code == 200:
            return response.json().get("path", [])
        return []
    except Exception:
        return []

def main():
    if not os.path.exists(CSV_FILE) or os.stat(CSV_FILE).st_size == 0:
        columns = ["Detection_Time", "ICAO24", "Callsign", "Track_Point_Time", "Latitude", "Longitude", "Altitude_m"]
        pd.DataFrame(columns=columns).to_csv(CSV_FILE, index=False)

    start_time = time.time()
    print(f"Starting robust continuous tracking for {RUN_DURATION_SECONDS/60} minutes...")

    while (time.time() - start_time) < RUN_DURATION_SECONDS:
        current_time_epoch = int(time.time())
        states = []
        
        try:
            response = requests.get("https://opensky-network.org/api/states/all", params={"lamin": LAT_MIN, "lamax": LAT_MAX, "lomin": LON_MIN, "lomax": LON_MAX}, timeout=10)
            if response.status_code == 200:
                states = response.json().get("states", [])
            elif response.status_code == 429:
                print("OpenSky API Rate limit hit (429). Waiting for next cycle...")
            else:
                print(f"API returned status code: {response.status_code}. Retrying later...")
        except Exception as e:
            print(f"Connection error: {e}. Retrying later...")

        new_rows = []
        if states:
            for s in states:
                icao24 = s[0]
                callsign = s[1].strip() if s[1] else "UNKNOWN"

                if icao24 in processed_flights and (current_time_epoch - processed_flights[icao24]) < 300:
                    continue

                print(f"Detected flight: {callsign}. Fetching historical path...")
                full_path = get_full_track(icao24)
                
                detection_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if full_path:
                    for point in full_path:
                        p_time, p_lat, p_lon, p_alt = point[0], point[1], point[2], point[3]
                        
                        # סינון: שומר נקודות של דקה לפני ודקה אחרי המעבר בחולון
                        if abs(current_time_epoch - p_time) <= 60:
                            p_time_str = datetime.fromtimestamp(p_time).strftime("%Y-%m-%d %H:%M:%S")
                            new_rows.append([detection_time, icao24, callsign, p_time_str, p_lat, p_lon, (p_alt if p_alt else 0)])

                processed_flights[icao24] = current_time_epoch

        if new_rows:
            df_combined = pd.concat([pd.read_csv(CSV_FILE), pd.DataFrame(new_rows, columns=["Detection_Time", "ICAO24", "Callsign", "Track_Point_Time", "Latitude", "Longitude", "Altitude_m"])], ignore_index=True)
            df_combined.to_csv(CSV_FILE, index=False)
            print(f"Saved {len(new_rows)} path points to CSV.")

        # במקום לעצור בגלל שגיאה, מחכים תמיד את ה-30 שניות וממשיכים ללולאה הבאה
        time.sleep(INTERVAL_SECONDS)

    print("Finished 10 minutes session.")

if __name__ == "__main__":
    main()
