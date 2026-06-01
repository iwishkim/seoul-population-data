import os
import time
import requests
import pandas as pd
from datetime import datetime
from urllib.parse import quote
import xml.etree.ElementTree as ET

API_KEY = os.environ["SEOUL_API_KEY"]

AREA_LIST = [
    "잠실종합운동장",
    "왕십리역",
    "신논현역·논현역",
    "연신내역",
    "군자역",
    "혜화역",
    "고속터미널역",
    "고덕역",
    "오목교역·목동운동장",
    "사당역",
    "총신대입구(이수)역",
    "합정역",
    "청계산",
    "신촌 스타광장",
    "수유역",
]

CSV_FILE = "data/seoul_population_log.csv"


def fetch_population(area_name):
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
        "수집시간": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "지역명": area_name,
        "API지역명": root.findtext(".//AREA_NM"),
        "혼잡도": root.findtext(".//AREA_CONGEST_LVL"),
        "혼잡도메시지": root.findtext(".//AREA_CONGEST_MSG"),
        "최소인구": min_pop,
        "최대인구": max_pop,
        "중앙추정인구": (
            pd.to_numeric(min_pop, errors="coerce")
            + pd.to_numeric(max_pop, errors="coerce")
        ) / 2,
        "업데이트시간": root.findtext(".//PPLTN_TIME"),
    }


def main():
    rows = []

    for area in AREA_LIST:
        try:
            row = fetch_population(area)
            rows.append(row)
            print("성공:", area, row["혼잡도"])
            time.sleep(1)
        except Exception as e:
            print("실패:", area, e)

    if not rows:
        raise Exception("수집된 데이터가 없습니다.")

    new_df = pd.DataFrame(rows)

    os.makedirs("data", exist_ok=True)

    if os.path.exists(CSV_FILE):
        old_df = pd.read_csv(CSV_FILE, encoding="utf-8-sig")
        df = pd.concat([old_df, new_df], ignore_index=True)
    else:
        df = new_df

    df.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")

    print("저장 완료:", CSV_FILE)


if __name__ == "__main__":
    main()
