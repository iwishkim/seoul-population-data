import os
import time
import requests
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import quote
import xml.etree.ElementTree as ET

API_KEY = os.environ["SEOUL_API_KEY"]

AREA_LIST = [
    "DDP(동대문디자인플라자)","DMC(디지털미디어시티)","가락시장","가로수길","가산디지털단지역",
    "강남 MICE 관광특구","강남역","강서한강공원","건대입구역","경복궁",
    "고덕역","고속터미널역","고척돔","광나루한강공원","광장(전통)시장",
    "광화문·덕수궁","광화문광장","교대역","구로디지털단지역","구로역",
    "국립중앙박물관·용산가족공원","군자역","김포공항","난지한강공원","남대문시장",
    "남산공원","노들섬","노량진","대림역","덕수궁길·정동길",
    "동대문 관광특구","동대문역","뚝섬역","뚝섬한강공원","망원한강공원",
    "명동 관광특구","미아사거리역","반포한강공원","발산역","보라매공원",
    "보신각","북서울꿈의숲","북창동 먹자골목","북촌한옥마을","사당역",
    "삼각지역","서대문독립공원","서리풀공원·몽마르뜨공원","서울 암사동 유적","서울대공원",
    "서울대입구역","서울숲공원","서울식물원·마곡나루역","서울역","서촌",
    "선릉역","성수카페거리","성신여대입구역","송리단길·호수단길","송현녹지광장",
    "수유역","숭례문","시의회 앞","신논현역·논현역","신도림역",
    "신림역","신정네거리역","신촌 스타광장","신촌·이대역","쌍문역",
    "아차산","안양천","압구정로데오거리","양재역","양화한강공원",
    "어린이대공원","여의도","여의도한강공원","여의서로","역삼역",
    "연남동","연신내역","영등포 타임스퀘어","오목교역·목동운동장","올림픽공원",
    "왕십리역","용리단길","용산역","월드컵공원","응봉산",
    "이촌한강공원","이태원 관광특구","이태원 앤틱가구거리","이태원역","익선동",
    "인사동","잠실 관광특구","잠실롯데타워·석촌호수","잠실새내역","잠실역",
    "잠실종합운동장","잠실한강공원","잠원한강공원","장지역","장한평역",
    "종로·청계 관광특구","창덕궁·종묘","창동 신경제 중심지","천호역","청계산",
    "청담동 명품거리","청량리 제기동 일대 전통시장","총신대입구(이수)역","충정로역","합정역",
    "해방촌·경리단길","혜화역","홍대 관광특구","홍대입구역(2호선)","홍제폭포","회기역"
]

CSV_FILE = "data/seoul_population_log.csv"
KST = ZoneInfo("Asia/Seoul")


def fetch_population(area_name, run_time):
    url = (
        f"http://openapi.seoul.go.kr:8088/"
        f"{API_KEY}/xml/citydata_ppltn/1/5/{quote(area_name)}"
    )

    res = requests.get(url, timeout=20)
    res.raise_for_status()

    root = ET.fromstring(res.text)

    code = root.findtext(".//CODE")
    message = root.findtext(".//MESSAGE")

    if code and code != "INFO-000":
        raise Exception(f"{area_name}: {code} / {message}")

    min_pop = root.findtext(".//AREA_PPLTN_MIN")
    max_pop = root.findtext(".//AREA_PPLTN_MAX")

    return {
        "수집시간": run_time,
        "지역명": area_name,
        "API지역명": root.findtext(".//AREA_NM"),
        "혼잡도": root.findtext(".//AREA_CONGEST_LVL"),
        "혼잡도메시지": root.findtext(".//AREA_CONGEST_MSG"),
        "최소인구": min_pop,
        "최대인구": max_pop,
        "업데이트시간": root.findtext(".//PPLTN_TIME"),
    }


def main():
    os.makedirs("data", exist_ok=True)

    run_time = datetime.now(KST).replace(minute=0, second=0, microsecond=0)
    run_time_str = run_time.strftime("%Y-%m-%d %H:%M:%S")

    rows = []

    print("수집 시작:", run_time_str)

    for area in AREA_LIST:
        try:
            row = fetch_population(area, run_time_str)
            rows.append(row)

            print(
                "성공:",
                area,
                row["혼잡도"],
                row["최소인구"],
                "~",
                row["최대인구"],
            )

            time.sleep(1)

        except Exception as e:
            print("실패:", area, e)

    if not rows:
        raise Exception("수집된 데이터가 없습니다.")

    new_df = pd.DataFrame(rows)

    new_df["최소인구"] = pd.to_numeric(new_df["최소인구"], errors="coerce")
    new_df["최대인구"] = pd.to_numeric(new_df["최대인구"], errors="coerce")
    new_df["중앙추정인구"] = (new_df["최소인구"] + new_df["최대인구"]) / 2

    if os.path.exists(CSV_FILE):
        old_df = pd.read_csv(CSV_FILE, encoding="utf-8-sig")
        df = pd.concat([old_df, new_df], ignore_index=True)
    else:
        df = new_df

    df = df.drop_duplicates(
        subset=["수집시간", "지역명"],
        keep="last"
    )

    df["수집시간"] = pd.to_datetime(df["수집시간"], errors="coerce")
    df = df.sort_values(["수집시간", "지역명"])
    df["수집시간"] = df["수집시간"].dt.strftime("%Y-%m-%d %H:%M:%S")

    df.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")

    print("CSV 누적 저장 완료:", CSV_FILE)
    print("총 행 수:", len(df))


if __name__ == "__main__":
    main()
