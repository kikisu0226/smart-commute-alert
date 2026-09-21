import os
import sys
import requests

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CWA_API_KEY = os.getenv("CWA_API_KEY")
MOENV_API_KEY = os.getenv("MOENV_API_KEY")
LOCATION_NAME = os.getenv("LOCATION_NAME", "臺北市")

def check_env_vars():
    missing = []
    if not TELEGRAM_BOT_TOKEN: missing.append("TELEGRAM_BOT_TOKEN")
    if not TELEGRAM_CHAT_ID: missing.append("TELEGRAM_CHAT_ID")
    if not CWA_API_KEY: missing.append("CWA_API_KEY")
    if not MOENV_API_KEY: missing.append("MOENV_API_KEY")
    if missing:
        print(f"錯誤：缺少環境變數：{', '.join(missing)}")
        sys.exit(1)

def get_weather_data(location):
    url = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001"
    params = {"Authorization": CWA_API_KEY, "locationName": location}
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        location_data = data["records"]["location"][0]
        max_pop = 0
        max_temp = 0
        for element in location_data["weatherElement"]:
            if element["elementName"] == "PoP12h":
                pops = [int(item["parameter"]["parameterName"]) for item in element["time"] if item["parameter"]["parameterName"].isdigit()]
                if pops: max_pop = max(pops)
            elif element["elementName"] == "MaxT":
                temps = [int(item["parameter"]["parameterName"]) for item in element["time"] if item["parameter"]["parameterName"].isdigit()]
                if temps: max_temp = max(temps)
        return max_temp, max_pop
    except Exception as e:
        print(f"氣象資料取得失敗: {e}")
        sys.exit(1)

def get_aqi_data(location):
    url = "https://data.moenv.gov.tw/api/v2/aqx_p_432"
    params = {"language": "zh", "api_key": MOENV_API_KEY, "limit": 1000}
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        records = response.json().get("records", [])
        matched_aqi = []
        for rec in records:
            if location in rec.get("county", "") or location in rec.get("sitename", ""):
                if rec.get("aqi", "").isdigit():
                    matched_aqi.append(int(rec.get("aqi")))
        return max(matched_aqi) if matched_aqi else 0
    except Exception as e:
        print(f"AQI資料取得失敗: {e}")
        sys.exit(1)

def generate_advices(max_temp, max_pop, aqi):
    advices = []
    if max_pop >= 60:
        advices.append("🌧️ 降雨機率達 60% 以上，出門請記得攜帶雨傘！")
    if max_temp >= 33:
        advices.append("☀️ 最高溫達 33°C 以上，請注意防曬並多補充水分！")
    if aqi >= 100:
        advices.append("😷 AQI 達到 100 以上，建議配戴口罩！")
    if not advices:
        advices.append("🟢 今日各項指標良好，非常適合外出通勤！")
    return advices

def send_telegram_message(message):
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
    max_temp, max_pop = get_weather_data(LOCATION_NAME)
    aqi = get_aqi_data(LOCATION_NAME)
    advices = generate_advices(max_temp, max_pop, aqi)
    
    msg = [
        f"🚌 *智慧通勤風險通知 - {LOCATION_NAME}*",
        "------------------------------------",
        f"🌡️ **預報最高溫**：`{max_temp} °C`",
        f"🌧️ **最高降雨機率**：`{max_pop} %`",
        f"🍃 **空氣品質 AQI**：`{aqi}`",
        "------------------------------------",
        "💡 **通勤建議**："
    ]
    for a in advices:
        msg.append(f"- {a}")
        
    send_telegram_message("\n".join(msg))

if __name__ == "__main__":
    main()
