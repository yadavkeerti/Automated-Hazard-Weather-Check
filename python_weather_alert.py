import os
import requests

MONITORING_ZONES = [
    {"name": "Kathmandu Valley (Central)", "lat": 27.7172, "lon": 85.3240},
    {"name": "Pokhara / Kaski (High Risk)", "lat": 28.2096, "lon": 83.9856},
    {"name": "Chitwan / Narayani Basin", "lat": 27.5291, "lon": 84.3542},
]

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

def evaluate_weather_severity(precip):
    """Determines hazard tier based on rainfall mm"""
    if precip >= 75.0:
        return "🔴 [CRITICAL WARNING] Extreme Heavy Rainfall"
    elif precip >= 45.0:
        return "🟠 [HIGH WATCH] Heavy Monsoon Rains"
    elif precip >= 25.0:
        return "🟡 [ADVISORY] Moderate Rainfall"
    return None

def check_all_hazard_zones():
    print("Scanning multi-tier weather forecasts across Nepal...")
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

        severity_tier = evaluate_weather_severity(daily_precip)
        if severity_tier:
            alert_msg = (
                f"{severity_tier}\n"
                f"📍 *Zone:* {zone['name']}\n"
                f"📊 *Forecasted Rain:* {daily_precip}mm on {date}\n\n"
                f"⚠️ *Risk:* High potential for localized flooding or debris flow.\n"
                f"🔍 [Open Live GEE Platform]({gee_app_url})"
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
        
        lon, lat = geom["coordinates"][0], geom["coordinates"][1]
        if (26.0 <= lat <= 30.4) and (80.0 <= lon <= 88.2):
            if mag >= 5.0:
                tier_label = "🔴 [CRITICAL SEISMIC EMERGENCY]" if mag >= 6.0 else "🟠 [SEISMIC WARNING]"
                alert_msg = (
                    f"{tier_label}\n"
                    f"🌍 *Magnitude:* {mag}\n"
                    f"📍 *Location:* {place}\n"
                    f"⚠️ *Risk:* Potential for secondary landslides in steep terrain.\n\n"
                    f"🔍 [Open Live GEE Platform]({gee_app_url})"
                )
                send_telegram_alert(alert_msg)

if __name__ == "__main__":
    check_all_hazard_zones()
    check_earthquakes()
