import os
import streamlit as st
import pandas as pd
import holidays
import pickle
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from datetime import datetime, timedelta
from pathlib import Path

st.set_page_config(layout="wide")
st.title("일별 기온 예측")

# ✅ 프로젝트 루트 디렉토리 기준 상대경로 설정
BASE_DIR = Path(os.getcwd())
DATA_PATH = BASE_DIR / "data" / "weather_supply.csv"

# ✅ 1️⃣ 데이터 로드 함수 (CSV 파일 사용, 컬럼명을 한국어로 변경)
@st.cache_data
def load_data():
    """CSV 파일에서 데이터 로드 및 컬럼명 한국어로 변경"""
    df = pd.read_csv(DATA_PATH, encoding='utf-8', sep=',')
    
    column_mapping = {
        'date': '날짜',
        'avg_temp': '평균기온',
        'max_temp': '최고기온',
        'min_temp': '최저기온',
        'supply_m3': '공급량(M3)',
        'supply_mj': '공급량(MJ)',
    }
    
    df.rename(columns=column_mapping, inplace=True)
    return df[['날짜', '평균기온', '최고기온', '최저기온', '공급량(M3)', '공급량(MJ)']]

# ✅ 2️⃣ 컬럼 추가 함수
def add_columns(df):
    """데이터프레임에 연, 월, 일, 요일, 공휴일 컬럼 추가"""
    df = df.copy()
    df['날짜'] = pd.to_datetime(df['날짜'])
    df['연'] = df['날짜'].dt.year
    df['월'] = df['날짜'].dt.month
    df['일'] = df['날짜'].dt.day

    weekday_map = {0: "월", 1: "화", 2: "수", 3: "목", 4: "금", 5: "토", 6: "일"}
    df['요일'] = df['날짜'].dt.weekday.map(weekday_map)
    
    kr_holidays = holidays.KR(years=df['연'].unique())
    df['공휴일'] = df['날짜'].apply(lambda x: kr_holidays.get(x, ""))

    return df

# ✅ 데이터 로드 및 컬럼 추가 적용
data = load_data()
data = add_columns(data)

def train_and_save_models():
    data_clean = data[['최고기온', '최저기온', '평균기온']].dropna()
    X_temp = data_clean[['최고기온', '최저기온']]
    y_temp = data_clean['평균기온']

    temp_model_linear = LinearRegression().fit(X_temp, y_temp)
    with open('temp_model_linear.pkl', 'wb') as f:
        pickle.dump(temp_model_linear, f)

    temp_model_rf = RandomForestRegressor(random_state=42).fit(X_temp, y_temp)
    with open('temp_model_rf.pkl', 'wb') as f:
        pickle.dump(temp_model_rf, f)

    return temp_model_linear, temp_model_rf

try:
    with open('temp_model_linear.pkl', 'rb') as f:
        temp_model_linear = pickle.load(f)
    with open('temp_model_rf.pkl', 'rb') as f:
        temp_model_rf = pickle.load(f)
    st.success("✅ 모델 로드 완료")
except:
    st.warning("⚠️ 모델 파일이 없어 훈련을 시작합니다...")
    temp_model_linear, temp_model_rf = train_and_save_models()
    st.success("✅ 모델 훈련 및 저장 완료!")

st.sidebar.title("📅 예측 기간 설정")
today = datetime.today()
start_date = st.sidebar.date_input("시작일", today)
end_date = st.sidebar.date_input("종료일", datetime(today.year, today.month + 1, 1) - timedelta(days=1))

if start_date > end_date:
    st.sidebar.error("시작일은 종료일보다 이전이어야 합니다.")

date_range = pd.date_range(start=start_date, end=end_date)
date_df = pd.DataFrame({'날짜': date_range})
date_df['최고기온'] = None
date_df['최저기온'] = None

st.write("### 최고기온, 최저기온 입력")
edited_df = st.data_editor(date_df, num_rows="dynamic")

if st.button("예측하기"):
    if edited_df[['최고기온', '최저기온']].isnull().any().any():
        st.error("❌ 모든 날짜의 최고기온과 최저기온을 입력해주세요.")
    else:
        X_pred = edited_df[['최고기온', '최저기온']]
        edited_df['평균기온(선형회귀)'] = temp_model_linear.predict(X_pred).round(1)
        edited_df['평균기온(랜덤포레스트)'] = temp_model_rf.predict(X_pred).round(1)

        st.session_state['result_temp_df'] = edited_df.copy()

if 'result_temp_df' in st.session_state:
    st.write("### 예측 결과")
    st.dataframe(st.session_state['result_temp_df'])