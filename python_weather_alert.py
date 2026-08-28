import os
import requests

MONITORING_ZONES = [
    {"name": "Kathmandu Valley (Central)", "lat": 27.7172, "lon": 85.3240},
    {"name": "Pokhara / Kaski (High Risk)", "lat": 28.2096, "lon": 83.9856},
    {"name": "Chitwan / Narayani Basin", "lat": 27.5291, "lon": 84.3542},
]

RAINFALL_THRESHOLD_MM = 30.0
EARTHQUAKE_MAGNITUDE_THRESHOLD = 4.5  # Alert if magnitude is >= 4.5
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def send_telegram_alert(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials missing!")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID, 
        "text": message, 
        "parse_mode": "Markdown"
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("Telegram alert sent successfully!")
    else:
        print(f"Failed to send alert: {response.text}")


def check_all_hazard_zones():
    print("Scanning live weather forecasts across Nepal hazard zones...")
    gee_app_url = "https://yadavkeerti1199.users.earthengine.app/view/hazardalertinhimalayas"
    
    for zone in MONITORING_ZONES:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={zone['lat']}&longitude={zone['lon']}&daily=precipitation_sum&timezone=auto"
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Failed to fetch data for {zone['name']}")
            continue

        data = response.json()
        daily_precip = data["daily"]["precipitation_sum"][0]
        date = data["daily"]["time"][0]

        print(f"- {zone['name']}: Expected Rainfall = {daily_precip}mm on {date}")

        if daily_precip >= RAINFALL_THRESHOLD_MM:
            alert_msg = (
                f"🚨 *FLOOD HAZARD ALERT: {zone['name']}!* 🚨\n"
                f"Forecasted rain: *{daily_precip}mm* on {date}.\n\n"
                f"🔍 [Click here to open live GEE Risk Platform]({gee_app_url})"
            )
            send_telegram_alert(alert_msg)


def check_earthquakes():
    print("Scanning live seismic activity around Nepal...")
    gee_app_url = "https://yadavkeerti1199.users.earthengine.app/view/hazardalertinhimalayas"
    url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
    
    response = requests.get(url)
    if response.status_code != 200:
        print("Failed to fetch earthquake data")
        return

    quakes = response.json().get("features", [])
    for quake in quakes:
        props = quake["properties"]
        geom = quake["geometry"]
        mag = props.get("mag", 0)
        place = props.get("place", "Unknown location")
        
        # Bounding box roughly covering Nepal region
        lon, lat = geom["coordinates"][0], geom["coordinates"][1]
        if (26.0 <= lat <= 30.4) and (80.0 <= lon <= 88.2):
            if mag >= EARTHQUAKE_MAGNITUDE_THRESHOLD:
                alert_msg = (
                    f"⚠️ *SEISMIC / EARTHQUAKE ALERT* ⚠️\n"
                    f"Magnitude: *{mag}* near {place}\n"
                    f"Check regional stability immediately!\n\n"
                    f"🔍 [Open Live GEE Platform]({gee_app_url})"
                )
                send_telegram_alert(alert_msg)


if __name__ == "__main__":
    check_all_hazard_zones()
    check_earthquakes()
