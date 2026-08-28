import os
import time
import requests

MONITORING_ZONES = [
    {
        "name": "Kathmandu Valley & Upstream Northern Basin", 
        "target_lat": 27.7172, "target_lon": 85.3240,
        "upstream_lat": 27.9172, "upstream_lon": 85.3240
    },
    {
        "name": "Pokhara / Kaski & Seti River Basin", 
        "target_lat": 28.2096, "target_lon": 83.9856,
        "upstream_lat": 28.4596, "upstream_lon": 83.9856
    },
    {
        "name": "Chitwan / Narayani Basin", 
        "target_lat": 27.5291, "target_lon": 84.3542,
        "upstream_lat": 27.8291, "upstream_lon": 84.3542
    },
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
    
    # Retry loop for sending telegram message
    for attempt in range(3):
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                print("Telegram alert sent successfully!")
                return
            else:
                print(f"Attempt {attempt+1} failed to send alert: {response.text}")
        except Exception as e:
            print(f"Attempt {attempt+1} connection error: {e}")
        time.sleep(2)

def fetch_with_retry(url):
    """Helper function to retry API requests if network glitches happen"""
    for attempt in range(3):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Network error fetching {url} (Attempt {attempt+1}/3): {e}")
        time.sleep(2)
    return None

def evaluate_weather_severity(precip):
    if precip >= 75.0:
        return "🔴 [CRITICAL WARNING] Extreme Heavy Rainfall"
    elif precip >= 45.0:
        return "🟠 [HIGH WATCH] Heavy Monsoon Rains"
    elif precip >= 25.0:
        return "🟡 [ADVISORY] Moderate Rainfall"
    return None

def check_all_hazard_zones():
    print("Scanning multi-tier weather forecasts & upstream basins safely...")
    gee_app_url = "https://yadavkeerti1199.users.earthengine.app/view/hazardalertinhimalayas"
    
    for zone in MONITORING_ZONES:
        target_url = f"https://api.open-meteo.com/v1/forecast?latitude={zone['target_lat']}&longitude={zone['target_lon']}&daily=precipitation_sum&timezone=auto"
        upstream_url = f"https://api.open-meteo.com/v1/forecast?latitude={zone['upstream_lat']}&longitude={zone['upstream_lon']}&daily=precipitation_sum&timezone=auto"
        
        t_data = fetch_with_retry(target_url)
        u_data = fetch_with_retry(upstream_url)
        
        if not t_data or not u_data:
            print(f"Skipping {zone['name']} due to persistent network connection issues.")
            continue

        target_precip = t_data["daily"]["precipitation_sum"][0]
        upstream_precip = u_data["daily"]["precipitation_sum"][0]
        date = t_data["daily"]["time"][0]

        print(f"- {zone['name']}: Local Rain = {target_precip}mm | Upstream Rain = {upstream_precip}mm on {date}")

        max_precip = max(target_precip, upstream_precip)
        severity_tier = evaluate_weather_severity(max_precip)
        
        if severity_tier:
            origin_note = "Upstream Catchment Surge" if upstream_precip > target_precip else "Direct Local Impact"
            alert_msg = (
                f"{severity_tier}\n"
                f"📍 *Zone:* {zone['name']}\n"
                f"🌊 *Driver:* {origin_note}\n"
                f"📊 *Local Rain:* {target_precip}mm | *Upstream Rain:* {upstream_precip}mm ({date})\n\n"
                f"⚠️ *Risk:* Elevated river discharge or mountain runoff expected.\n"
                f"🔍 [Open Live GEE Platform]({gee_app_url})"
            )
            send_telegram_alert(alert_msg)

def check_earthquakes():
    print("Scanning live seismic activity safely around Nepal...")
    gee_app_url = "https://yadavkeerti1199.users.earthengine.app/view/hazardalertinhimalayas"
    url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
    
    data = fetch_with_retry(url)
    if not data:
        print("Failed to fetch earthquake data from USGS.")
        return

    quakes = data.get("features", [])
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
