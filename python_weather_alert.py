import os
import time
import requests

# -------------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GEE_APP_URL = "https://yadavkeerti1199.users.earthengine.app/view/hazardalertinhimalayas"

# 12 Hydrological River Basins & Flash-Flood Corridors
MONITORING_BASINS = [
    {"name": "Pokhara / Seti River Basin", "lat": 28.20, "lon": 83.98, "driver": "Upstream Catchment Surge"},
    {"name": "Chitwan / Narayani River Basin", "lat": 27.52, "lon": 84.43, "driver": "Direct Local Impact"},
    {"name": "Saptakoshi / Eastern Koshi Basin", "lat": 26.90, "lon": 87.15, "driver": "Basin Saturation"},
    {"name": "Rasuwa / Bhotekoshi Gorge", "lat": 28.15, "lon": 85.35, "driver": "Himalayan Flash Flood / GLOF Risk"},
    {"name": "Karnali Basin / Chisapani", "lat": 28.64, "lon": 81.28, "driver": "Massive Downstream Inundation"},
    {"name": "Mahakali River Basin", "lat": 28.97, "lon": 80.18, "driver": "Transboundary River Surge"},
    {"name": "West Rapti / Banke Plains", "lat": 28.05, "lon": 81.60, "driver": "Churia Hill Runoff Overflow"},
    {"name": "Babai River Basin", "lat": 28.18, "lon": 81.70, "driver": "Flash Flood / Inundation Risk"},
    {"name": "Kankai / Kamala Basin", "lat": 26.65, "lon": 87.88, "driver": "Churia Cloudburst Runoff"},
    {"name": "Kathmandu Valley Basin", "lat": 27.71, "lon": 85.32, "driver": "Urban Hydrological Runoff"},
    {"name": "Jajarkot & Bheri River Corridor", "lat": 28.70, "lon": 82.20, "driver": "Landslide Risk / Slope Saturation"},
    {"name": "Kavrepalanchok & Roshi Khola Zone", "lat": 27.58, "lon": 85.55, "driver": "Debris Flow Hazard"}
]

# High-Altitude Glacial Lakes for GLOF Tracking
GLACIAL_LAKES = [
    {"name": "Imja Tsho (Everest Region)", "lat": 27.90, "lon": 86.92, "alt": "5010m"},
    {"name": "Tsho Rolpa (Rolwaling Valley)", "lat": 27.85, "lon": 86.47, "alt": "4580m"},
    {"name": "Thulagi Glacier Lake (Manaslu)", "lat": 28.50, "lon": 84.48, "alt": "4050m"}
]

# In-memory deduplication set
processed_event_ids = set()

# -------------------------------------------------------------------
# HELPER FUNCTIONS
# -------------------------------------------------------------------
def get_free_static_map_url(lat, lon, zoom=11):
    """Generates a free satellite map snapshot snippet."""
    return f"https://static-maps.yandex.ru/1.x/?l=sat&ll={lon},{lat}&z={zoom}&pt={lon},{lat},pm2rdm"

def fetch_with_retry(url):
    """Retries API requests upon connection glitches."""
    for attempt in range(3):
        try:
            response = requests.get(url, timeout=12)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Fetch error ({url}): {e} (Attempt {attempt+1}/3)")
        time.sleep(2)
    return None

def send_telegram_photo(photo_url, caption, reply_markup=None):
    """Sends a photo card with inline markup buttons to Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram tokens not set!")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "Markdown"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            print("Telegram alert sent successfully!")
        else:
            print(f"Failed to send photo alert: {res.text}")
    except Exception as e:
        print(f"Error sending photo alert: {e}")

# -------------------------------------------------------------------
# 1. SEISMIC MONITOR (USGS) - Threshold >= 4.0 Mw
# -------------------------------------------------------------------
def check_earthquakes():
    print("🔎 Checking USGS Earthquakes...")
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&minlatitude=26&maxlatitude=31&minlongitude=80&maxlongitude=89&minmagnitude=3.5"
    data = fetch_with_retry(url)
    
    if not data or "features" not in data:
        return

    for feature in data["features"]:
        eq_id = f"EQ_{feature['id']}"
        if eq_id in processed_event_ids:
            continue

        props = feature["properties"]
        coords = feature["geometry"]["coordinates"]
        lon, lat, depth = coords[0], coords[1], coords[2]
        mag = props.get("mag", 0)

        if mag >= 4.0:
            severity = "🚨 *CRITICAL EARTHQUAKE ALERT*" if mag >= 5.0 else "⚠️ *MODERATE SEISMIC ACTIVITY*"
            caption = (
                f"{severity}\n\n"
                f"• *Magnitude:* `{mag} Mw`\n"
                f"• *Location:* {props['place']}\n"
                f"• *Depth:* `{depth} km`\n"
                f"• *Coordinates:* `{lat:.4f}, {lon:.4f}`\n\n"
                f"🔍 *Impact Check:* Satellite highlight generated for a 10km epicenter radius with downstream flow tracing."
            )

            gee_link = f"{GEE_APP_URL}?lat={lat}&lon={lon}&zoom=12&radius=10000"
            gmaps_link = f"https://www.google.com/maps?q={lat},{lon}"
            photo_url = get_free_static_map_url(lat, lon, zoom=11)

            reply_markup = {
                "inline_keyboard": [
                    [{"text": "🛰️ Open GEE Platform", "url": gee_link}, {"text": "📍 Google Maps", "url": gmaps_link}],
                    [{"text": "📊 USGS Event Report", "url": props["url"]}]
                ]
            }

            send_telegram_photo(photo_url, caption, reply_markup)
            processed_event_ids.add(eq_id)

# -------------------------------------------------------------------
# 2. WILDFIRE MONITOR (NASA FIRMS)
# -------------------------------------------------------------------
def check_nasafirms_wildfires():
    print("🔎 Checking NASA FIRMS Thermal Anomalies...")
    url = "https://firms.modaps.eosdis.nasa.gov/api/country/csv/free/VIIRS_SNPP_NRT/NPL/1"
    
    try:
        res = requests.get(url, timeout=12)
        if res.status_code != 200:
            return

        lines = res.text.split("\n")
        if len(lines) <= 1:
            return

        for line in lines[1:]:
            row = line.split(",")
            if len(row) < 11:
                continue

            try:
                lat = float(row[1])
                lon = float(row[2])
                acq_date = row[6]
                acq_time = row[7]
                confidence = row[10]
                frp = float(row[13]) if len(row) > 13 and row[13] else 0.0
            except ValueError:
                continue

            fire_id = f"FIRMS_{lat:.3f}_{lon:.3f}_{acq_date}_{acq_time}"
            if fire_id in processed_event_ids:
                continue

            if 26.0 <= lat <= 31.0 and 80.0 <= lon <= 89.0 and confidence in ["h", "n"]:
                confidence_label = "🔥 *HIGH CONFIDENCE THERMAL ANOMALY*" if confidence == "h" else "⚠️ *MODERATE THERMAL ANOMALY*"
                caption = (
                    f"{confidence_label}\n\n"
                    f"• *Source:* NASA VIIRS Satellite (375m)\n"
                    f"• *Acquisition Time:* {acq_date} {acq_time} UTC\n"
                    f"• *Fire Radiative Power (FRP):* `{frp:.1f} MW`\n"
                    f"• *Coordinates:* `{lat:.4f}, {lon:.4f}`\n\n"
                    f"🌲 *Action Required:* Inspect SWIR burn-scar indices in Earth Engine."
                )

                gee_link = f"{GEE_APP_URL}?lat={lat}&lon={lon}&zoom=13&radius=3000"
                gmaps_link = f"https://www.google.com/maps?q={lat},{lon}"
                photo_url = get_free_static_map_url(lat, lon, zoom=12)

                reply_markup = {
                    "inline_keyboard": [
                        [{"text": "🛰️ View Burn Scar Zone in GEE", "url": gee_link}, {"text": "📍 View on Google Maps", "url": gmaps_link}]
                    ]
                }

                send_telegram_photo(photo_url, caption, reply_markup)
                processed_event_ids.add(fire_id)

    except Exception as e:
        print(f"NASA FIRMS Error: {e}")

# -------------------------------------------------------------------
# 3. HYDROLOGICAL MONITOR (Rainfall >= 50mm Threshold)
# -------------------------------------------------------------------
def check_live_rainfall():
    print("🔎 Checking 12 River Basins for Flash Flood Risks...")
    today_str = time.strftime("%Y-%m-%d")

    for basin in MONITORING_BASINS:
        basin_key = f"RAIN_V2_{basin['name'].replace(' ', '')}_{today_str}"
        if basin_key in processed_event_ids:
            continue

        url = f"https://api.open-meteo.com/v1/forecast?latitude={basin['lat']}&longitude={basin['lon']}&daily=rain_sum&past_days=3&timezone=auto"
        data = fetch_with_retry(url)

        if data and "daily" in data and "rain_sum" in data["daily"]:
            rain_sums = data["daily"]["rain_sum"]
            past_3days_rain = sum(rain_sums[:3]) if len(rain_sums) >= 3 else 0.0
            today_rain = rain_sums[3] if len(rain_sums) >= 4 else 0.0

            is_high_risk = (today_rain >= 50.0) or (today_rain >= 25.0 and past_3days_rain >= 60.0)
            is_moderate_risk = (today_rain >= 20.0 and not is_high_risk)

            if is_high_risk or is_moderate_risk:
                header = "🌧️ *CRITICAL FLOOD & LANDSLIDE RISK*" if is_high_risk else "🟡 *MODERATE RAINFALL ADVISORY*"
                saturation_status = "🔴 HIGH (Saturated Soil)" if past_3days_rain >= 60 else "🟢 MODERATE / LOW"

                caption = (
                    f"{header}\n\n"
                    f"📍 *Zone:* {basin['name']}\n"
                    f"🌊 *Driver:* {basin['driver']}\n"
                    f"🌧️ *Today's Rainfall:* `{today_rain:.1f} mm`\n"
                    f"📊 *3-Day Accumulated Rain:* `{past_3days_rain:.1f} mm`\n"
                    f"💧 *Ground Saturation Level:* {saturation_status}\n\n"
                    f"⚠️ *Risk Assessment:* " + ("Heavy precipitation threshold exceeded! High risk of flash flooding and slope failure." if is_high_risk else "Elevated river discharge expected.")
                )

                gee_link = f"{GEE_APP_URL}?lat={basin['lat']}&lon={basin['lon']}&zoom=11&radius=8000"
                gmaps_link = f"https://www.google.com/maps?q={basin['lat']},{basin['lon']}"
                photo_url = get_free_static_map_url(basin['lat'], basin['lon'], zoom=11)

                reply_markup = {
                    "inline_keyboard": [
                        [{"text": "🌊 Open Live GEE Platform", "url": gee_link}, {"text": "📍 View Google Maps", "url": gmaps_link}]
                    ]
                }

                send_telegram_photo(photo_url, caption, reply_markup)
                processed_event_ids.add(basin_key)

# -------------------------------------------------------------------
# 4. GLOF FREEZE-THAW MONITOR (High Altitude Lakes > 2.0°C)
# -------------------------------------------------------------------
def check_glof_hazards():
    print("🔎 Checking High-Altitude Glacial Lakes...")
    today_str = time.strftime("%Y-%m-%d")

    for lake in GLACIAL_LAKES:
        glof_key = f"GLOF_{lake['name'].replace(' ', '')}_{today_str}"
        if glof_key in processed_event_ids:
            continue

        url = f"https://api.open-meteo.com/v1/forecast?latitude={lake['lat']}&longitude={lake['lon']}&daily=temperature_2m_max&timezone=auto"
        data = fetch_with_retry(url)

        if data and "daily" in data and "temperature_2m_max" in data["daily"]:
            max_temp = data["daily"]["temperature_2m_max"][0]

            if max_temp > 2.0:
                caption = (
                    f"🧊 *GLACIAL LAKE MELT / THERMAL SURGE WARNING*\n\n"
                    f"📍 *Target Lake:* {lake['name']} ({lake['alt']})\n"
                    f"🌡️ *Peak Temp Today:* `{max_temp:.1f}°C` (Thermal Thaw Condition Active)\n"
                    f"⚠️ *Risk Assessment:* Accelerated glacial melt rate & structural moraine dam pressure."
                )

                gee_link = f"{GEE_APP_URL}?lat={lake['lat']}&lon={lake['lon']}&zoom=13&radius=5000"
                photo_url = get_free_static_map_url(lake['lat'], lake['lon'], zoom=12)

                reply_markup = {
                    "inline_keyboard": [
                        [{"text": "🛰️ Inspect Glacier Lake in GEE", "url": gee_link}]
                    ]
                }

                send_telegram_photo(photo_url, caption, reply_markup)
                processed_event_ids.add(glof_key)

# -------------------------------------------------------------------
# MAIN EXECUTION LOOP
# -------------------------------------------------------------------
if __name__ == "__main__":
    print("🚀 Starting Himalayan Hazard Decision Support System...")
    check_earthquakes()
    check_nasafirms_wildfires()
    check_live_rainfall()
    check_glof_hazards()
    print("✅ Diagnostic scan completed across all 4 feeds!")
