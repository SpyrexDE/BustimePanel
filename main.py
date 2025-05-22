from fastapi import FastAPI
from datetime import datetime
from typing import Dict, List
import requests
from zoneinfo import ZoneInfo

app = FastAPI()


BUS_STOPS = {
    "29": ["de:09663:358"],
    "10": ["de:09663:229"]
}

def fetch_bus_arrivals(stop_id: str) -> List[Dict]:
    url = "https://bahnland-bayern.de/efa/XML_DM_REQUEST"
    params = {
        "outputFormat": "rapidJSON",
        "coordOutputFormat": "WGS84[dd.ddddd]",
        "locationServerActive": "1",
        "mode": "direct",
        "useAllStops": "1",
        "useProxFootSearch": "0",
        "name_dm": stop_id,
        "timeOffset": "-30",
        "type_dm": "any",
        "limit": "10"
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    return data.get("stopEvents", [])

@app.get("/bustime")
def get_next_bus_arrivals() -> Dict:
    try:
        now = datetime.now(ZoneInfo("Europe/Berlin"))
        timestamps = {
            "TIMESTAMP": int(now.timestamp()),
            "29": None,
            "10": None
        }

        def get_departure_time(event):
            return event.get("departureTimeEstimated") or event.get("departureTimePlanned")

        for line, stop_ids in BUS_STOPS.items():
            if timestamps[line] is not None:
                continue

            all_events = []
            for stop_id in stop_ids:
                events = fetch_bus_arrivals(stop_id)
                all_events.extend(events)

            all_events.sort(key=lambda e: get_departure_time(e))

            for event in all_events:
                if "transportation" not in event:
                    continue

                number = event["transportation"].get("number")
                if number == line:
                    departure_str = get_departure_time(event)
                    if departure_str:
                        # Parse UTC time and convert to local time
                        departure_time = datetime.strptime(departure_str, "%Y-%m-%dT%H:%M:%SZ")
                        departure_time = departure_time.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Europe/Berlin"))
                        
                        if departure_time > now:
                            timestamps[line] = int(departure_time.timestamp())
                            break

        return timestamps
    except Exception as e:
        return {"error": str(e)}
