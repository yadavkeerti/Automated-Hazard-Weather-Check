/**
 * Interactive 24/7 Cloud Listener & Decision Support System for Nepal & Himalayas
 * Target: Keerti (ID: 6599577091)
 */

var TELEGRAM_TOKEN = "8833080160:AAGSNfJ7DTwd08rwM0LJn0tQGNsa_37gwPs";
var CHAT_ID = "6599577091";
var GEE_APP_URL = "https://yadavkeerti1199.users.earthengine.app/view/hazardalertinhimalayas";

/**
 * HELPER: Generate Free Satellite Map Snapshot
 */
function getFreeStaticMapUrl(lat, lon, zoom) {
  return "https://static-maps.yandex.ru/1.x/?l=sat&ll=" + lon + "," + lat + "&z=" + (zoom || 11) + "&pt=" + lon + "," + lat + ",pm2rdm";
}

/**
 * HELPER: Send Direct Text Reply
 */
function sendTelegramReply(chatId, msgText) {
  if (!msgText || msgText.trim() === "") return;
  
  var telegramUrl = "https://api.telegram.org/bot" + TELEGRAM_TOKEN + "/sendMessage";
  var payload = {
    "chat_id": chatId,
    "text": msgText,
    "parse_mode": "Markdown"
  };

  try {
    UrlFetchApp.fetch(telegramUrl, {
      "method": "post",
      "contentType": "application/json",
      "payload": JSON.stringify(payload),
      "muteHttpExceptions": true
    });
  } catch (e) {
    Logger.log("Error in sendTelegramReply: " + e.toString());
  }
}

/**
 * HELPER: Send Interactive Text Message
 */
function sendTelegramInteractive(msgText, replyMarkupObj) {
  var telegramUrl = "https://api.telegram.org/bot" + TELEGRAM_TOKEN + "/sendMessage";
  var payload = {
    "chat_id": CHAT_ID,
    "text": msgText,
    "parse_mode": "Markdown",
    "reply_markup": replyMarkupObj ? JSON.stringify(replyMarkupObj) : null
  };

  try {
    UrlFetchApp.fetch(telegramUrl, {
      "method": "post",
      "contentType": "application/json",
      "payload": JSON.stringify(payload)
    });
  } catch (e) {
    Logger.log("Error sending text message: " + e.toString());
  }
}

/**
 * HELPER: Send Photo Message
 */
function sendTelegramWithPhoto(photoUrl, msgText, replyMarkupObj) {
  var telegramUrl = "https://api.telegram.org/bot" + TELEGRAM_TOKEN + "/sendPhoto";
  var payload = {
    "chat_id": CHAT_ID,
    "photo": photoUrl,
    "caption": msgText,
    "parse_mode": "Markdown",
    "reply_markup": JSON.stringify(replyMarkupObj)
  };

  try {
    var response = UrlFetchApp.fetch(telegramUrl, {
      "method": "post",
      "contentType": "application/json",
      "payload": JSON.stringify(payload),
      "muteHttpExceptions": true
    });
    
    if (response.getResponseCode() !== 200) {
      sendTelegramInteractive(msgText, replyMarkupObj);
    }
  } catch (e) {
    sendTelegramInteractive(msgText, replyMarkupObj);
  }
}

/**
 * 1️⃣ EARTHQUAKE LISTENER (USGS) - Threshold: Mag >= 4.0
 */
function checkUSGSAndSendAlerts() {
  var url = "https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&minlatitude=26&maxlatitude=31&minlongitude=80&maxlongitude=89&minmagnitude=3.5";
  
  try {
    var response = UrlFetchApp.fetch(url);
    var data = JSON.parse(response.getContentText());
    var features = data.features;
    var scriptProperties = PropertiesService.getScriptProperties();
    
    features.forEach(function(feature) {
      var id = "EQ_" + feature.id;
      var alreadyProcessed = scriptProperties.getProperty(id);
      
      if (!alreadyProcessed) {
        var props = feature.properties;
        var coords = feature.geometry.coordinates;
        var lat = coords[1];
        var lon = coords[0];
        var mag = props.mag;

        // THRESHOLD FILTER: Only send alert if magnitude is >= 4.0
        if (mag >= 4.0) {
          var severityHeader = mag >= 5.0 ? "🚨 *CRITICAL EARTHQUAKE ALERT*" : "⚠️ *MODERATE SEISMIC ACTIVITY*";
          
          var msg = severityHeader + "\n\n" +
                    "• *Magnitude:* `" + mag + " Mw`\n" +
                    "• *Location:* " + props.place + "\n" +
                    "• *Depth:* `" + coords[2] + " km`\n" +
                    "• *Coordinates:* `" + lat.toFixed(4) + ", " + lon.toFixed(4) + "`\n\n" +
                    "🔍 *Impact Check:* Satellite highlight generated for a 10km epicenter radius with downstream flow tracing.";

          var geeLink = GEE_APP_URL + "?lat=" + lat + "&lon=" + lon + "&zoom=12&radius=10000";
          var gmapsLink = "https://www.google.com/maps?q=" + lat + "," + lon;
          var photoUrl = getFreeStaticMapUrl(lat, lon, 11);

          var inlineKeyboard = {
            "inline_keyboard": [
              [
                { "text": "🛰️ Open GEE Platform", "url": geeLink },
                { "text": "📍 Google Maps", "url": gmapsLink }
              ],
              [
                { "text": "📊 USGS Event Report", "url": props.url }
              ]
            ]
          };
          
          sendTelegramWithPhoto(photoUrl, msg, inlineKeyboard);
          scriptProperties.setProperty(id, "true");
        }
      }
    });
  } catch (error) {
    Logger.log("USGS Error: " + error.toString());
  }
}

/**
 * 2️⃣ WILDFIRE LISTENER (NASA FIRMS)
 */
function checkNASAFirmsWildfiresAndSendAlerts() {
  var minLat = 26.0, maxLat = 31.0, minLon = 80.0, maxLon = 89.0;
  var url = "https://firms.modaps.eosdis.nasa.gov/api/country/csv/free/VIIRS_SNPP_NRT/NPL/1"; 

  var options = {
    "muteHttpExceptions": true,
    "validateHttpsCertificates": true
  };

  try {
    var response = UrlFetchApp.fetch(url, options);
    if (response.getResponseCode() !== 200) return;

    var csvData = response.getContentText();
    var lines = csvData.split("\n");
    if (lines.length <= 1) return;

    var scriptProperties = PropertiesService.getScriptProperties();

    for (var i = 1; i < lines.length; i++) {
      var row = lines[i].split(",");
      if (row.length < 10) continue;

      var lat = parseFloat(row[1]);
      var lon = parseFloat(row[2]);
      var acqDate = row[6];
      var acqTime = row[7];
      var confidence = row[10];
      var frp = parseFloat(row[13]) || 0;

      var fireId = "FIRMS_" + lat.toFixed(3) + "_" + lon.toFixed(3) + "_" + acqDate + "_" + acqTime;
      var alreadyProcessed = scriptProperties.getProperty(fireId);

      if (!alreadyProcessed && lat >= minLat && lat <= maxLat && lon >= minLon && lon <= maxLon && (confidence === "h" || confidence === "n")) {
        var confidenceLabel = confidence === "h" ? "🔥 *HIGH CONFIDENCE THERMAL ANOMALY*" : "⚠️ *MODERATE THERMAL ANOMALY*";
        
        var msg = confidenceLabel + "\n\n" +
                  "• *Source:* NASA VIIRS Satellite (375m)\n" +
                  "• *Acquisition Time:* " + acqDate + " " + acqTime + " UTC\n" +
                  "• *Fire Radiative Power (FRP):* `" + frp.toFixed(1) + " MW`\n" +
                  "• *Coordinates:* `" + lat.toFixed(4) + ", " + lon.toFixed(4) + "`\n\n" +
                  "🌲 *Action Required:* Inspect SWIR burn-scar indices in Earth Engine.";

        var geeLink = GEE_APP_URL + "?lat=" + lat + "&lon=" + lon + "&zoom=13&radius=3000";
        var gmapsLink = "https://www.google.com/maps?q=" + lat + "," + lon;
        var photoUrl = getFreeStaticMapUrl(lat, lon, 12);

        var inlineKeyboard = {
          "inline_keyboard": [
            [
              { "text": "🛰️ View Burn Scar Zone in GEE", "url": geeLink },
              { "text": "📍 View on Google Maps", "url": gmapsLink }
            ]
          ]
        };

        sendTelegramWithPhoto(photoUrl, msg, inlineKeyboard);
        scriptProperties.setProperty(fireId, "true");
      }
    }
  } catch (error) {
    Logger.log("NASA FIRMS Error: " + error.toString());
  }
}

/**
 * 3️⃣ DYNAMIC HYDROLOGICAL LISTENER (Rainfall > 50mm Threshold)
 */
function checkLiveRainfallAndSendAlerts() {
  var basins = [
    { name: "Pokhara / Seti River Basin", lat: 28.20, lon: 83.98, driver: "Upstream Catchment Surge" },
    { name: "Chitwan / Narayani River Basin", lat: 27.52, lon: 84.43, driver: "Direct Local Impact" },
    { name: "Saptakoshi / Eastern Koshi Basin", lat: 26.90, lon: 87.15, driver: "Basin Saturation" },
    { name: "Rasuwa / Bhotekoshi Gorge", lat: 28.15, lon: 85.35, driver: "Himalayan Flash Flood / GLOF Risk" },
    { name: "Karnali Basin / Chisapani", lat: 28.64, lon: 81.28, driver: "Massive Downstream Inundation" },
    { name: "Mahakali River Basin", lat: 28.97, lon: 80.18, driver: "Transboundary River Surge" },
    { name: "West Rapti / Banke Plains", lat: 28.05, lon: 81.60, driver: "Churia Hill Runoff Overflow" },
    { name: "Babai River Basin", lat: 28.18, lon: 81.70, driver: "Flash Flood / Inundation Risk" },
    { name: "Kankai / Kamala Basin", lat: 26.65, lon: 87.88, driver: "Churia Cloudburst Runoff" },
    { name: "Kathmandu Valley Basin", lat: 27.71, lon: 85.32, driver: "Urban Hydrological Runoff" },
    { name: "Jajarkot & Bheri River Corridor", lat: 28.70, lon: 82.20, driver: "Landslide Risk / Slope Saturation" },
    { name: "Kavrepalanchok & Roshi Khola Zone", lat: 27.58, lon: 85.55, driver: "Debris Flow Hazard" }
  ];

  var scriptProperties = PropertiesService.getScriptProperties();
  var todayDateStr = new Date().toISOString().split('T')[0];

  basins.forEach(function(basin) {
    var alertKey = "RAIN_V2_" + basin.name.replace(/[^a-zA-Z0-9]/g, "") + "_" + todayDateStr;
    var alreadyProcessed = scriptProperties.getProperty(alertKey);

    if (!alreadyProcessed) {
      var url = "https://api.open-meteo.com/v1/forecast?latitude=" + basin.lat + "&longitude=" + basin.lon + 
                "&daily=rain_sum&past_days=3&timezone=auto";
      
      try {
        var response = UrlFetchApp.fetch(url);
        var json = JSON.parse(response.getContentText());
        
        if (json.daily && json.daily.rain_sum) {
          var rainData = json.daily.rain_sum;
          var past3DaysRain = (rainData[0] || 0) + (rainData[1] || 0) + (rainData[2] || 0);
          var todayRain = rainData[3] || 0;
          
          var isHighRisk = (todayRain >= 50.0) || (todayRain >= 25.0 && past3DaysRain >= 60.0);
          var isModerateRisk = (todayRain >= 20.0 && !isHighRisk);

          if (isHighRisk || isModerateRisk) {
            var header = isHighRisk ? "🌧️ *CRITICAL FLOOD & LANDSLIDE RISK*" : "🟡 *MODERATE RAINFALL ADVISORY*";
            var saturationStatus = past3DaysRain >= 60 ? "🔴 HIGH (Saturated Soil)" : "🟢 MODERATE / LOW";

            var msg = header + "\n\n" +
                      "📍 *Zone:* " + basin.name + "\n" +
                      "🌊 *Driver:* " + basin.driver + "\n" +
                      "🌧️ *Today's Rainfall:* `" + todayRain.toFixed(1) + " mm`\n" +
                      "📊 *3-Day Accumulated Rain:* `" + past3DaysRain.toFixed(1) + " mm`\n" +
                      "💧 *Ground Saturation Level:* " + saturationStatus + "\n\n" +
                      "⚠️ *Risk Assessment:* " + (isHighRisk ? "Heavy precipitation threshold exceeded! High risk of flash flooding and slope failure." : "Elevated river discharge expected.");

            var geeLink = GEE_APP_URL + "?lat=" + basin.lat + "&lon=" + basin.lon + "&zoom=11&radius=8000";
            var gmapsLink = "https://www.google.com/maps?q=" + basin.lat + "," + basin.lon;
            var photoUrl = getFreeStaticMapUrl(basin.lat, basin.lon, 11);

            var inlineKeyboard = {
              "inline_keyboard": [
                [
                  { "text": "🌊 Open Live GEE Platform", "url": geeLink },
                  { "text": "📍 View Google Maps", "url": gmapsLink }
                ]
              ]
            };

            sendTelegramWithPhoto(photoUrl, msg, inlineKeyboard);
            scriptProperties.setProperty(alertKey, "true");
          }
        }
      } catch (e) {
        Logger.log("Rainfall API error for " + basin.name + ": " + e.toString());
      }
    }
  });
}

/**
 * 4️⃣ HIGH-ALTITUDE GLOF & FREEZE-THAW MONITOR (Threshold: Temp > 2°C)
 */
function checkGLOFHighAltitudeHazards() {
  var glacialLakes = [
    { name: "Imja Tsho (Everest Region)", lat: 27.90, lon: 86.92, alt: "5010m" },
    { name: "Tsho Rolpa (Rolwaling Valley)", lat: 27.85, lon: 86.47, alt: "4580m" },
    { name: "Thulagi Glacier Lake (Manaslu)", lat: 28.50, lon: 84.48, alt: "4050m" }
  ];

  var scriptProperties = PropertiesService.getScriptProperties();
  var todayDateStr = new Date().toISOString().split('T')[0];

  glacialLakes.forEach(function(lake) {
    var glofKey = "GLOF_" + lake.name.replace(/[^a-zA-Z0-9]/g, "") + "_" + todayDateStr;
    if (!scriptProperties.getProperty(glofKey)) {
      var url = "https://api.open-meteo.com/v1/forecast?latitude=" + lake.lat + "&longitude=" + lake.lon + 
                "&daily=temperature_2m_max&timezone=auto";
      try {
        var response = UrlFetchApp.fetch(url);
        var json = JSON.parse(response.getContentText());

        if (json.daily && json.daily.temperature_2m_max) {
          var maxTemp = json.daily.temperature_2m_max[0];

          // Trigger alert if high altitude max temp goes above 2.0°C
          if (maxTemp > 2.0) {
            var msg = "🧊 *GLACIAL LAKE MELT / THERMAL SURGE WARNING*\n\n" +
                      "📍 *Target Lake:* " + lake.name + " (" + lake.alt + ")\n" +
                      "🌡️ *Peak Temp Today:* `" + maxTemp.toFixed(1) + "°C` (Thermal Thaw Condition Active)\n" +
                      "⚠️ *Risk Assessment:* Accelerated glacial melt rate & structural moraine dam pressure.";

            var geeLink = GEE_APP_URL + "?lat=" + lake.lat + "&lon=" + lake.lon + "&zoom=13&radius=5000";
            var photoUrl = getFreeStaticMapUrl(lake.lat, lake.lon, 12);

            var inlineKeyboard = {
              "inline_keyboard": [
                [
                  { "text": "🛰️ Inspect Glacier Lake in GEE", "url": geeLink }
                ]
              ]
            };

            sendTelegramWithPhoto(photoUrl, msg, inlineKeyboard);
            scriptProperties.setProperty(glofKey, "true");
          }
        }
      } catch (e) {
        Logger.log("GLOF API Error: " + e.toString());
      }
    }
  });
}

/**
 * 5️⃣ TELEGRAM INCOMING WEBHOOK HANDLER
 */
function doPost(e) {
  try {
    var contents = JSON.parse(e.postData.contents);
    
    if (contents.message && contents.message.text) {
      var message = contents.message;
      var targetChatId = message.chat ? message.chat.id : CHAT_ID;
      
      // Clean command string: removes spaces, slashes, caps, and bot @names
      var rawText = message.text.trim().toLowerCase();
      var cleanCmd = rawText.split("@")[0].split(" ")[0].replace("/", "");

      if (cleanCmd === "status") {
        var scriptProperties = PropertiesService.getScriptProperties();
        var keys = scriptProperties.getKeys().length;
        var statusMsg = "🟢 *SYSTEM STATUS: ONLINE*\n\n" +
                        "• *Target Region:* Nepal & Himalayas\n" +
                        "• *Events Logged in Memory:* `" + keys + "`\n" +
                        "• *Active Sensors:* USGS Seismic, NASA FIRMS, Open-Meteo Saturation & GLOF Thermo-Surge";
        sendTelegramReply(targetChatId, statusMsg);
      }
      else if (cleanCmd === "check") {
        sendTelegramReply(targetChatId, "🔄 *Running manual diagnostic check on all 4 hazard feeds...*");
        checkUSGSAndSendAlerts();
        checkNASAFirmsWildfiresAndSendAlerts();
        checkLiveRainfallAndSendAlerts();
        checkGLOFHighAltitudeHazards();
        sendTelegramReply(targetChatId, "✅ *Manual scan complete across all feeds.*");
      }
      else if (cleanCmd === "basins") {
        var basinsList = "🌊 *12 Monitored River Basins & Flash-Flood Corridors:*\n\n" +
                         "1. Pokhara / Seti River\n" +
                         "2. Chitwan / Narayani River\n" +
                         "3. Saptakoshi / Eastern Koshi\n" +
                         "4. Rasuwa / Bhotekoshi Gorge (GLOF)\n" +
                         "5. Karnali Basin / Chisapani\n" +
                         "6. Mahakali River Basin\n" +
                         "7. West Rapti / Banke Plains\n" +
                         "8. Babai River Basin\n" +
                         "9. Kankai / Kamala Basin\n" +
                         "10. Kathmandu Valley Basin\n" +
                         "11. Jajarkot & Bheri Corridor\n" +
                         "12. Kavre & Roshi Khola Zone";
        sendTelegramReply(targetChatId, basinsList);
      }
      else {
        var helpMsg = "🛰️ *Himalayan Hazard Decision Support System*\n\n" +
                      "Available Commands:\n" +
                      "• `/status` - Check system state\n" +
                      "• `/check` - Manually force run hazard listeners\n" +
                      "• `/basins` - View monitored hydrological zones";
        sendTelegramReply(targetChatId, helpMsg);
      }
    }
  } catch (err) {
    Logger.log("doPost Error: " + err.toString());
  }
}

/**
 * 6️⃣ WEBHOOK SETUP LINK
 */
function setTelegramWebhook() {
  var webAppUrl = "https://script.google.com/macros/s/AKfycbwpA6aby9O-AK2hCTg7EuZPs3cuiJeBjxyTzl582Jsa-gIT0Wa976xOvisUUFMRGkU1/exec"; 
  var url = "https://api.telegram.org/bot" + TELEGRAM_TOKEN + "/setWebhook?url=" + webAppUrl;
  
  var response = UrlFetchApp.fetch(url);
  Logger.log("Webhook Response: " + response.getContentText());
}
