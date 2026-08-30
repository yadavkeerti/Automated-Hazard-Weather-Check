# 🛰️ Himalayan Hazard Decision Support System (HHDSS)

An automated, serverless 24/7 multi-hazard listener and decision-support pipeline tailored for Nepal and the broader Himalayan region. The system continuously monitors seismic activity, forest fires, extreme hydrological precipitation, and high-altitude glacial thaw, sending real-time alert cards with satellite previews directly to a Telegram interface.

---

## 📌 Architecture & Data Feeds

The system runs on Google Apps Script using time-driven trigger architecture and webhooks:

1. USGS Earthquake API:
   - Bounding Box: Lat 26.0°N to 31.0°N, Lon 80.0°E to 89.0°E
   - Threshold: ≥ 4.0 Mw
2. NASA FIRMS (VIIRS SNPP 375m):
   - Threshold: Moderate to High confidence thermal anomalies
3. Open-Meteo Hydrological Pipeline:
   - Coverage: 12 primary Himalayan river basins & landslide corridors (Seti, Narayani, Saptakoshi, Rasuwa, Karnali, Kavre/Roshi Khola, etc.)
   - Threshold: ≥ 50 mm/day or ≥ 25 mm with cumulative 3-day ground saturation (≥ 60 mm)
4. GLOF Freeze-Thaw Thermal Monitor:
   - Target Glacial Lakes: Imja Tsho (5010m), Tsho Rolpa (4580m), Thulagi (4050m)
   - Threshold: Peak daily air temp > 2.0°C

---

## 🚀 Key Features

- Static Satellite Cards: Dynamically generates satellite imagery overlays centered on hazard locations.
- Interactive Deep Links: Every alert features inline buttons directing users to a custom Google Earth Engine (GEE) app and Google Maps.
- Stateful Memory Management: Uses Apps Script `PropertiesService` to log event IDs and prevent duplicate notification spamming.
- Bi-directional Bot Webhook: Responds instantly to Telegram commands (`/status`, `/check`, `/basins`).

---

## 🛠️ Tech Stack

- Language: JavaScript (Google Apps Script)
- Platforms: Google Earth Engine, Telegram Bot API, Yandex Static Maps API
- Data Protocols: GeoJSON, REST APIs, CSV Streaming
