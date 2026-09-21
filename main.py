import os
import sys
import requests

# 讀取 Telegram Secrets 環境變數
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 地點設定 (預設台北市經緯度)
LOCATION_NAME = os.getenv("LOCATION_NAME", "臺北市")
LATITUDE = float(os.getenv("LATITUDE", "25.04"))
LONGITUDE = float(os.getenv("LONGITUDE", "121.56"))

def check_env_vars():
    """檢查 Telegram 金鑰是否存在"""
    missing = []
    if not TELEGRAM_BOT_TOKEN: missing.append("TELEGRAM_BOT_TOKEN")
    if not TELEGRAM_CHAT_ID: missing.append("TELEGRAM_CHAT_ID")
    
    if missing:
        print(f"錯誤：缺少環境變數：{', '.join(missing)}")
        sys.exit(1)

def get_open_meteo_weather(lat, lon):
    """取得 Open-Meteo 最高溫度與最高降雨機率 (免 API Key)"""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "precipitation_probability_max,temperature_2m_max",
        "forecast_days": 1,
        "timezone": "Asia/Taipei"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        daily_data = data.get("daily", {})
        max_temp = daily_data.get("temperature_2m_max", [0])[0]
        max_pop = daily_data.get("precipitation_probability_max", [0])[0]
        
        return round(max_temp), int(max_pop)
    except Exception as e:
        print(f"取得天氣資料失敗: {e}")
        sys.exit(1)

def get_aqi_data(location):
    """取得環境部 AQI 資料 (使用開放 JSON 網址，免 API Key)"""
    url = "https://data.moenv.gov.tw/api/v2/aqx_p_432?format=json"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        records = response.json().get("records", [])
        matched_aqi = []
        
        for rec in records:
            if location in rec.get("county", "") or location in rec.get("sitename", ""):
                if rec.get("aqi", "").isdigit():
                    matched_aqi.append(int(rec.get("aqi")))
                    
        return max(matched_aqi) if matched_aqi else 0
    except Exception as e:
        print(f"取得 AQI 資料失敗: {e}")
        sys.exit(1)

def generate_advices(max_temp, max_pop, aqi):
    """依據規格條件產生通勤建議"""
    advices = []
    
    # 規格 3: 降雨機率達 60% 時提醒攜帶雨傘
    if max_pop >= 60:
        advices.append("🌧️ 降雨機率達 60% 以上，出門請記得攜帶雨傘！")
        
    # 規格 4: 最高溫度達 33°C 時提醒防曬與補充水分
    if max_temp >= 33:
        advices.append("☀️ 最高溫達 33°C 以上，請注意防曬並多補充水分！")
        
    # 規格 5: AQI 達 100 時提醒配戴口罩
    if aqi >= 100:
        advices.append("😷 AQI 達到 100 以上，建議配戴口罩！")
        
    # 規格 6: 所有條件正常時，顯示適合外出通勤
    if not advices:
        advices.append("🟢 今日各項指標良好，非常適合外出通勤！")
        
    return advices

def send_telegram_message(message):
    """傳送訊息至 Telegram Bot"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        print("Telegram 通知發送成功！")
    except Exception as e:
        print(f"發送 Telegram 訊息失敗: {e}")
        sys.exit(1)

def main():
    check_env_vars()
    
    max_temp, max_pop = get_open_meteo_weather(LATITUDE, LONGITUDE)
    aqi = get_aqi_data(LOCATION_NAME)
    advices = generate_advices(max_temp, max_pop, aqi)
    
    message_lines = [
        f"🚌 *智慧通勤風險通知 - {LOCATION_NAME}*",
        "------------------------------------",
        f"🌡️ **預報最高溫**：`{max_temp} °C`",
        f"🌧️ **最高降雨機率**：`{max_pop} %`",
        f"🍃 **空氣品質 AQI**：`{aqi}`",
        "------------------------------------",
        "💡 **通勤建議**："
    ]
    for advice in advices:
        message_lines.append(f"- {advice}")
        
    send_telegram_message("\n".join(message_lines))

if __name__ == "__main__":
    main()
