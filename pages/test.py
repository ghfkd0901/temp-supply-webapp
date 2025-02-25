import os
import streamlit as st
import pandas as pd
import holidays
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from pathlib import Path

st.set_page_config(layout="wide")

st.title("일별 기온 및 공급량 분석 (리눅스 & 윈도우 호환)")

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

# ✅ 사이드바 필터
st.sidebar.title("🗓 필터 선택")
default_years = [2023, 2024, 2025]
current_month = datetime.today().month

selected_years = st.sidebar.multiselect("연도 선택", sorted(data['연'].unique()), default=default_years)
selected_months = st.sidebar.multiselect("월 선택", sorted(data['월'].unique()), default=[current_month])

show_day_info = st.sidebar.checkbox("📌 요일/공휴일 마커 표시", value=True)

filtered_data = data[(data['연'].isin(selected_years)) & (data['월'].isin(selected_months))]
filtered_data['월일'] = filtered_data['월'].astype(str) + '-' + filtered_data['일'].astype(str)

color_map = {2023: 'blue', 2024: 'deepskyblue', 2025: 'red'}

# 📊 그래프 생성 (총 4개)
fig = make_subplots(
    rows=4, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.1,
    subplot_titles=(
        "평균기온(°C) 변화", "공급량(M3) 변화", "누적 공급량(M3)", "기온 vs 공급량 상관관계"
    )
)

if not filtered_data.empty:
    for year in selected_years:
        year_data = filtered_data[filtered_data['연'] == year].copy()

        # ✅ 요일/공휴일 마커 설정
        marker_texts = []
        marker_sizes = []
        for _, row in year_data.iterrows():
            if show_day_info:
                text = row['공휴일'] if row['공휴일'] else row['요일']
                marker_texts.append(text)
                marker_sizes.append(12 if row['공휴일'] else 8)
            else:
                marker_texts.append("")
                marker_sizes.append(8)

        # (1) 평균기온 변화 그래프
        fig.add_trace(go.Scatter(
            x=year_data['월일'], y=year_data['평균기온'],
            mode='lines+markers+text' if show_day_info else 'lines+markers',
            name=f"{year} 평균기온",
            line=dict(color=color_map.get(year), width=2),
            marker=dict(size=marker_sizes),
            text=marker_texts if show_day_info else None,
            textposition='top center' if show_day_info else None,
        ), row=1, col=1)

        # (2) 공급량 변화 그래프
        fig.add_trace(go.Bar(
            x=year_data['월일'], y=year_data['공급량(M3)'],
            name=f"{year} 공급량(M3)",
            marker=dict(color=color_map.get(year), opacity=0.7),
            text=marker_texts if show_day_info else None,
            textposition='outside' if show_day_info else None,
        ), row=2, col=1)

        # (3) 누적 공급량 그래프
        year_data['누적공급량(M3)'] = year_data['공급량(M3)'].cumsum()
        fig.add_trace(go.Scatter(
            x=year_data['월일'], y=year_data['누적공급량(M3)'],
            mode='lines+markers',
            name=f"{year} 누적공급량",
            line=dict(color=color_map.get(year), width=2),
            marker=dict(size=6),
        ), row=3, col=1)

        # (4) 기온 vs 공급량 산점도
        fig.add_trace(go.Scatter(
            x=year_data['평균기온'], y=year_data['공급량(M3)'],
            mode='markers',
            name=f"{year} 상관관계",
            marker=dict(size=10, color=color_map.get(year), line=dict(width=0.5, color='black')),
        ), row=4, col=1)

fig.update_layout(title="일별 기온 및 공급량 분석", height=1300, showlegend=True, hovermode='x unified')

st.plotly_chart(fig, use_container_width=True)
