import os
import requests

# Key high-risk monitoring stations/zones in Nepal (matching your hazard areas)
MONITORING_ZONES = [
    {"name": "Kathmandu Valley (Central)", "lat": 27.7172, "lon": 85.3240},
    {"name": "Pokhara / Kaski (High Risk)", "lat": 28.2096, "lon": 83.9856},
    {"name": "Chitwan / Narayani Basin", "lat": 27.5291, "lon": 84.3542},
]

RAINFALL_THRESHOLD_MM = 50.0
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def check_all_hazard_zones():
  print("Scanning live weather forecasts across Nepal hazard zones...")

  for zone in MONITORING_ZONES:
    url = f"https://api.open-meteo.com/v1/forecast?latitude={zone['lat']}&longitude={zone['lon']}&daily=precipitation_sum&timezone=auto"

    response = requests.get(url)
    if response.status_code != 200:
      print(f"Failed to fetch data for {zone['name']}")
      continue

    data = response.json()
    daily_precip = data["daily"]["precipitation_sum"][0]
    date = data["daily"]["time"][0]

    print(
        f"- {zone['name']}: Expected Rainfall = {daily_precip}mm on {date}"
    )

    if daily_precip >= RAINFALL_THRESHOLD_MM:
      alert_msg = (
          f"🚨 FLOOD HAZARD ALERT: {zone['name']}! 🚨\nForecasted rain:"
          f" {daily_precip}mm on {date}. Immediate review of GEE map required!"
      )
      send_telegram_alert(alert_msg)


def send_telegram_alert(message):
  if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print("Telegram credentials missing!")
    return
  url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
  payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
  requests.post(url, json=payload)


if __name__ == "__main__":
  check_all_hazard_zones()
