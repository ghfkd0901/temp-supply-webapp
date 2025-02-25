import requests
import pandas as pd
from datetime import datetime, timedelta
import os

# 어제 날짜 구하기
yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
yesterday_hyphen = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

# 기상청 ASOS API 요청 및 데이터 가져오기
service_key = "oBHTNIKevpXpwRCwxrdKSjd6FmUe1ix0zzu+QudQCzhlV8v4ZziSpv4qcXke0hAH+ha6wO7OeHlM8CeImAbnNQ=="

url = "http://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList"

params = {
    'serviceKey': service_key,
    'pageNo': '1',
    'numOfRows': '10',
    'dataType': 'JSON',
    'dataCd': 'ASOS',
    'dateCd': 'DAY',
    'startDt': yesterday,
    'endDt': yesterday,
    'stnIds': '143'  # 대구 지점번호
}

response = requests.get(url, params=params)
data = response.json()

result_code = data['response']['header']['resultCode']
result_msg = data['response']['header']['resultMsg']

if result_code != '00':
    print(f"API 호출 실패: {result_msg}")
else:
    items = data['response']['body']['items']['item']
    df_new = pd.DataFrame(items)
    
    # 필요한 컬럼만 선택하고 영어 컬럼명 적용
    df_new = df_new[['tm', 'avgTa', 'minTa', 'maxTa']]
    df_new.rename(columns={'tm': 'date', 'avgTa': 'avg_temp', 'minTa': 'min_temp', 'maxTa': 'max_temp'}, inplace=True)
    df_new[['avg_temp', 'min_temp', 'max_temp']] = df_new[['avg_temp', 'min_temp', 'max_temp']].astype(float)

    # CSV 파일 경로
    csv_path = r'D:\1_Project\기온및공급량웹앱\data\weather_supply.csv'

    # 기존 CSV 파일이 존재하면 불러와서 이어붙이기
    if os.path.exists(csv_path):
        df_existing = pd.read_csv(csv_path, encoding='utf-8', sep=',', on_bad_lines='skip')

        # CSV 컬럼명 확인 및 '날짜' 컬럼명 변환
        df_existing.rename(columns={'날짜': 'date'}, inplace=True)

        # 중복 방지
        if 'date' in df_existing.columns and yesterday_hyphen in df_existing['date'].values:
            print(f"{yesterday_hyphen} 데이터가 이미 존재합니다.")
        else:
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            df_combined.to_csv(csv_path, index=False, encoding='utf-8', sep=',', quoting=1)
            print(f"✅ {yesterday_hyphen} 데이터 추가 완료! CSV 파일 업데이트 완료.")
    else:
        # CSV 파일이 없으면 새로 생성 (쉼표 강제 적용)
        df_new.to_csv(csv_path, index=False, encoding='utf-8', sep=',', quoting=1)
        print(f"✅ {csv_path} 파일 생성 및 {yesterday_hyphen} 데이터 저장 완료!")
