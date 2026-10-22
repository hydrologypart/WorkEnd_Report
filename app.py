import streamlit as st
import pandas as pd
import requests
import time
import urllib3
from datetime import datetime

# เพิ่มบรรทัดนี้ลงไปเพื่อใช้งานไลบรารีที่ import มา (จะช่วยให้แจ้งเตือนหายไป)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)



# ============================================================
# ฟังก์ชันดึงข้อมูลน้ำ
# ============================================================
@st.cache_data(ttl=600)
def fetch_water_data():
    url = "ใส่_URL_API_น้ำล้นตลิ่ง_ที่นี่"  # แทนที่ด้วย URL จริงของคุณ

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, verify=False, timeout=15)

        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"เชื่อมต่อได้แต่เซิร์ฟเวอร์ตอบกลับผิดพลาด (Status Code: {response.status_code})")
            return None

    except requests.exceptions.SSLError as e:
        st.error(f"SSL Error: {e}")
        return None
    except requests.exceptions.Timeout:
        st.error("เกิดข้อผิดพลาด: หมดเวลาเชื่อมต่อ (Timeout) เซิร์ฟเวอร์ปลายทางช้าเกินไป")
        return None
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดที่ไม่คาดคิด: {e}")
        return None
    
# ============================================================
# ตั้งค่าหน้าตาเว็บแอป
# ============================================================
st.set_page_config(page_title="ระบบออกรายงานส่งต่อเวร", page_icon="🌊", layout="centered")

# CSS ตกแต่งเพิ่มเติม
st.markdown("""
    <style>
    .main-header { text-align: center; color: #1E3A8A; font-weight: bold; margin-bottom: 20px; }
    .stButton>button { background-color: #2563EB; color: white; border-radius: 8px; height: 3em; font-size: 16px; font-weight: bold; }
    .stButton>button:hover { background-color: #1D4ED8; color: white; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h2 class='main-header'>🌊 ระบบออกรายงานสถานการณ์น้ำและฝน</h2>", unsafe_allow_html=True)

# ============================================================
# ฟังก์ชันประมวลผล (จากสคริปต์ Python ที่เราพัฒนากัน)
# ============================================================
def join_with_and(items):
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} และ {items[1]}"
    return " ".join(items[:-1]) + f" และ {items[-1]}"

def format_thai_date(date_str):
    thai_months = {
        "01": "มกราคม", "02": "กุมภาพันธ์", "03": "มีนาคม", "04": "เมษายน",
        "05": "พฤษภาคม", "06": "มิถุนายน", "07": "กรกฎาคม", "08": "สิงหาคม",
        "09": "กันยายน", "10": "ตุลาคม", "11": "พฤศจิกายน", "12": "ธันวาคม"
    }
    try:
        parts = date_str.split("/")
        if len(parts) == 3:
            day = str(int(parts[0]))
            month = thai_months.get(parts[1], "")
            year = parts[2]
            return f"{day} {month} {year}"
    except Exception:
        pass
    return date_str

def get_overflow_water_level(date, hour):
    url_overflow = "https://hyd-app-db.rid.go.th/webservice/getWaterLevelListReportOverflowWaterLevel.ashx"
    data = {
        "DW[HourlyTime]": hour,
        "DW[TimeCurrent]": date,
        "_search": "false",
        "nd": str(int(time.time() * 1000)),
        "rows": "1000",
        "page": "1",
        "sidx": "indexcount",
        "sord": "asc",
    }
    station_info_dict = {
        'B.1': {'District': 'บ้านลาด', 'Province': 'เพชรบุรี', 'Stream': 'แม่น้ำเพชรบุรี'},
        'B.10': {'District': 'ท่ายาง', 'Province': 'เพชรบุรี', 'Stream': 'แม่น้ำเพชรบุรี'},
        'B.11': {'District': 'หนองหญ้าปล้อง', 'Province': 'เพชรบุรี', 'Stream': 'ห้วยแม่ประจันต์'},
        'B.12': {'District': 'ท่ายาง', 'Province': 'เพชรบุรี', 'Stream': 'ห้วยแม่ประจันต์'},
        'B.13': {'District': 'แก่งกระจาน', 'Province': 'เพชรบุรี', 'Stream': 'แม่น้ำเพชรบุรี'},
        'B.15': {'District': 'เมือง', 'Province': 'เพชรบุรี', 'Stream': 'แม่น้ำเพชรบุรี'},
        'B.16': {'District': 'บ้านลาด', 'Province': 'เพชรบุรี', 'Stream': 'แม่น้ำเพชรบุรี'}
    }
    output_lines = []
    try:
        response = requests.post(url_overflow, data=data, timeout=10)
        if response.status_code == 200:
            json_data = response.json()
            if "rows" in json_data and len(json_data["rows"]) > 0:
                df = pd.DataFrame(json_data["rows"])
                df["waterlevelvalue"] = pd.to_numeric(df["waterlevelvalue"], errors="coerce")
                df["braelevel"] = pd.to_numeric(df["braelevel"], errors="coerce")
                df["overflow_level"] = df["waterlevelvalue"] - df["braelevel"]
                df_overflow = df[df["overflow_level"] > 0].copy()

                if len(df_overflow) == 0:
                    output_lines.append("ไม่มีสถานการณ์น้ำล้นตลิ่ง")
                else:
                    if station_info_dict:
                        df_info = pd.DataFrame.from_dict(station_info_dict, orient="index").reset_index()
                        df_info = df_info.rename(columns={"index": "stationcode"})
                        df_overflow = pd.merge(df_overflow, df_info, on="stationcode", how="left")
                    else:
                        df_overflow["Stream"] = "-"
                        df_overflow["District"] = "-"
                        df_overflow["Province"] = "-"

                    df_overflow = df_overflow.sort_values(by=["hydroid", "stationcode"], ascending=[True, True])
                    status_mapping = {
                        "ระดับน้ำเพิ่มขึ้น": "แนวโน้มเพิ่มขึ้น",
                        "ระดับน้ำลดลง": "แนวโน้มลดลง",
                        "ระดับน้ำทรงตัว": "แนวโน้มทรงตัว",
                    }
                    df_overflow["wlstatus"] = df_overflow["wlstatus"].replace(status_mapping)

                    total_stations = len(df_overflow)
                    output_lines.append(f"สถานการณ์น้ำล้นตลิ่ง {total_stations} สถานี")

                    for _, row in df_overflow.iterrows():
                        st_code = row.get("stationcode", "-")
                        stream = row.get("Stream", "-")
                        district = row.get("District", "-")
                        province = row.get("Province", "-")
                        status = row.get("wlstatus", "-")
                        output_lines.append(f"- สถานี {st_code} {stream} อ.{district} จ.{province} {status}")

                    time_col = None
                    for col in ['time', 'timerecord', 'waterleveltime', 'datatime', 'reporttime']:
                        if col in df_overflow.columns:
                            time_col = col
                            break

                    output_lines.append("")
                    output_lines.append("หมายเหตุ:")

                    if time_col:
                        time_groups = df_overflow.groupby(time_col)['stationcode'].apply(list).to_dict()
                        for t_val, codes in time_groups.items():
                            station_list_str = join_with_and([f"สถานี {c}" for c in codes])
                            t_str = str(t_val).strip()
                            if len(t_str) > 5 and ":" in t_str:
                                t_str = t_str[:5]
                            output_lines.append(f"- {station_list_str} ใช้ข้อมูล ณ เวลา {t_str} น.")
                    else:
                        all_codes = [row.get("stationcode", "-") for _, row in df_overflow.iterrows()]
                        station_list_str = join_with_and([f"สถานี {c}" for c in all_codes])
                        display_h = hour[:5] if len(hour) >= 5 else hour
                        output_lines.append(f"- {station_list_str} ใช้ข้อมูล ณ เวลา {display_h} น.")
            else:
                output_lines.append("ไม่มีสถานการณ์น้ำล้นตลิ่ง")
        else:
            output_lines.append("ไม่สามารถเชื่อมต่อ API น้ำล้นตลิ่งได้")
    except Exception:
        output_lines.append("ไม่สามารถเชื่อมต่อ API น้ำล้นตลิ่งได้")

    return output_lines

def get_rain_and_warning_data():
    url_rain24h = "https://api-v3.thaiwater.net/api/v1/thaiwater30/public/rain_24h"
    rain_output_lines = []
    fallback_provinces = []
    
    try:
        response_rain24h = requests.get(url_rain24h, timeout=10)
        if response_rain24h.status_code == 200:
            data_rain = response_rain24h.json()
            if data_rain.get("result") == "OK":
                stations = data_rain.get("data", [])
                data_list = []
                for item in stations:
                    station = item.get("station", {})
                    st_name = station.get("tele_station_code", "") or station.get("tele_station_name", {}).get("th", "Unknown")
                    geocode = item.get("geocode", {})
                    tb_name = geocode.get("tumbon_name", {}).get("th", "")
                    ap_name = geocode.get("amphoe_name", {}).get("th", "")
                    pv_name = geocode.get("province_name", {}).get("th", "")
                    rn_val = item.get("rain_24h")
                    
                    clean_pv = str(pv_name).replace("จ.", "").strip()
                    try:
                        rain_val = float(rn_val) if rn_val is not None else 0.0
                    except (ValueError, TypeError):
                        rain_val = 0.0

                    data_list.append({
                        "ชื่อสถานี": st_name, "ตำบล": tb_name, "อำเภอ": ap_name,
                        "จังหวัด": clean_pv, "rain_24h": rain_val
                    })

                df_all = pd.DataFrame(data_list)
                df_90 = df_all[df_all["rain_24h"] >= 90].copy()
                
                if not df_90.empty:
                    for p in df_90["จังหวัด"].unique():
                        fallback_provinces.append(f"จ.{p}" if p != "กรุงเทพมหานคร" else p)

                if len(df_90) < 6:
                    df = df_all.sort_values(by="rain_24h", ascending=False).head(5)
                else:
                    df = df_90.sort_values(by="rain_24h", ascending=False)

                station_count = len(df)
                if station_count == 0 or df["rain_24h"].max() == 0:
                    rain_output_lines.append("***ไม่มีปริมาณฝนสะสม 24 ชม. จากการตรวจวัดทั่วประเทศไทย***")
                elif station_count <= 15:
                    for _, row in df.iterrows():
                        prov_name = row['จังหวัด']
                        formatted_prov = f"จ.{prov_name}" if prov_name != "กรุงเทพมหานคร" else prov_name
                        rain_output_lines.append(f"- สถานี{row['ชื่อสถานี']} ต.{row['ตำบล']} อ.{row['อำเภอ']} {formatted_prov} {row['rain_24h']} มม.")
                else:
                    province_df = df.groupby("จังหวัด")["rain_24h"].max().reset_index().sort_values(by="rain_24h", ascending=False)
                    cat_over_200 = province_df[province_df["rain_24h"] >= 200]
                    cat_150_199 = province_df[(province_df["rain_24h"] >= 150) & (province_df["rain_24h"] < 200)]
                    cat_100_149 = province_df[(province_df["rain_24h"] >= 100) & (province_df["rain_24h"] < 150)]
                    cat_90_99   = province_df[(province_df["rain_24h"] >= 90) & (province_df["rain_24h"] < 100)]

                    def format_province_list(sub_df, range_name):
                        if sub_df.empty:
                            return f"ไม่มีพื้นที่ใดมีปริมาณฝนสะสม 24 ชม. ในช่วง{range_name}"
                        items = [f"จ.{row['จังหวัด']}" if row['จังหวัด'] != "กรุงเทพมหานคร" else row['จังหวัด'] for _, row in sub_df.iterrows()]
                        return join_with_and(items)

                    rain_output_lines.append(f"- พื้นที่มีปริมาณฝนมากกว่า 200 มม.:\n{format_province_list(cat_over_200, 'มากกว่า 200 มม.')}")
                    rain_output_lines.append(f"- พื้นที่มีปริมาณฝน 150 - 199 มม.:\n{format_province_list(cat_150_199, '150 - 199 มม.')}")
                    rain_output_lines.append(f"- พื้นที่มีปริมาณฝน 100 - 149 มม.:\n{format_province_list(cat_100_149, '100 - 149 มม.')}")
                    rain_output_lines.append(f"- พื้นที่มีปริมาณฝน 90 - 99 มม.:\n{format_province_list(cat_90_99, '90 - 99 มม.')}")
    except Exception:
        rain_output_lines.append("ไม่สามารถเชื่อมต่อกับ API ฝน 24 ชม. ได้")

    url_warning = "https://www.thaiwater.net/proxy/riskrainfall48h.php?file=https://api.hii.or.th/v2/4UQaYnf0Bx4fXPYyCdDRbqHyXH9Ixvd2nVUjaN1cLBY=/warning/flashflood-48h"
    regions = {
        "ภาคเหนือตอนบน": ["เชียงใหม่", "ลำพูน", "ลำปาง", "แพร่", "น่าน", "พะเยา", "เชียงราย", "แม่ฮ่องสอน"],
        "ภาคเหนือตอนล่าง": ["เพชรบูรณ์", "พิจิตร", "พิษณุโลก", "อุตรดิตถ์", "สุโขทัย", "ตาก", "กำแพงเพชร"],
        "ภาคตะวันออกเฉียงเหนือตอนบน": ["ขอนแก่น", "อุดรธานี", "หนองคาย", "บึงกาฬ", "เลย", "สกลนคร", "นครพนม", "กาฬสินธุ์", "มหาสารคาม", "ยโสธร", "ร้อยเอ็ด", "ชัยภูมิ", "มุกดาหาร", "หนองบัวลำภู"],
        "ภาคตะวันออกเฉียงเหนือตอนล่าง": ["นครราชสีมา", "อุบลราชธานี", "บุรีรัมย์", "สุรินทร์", "ศรีสะเกษ", "อำนาจเจริญ"],
        "ภาคกลาง": ["ชัยนาท", "นครสวรรค์", "อุทัยธานี", "สิงห์บุรี", "อ่างทอง", "พระนครศรีอยุธยา", "ลพบุรี", "สระบุรี", "ปทุมธานี", "นนทบุรี", "สมุทรปราการ", "กรุงเทพมหานคร"],
        "ภาคตะวันออก": ["ชลบุรี", "ระยอง", "ฉะเชิงเทรา", "จันทบุรี", "ตราด", "ปราจีนบุรี", "นครนายก", "สระแก้ว"],
        "ภาคตะวันตก": ["กาญจนบุรี", "เพชรบุรี", "นครปฐม", "สมุทรสาคร", "สมุทรสงคราม", "ราชบุรี", "สุพรรณบุรี", "ประจวบคีรีขันธ์"],
        "ภาคใต้": ["พัทลุง", "ชุมพร", "ระนอง", "สุราษฎร์ธานี", "ภูเก็ต", "พังงา", "นครศรีธรรมราช", "กระบี่", "ตรัง", "สงขลา", "สตูล", "ปัตตานี", "ยะลา", "นราธิวาส"]
    }
    top_provinces = {
        "ภาคเหนือตอนบน": 3, "ภาคเหนือตอนล่าง": 3, "ภาคตะวันออกเฉียงเหนือตอนบน": 4,
        "ภาคตะวันออกเฉียงเหนือตอนล่าง": 3, "ภาคกลาง": 4, "ภาคตะวันออก": 3,
        "ภาคตะวันตก": 3, "ภาคใต้": 4
    }

    is_from_warning_api = True
    try:
        response_warning = requests.get(url_warning, timeout=10)
        data_warning = response_warning.json()
    except Exception:
        data_warning = {}

    if "area" not in data_warning:
        warning_output = "ไม่มีพื้นที่เตือนภัย"
    else:
        areas = data_warning["area"]
        province_rain = {}
        for item in areas:
            province = item.get("province")
            rainfall = item.get("sum_rainfall_48h")
            if not province or rainfall is None:
                continue
            province = province.replace("จ.", "").strip()
            try:
                rainfall = float(rainfall)
            except ValueError:
                continue
            if province not in province_rain or rainfall > province_rain[province]:
                province_rain[province] = rainfall

        region_results = []
        individual_provinces = []
        for region, provinces in regions.items():
            warning_in_region = [{"province": p, "rainfall": province_rain[p]} for p in provinces if p in province_rain]
            warning_count = len(warning_in_region)
            total_count = len(provinces)
            if warning_count == 0:
                continue
            percentage = (warning_count / total_count) * 100
            if percentage >= 70:
                warning_in_region.sort(key=lambda x: x["rainfall"], reverse=True)
                top_n = top_provinces[region]
                top_list = warning_in_region[:top_n]
                top_text_list = [f"จ.{item['province']}" for item in top_list]
                region_results.append(f"{region} ได้แก่ {join_with_and(top_text_list)}")
            else:
                for item in warning_in_region:
                    individual_provinces.append(f"จ.{item['province']}")

        if not region_results and not individual_provinces:
            warning_output = "ไม่มีพื้นที่เตือนภัย"
        elif not region_results and individual_provinces:
            warning_output = join_with_and(individual_provinces)
        elif region_results and not individual_provinces:
            warning_output = join_with_and(region_results)
        else:
            province_text = " ".join(individual_provinces)
            region_text = join_with_and(region_results)
            warning_output = f"{province_text} {region_text}"

    if warning_output == "ไม่มีพื้นที่เตือนภัย":
        if fallback_provinces:
            warning_output = join_with_and(fallback_provinces)
            is_from_warning_api = False
        else:
            warning_output = "ไม่มีพื้นที่เสี่ยงภัยจากปริมาณฝนสะสม 48 ชม."
            is_from_warning_api = False

    return rain_output_lines, warning_output, is_from_warning_api

# ============================================================
# หน้าจอ UI สำหรับใช้งาน
# ============================================================
col1, col2 = st.columns(2)

with col1:
    today_str = datetime.now().strftime("%d/%m/%Y")
    input_date = st.text_input("📅 วันที่ (DD/MM/YYYY)", value=today_str)

with col2:
    input_time = st.text_input("⏰ เวลา (xx.xx เช่น 06.00 หรือ 18.00)", value="18.00")

st.markdown("<br>", unsafe_allow_html=True)

if st.button("🚀 ประมวลผลและสร้างรายงาน", use_container_width=True):
    if not input_date or not input_time:
        st.error("กรุณากรอกวันที่และเวลาให้ครบถ้วน")
    else:
        with st.spinner("กำลังดึงข้อมูลจาก API และจัดทำรายงาน..."):
            if "." in input_time:
                parts = input_time.split(".")
                hour_part = parts[0].zfill(2)
                minute_part = parts[1].zfill(2) if len(parts) > 1 else "00"
                api_hour = f"{hour_part}:{minute_part}:00"
                display_time = f"{hour_part}:{minute_part} น."
            else:
                api_hour = "18:00:00"
                display_time = "18:00 น."

            shift_text = "กลางวัน" if api_hour < "12:00:00" else "กลางคืน"
            formatted_thai_date = format_thai_date(input_date)

            overflow_results = get_overflow_water_level(input_date, api_hour)
            rain_results, warning_results, is_from_warning_api = get_rain_and_warning_data()

            report_lines = []
            report_lines.append("เรียน ผอท.บอ. และ สพ.บอ.")
            report_lines.append(f"ส่งต่อเวร{shift_text}")
            report_lines.append(f"วันที่ {formatted_thai_date} เวลา {display_time}\n")

            for line in overflow_results:
                report_lines.append(line)
            report_lines.append("")

            report_lines.append("ปริมาณฝนสะสม 24 ชม.")
            for line in rain_results:
                report_lines.append(line)
            report_lines.append("")

            if is_from_warning_api:
                report_lines.append("พื้นที่เสี่ยงภัยเนื่องจากปริมาณฝนสะสม 48 ชม.")
            else:
                report_lines.append("พื้นที่เฝ้าระวังเพิ่มเติม")
                
            report_lines.append(warning_results)

            report_content = "\n".join(report_lines)

        st.success("สร้างรายงานสำเร็จ!")
        st.text_area("📋 ข้อความรายงาน (กดคัดลอกนำไปใช้งานได้ทันที):", value=report_content, height=350)