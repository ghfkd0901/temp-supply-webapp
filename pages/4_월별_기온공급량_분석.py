import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import holidays
from pathlib import Path
import plotly.subplots as sp

st.title("월별 공급량 및 기온 분석")

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

default_years = [2023, 2024, 2025]
selected_years = st.sidebar.multiselect("연도 선택", sorted(data['연'].unique()), default=default_years)

unit = st.sidebar.radio("단위 선택", ['부피 (M3)', '열량 (MJ)'], index=0)

selected_months = st.sidebar.multiselect("월 선택", sorted(data['월'].unique()), default=list(range(1, 13)))

monthly_summary = data[(data['연'].isin(selected_years)) & (data['월'].isin(selected_months))].groupby(['연', '월']).agg(
    평균기온=('평균기온', 'mean'),
    공급량_M3=('공급량(M3)', 'sum'),
    공급량_MJ=('공급량(MJ)', 'sum'),
    공휴일=('공휴일', lambda x: '추석' if any('추석' in str(i) for i in x) else ('설날' if any('설날' in str(i) for i in x) else ''))
).reset_index()

monthly_summary['누적공급량_M3'] = monthly_summary.groupby('연')['공급량_M3'].cumsum()
monthly_summary['누적공급량_MJ'] = monthly_summary.groupby('연')['공급량_MJ'].cumsum()

st.write("### 월별 공급량 및 기온 그래프")

fig = go.Figure()

colors = {2023: 'blue', 2024: 'red', 2025: 'green'}

for year in selected_years:
    year_data = monthly_summary[monthly_summary['연'] == year]
    fig.add_trace(go.Bar(
        x=year_data['월'].astype(str),
        y=year_data['공급량_M3'] if unit == '부피 (M3)' else year_data['공급량_MJ'],
        name=f"{year} 공급량",
        marker_color=colors.get(year, 'gray'),
        yaxis='y1',
        text=year_data['공휴일'],
        textposition='outside'
    ))
    fig.add_trace(go.Scatter(
        x=year_data['월'].astype(str),
        y=year_data['평균기온'],
        name=f"{year} 평균기온",
        line=dict(color=colors.get(year, 'gray'), width=2),
        mode='lines+markers',
        yaxis='y2'
    ))

fig.update_layout(
    yaxis=dict(title="공급량(M3)" if unit == '부피 (M3)' else "공급량(MJ)", side='left', showgrid=True),
    yaxis2=dict(title="평균기온(℃)", side='right', overlaying='y', showgrid=False),
    xaxis=dict(title="월"),
    barmode='group',
    height=500
)

st.write("### 월별 누적 공급량 그래프")

fig_cumulative = go.Figure()

for year in selected_years:
    year_data = monthly_summary[monthly_summary['연'] == year]
    fig_cumulative.add_trace(go.Scatter(
        x=year_data['월'].astype(str),
        y=year_data['누적공급량_M3'] if unit == '부피 (M3)' else year_data['누적공급량_MJ'],
        name=f"{year} 누적 공급량",
        line=dict(color=colors.get(year, 'gray'), width=2),
        mode='lines+markers'
    ))

fig_cumulative.update_layout(
    yaxis=dict(title="누적 공급량(M3)" if unit == '부피 (M3)' else "누적 공급량(MJ)", side='left', showgrid=True),
    xaxis=dict(title="월"),
    height=500
)

col1, col2 = st.columns(2)
col1.plotly_chart(fig, use_container_width=True)
col2.plotly_chart(fig_cumulative, use_container_width=True)

st.write("### 월별 데이터 요약")
monthly_summary_display = monthly_summary.copy()
monthly_summary_display['공급량'] = monthly_summary_display['공급량_M3'] if unit == '부피 (M3)' else monthly_summary_display['공급량_MJ']
monthly_summary_display['공급량'] = monthly_summary_display['공급량'].apply(lambda x: f"{x:,.0f}")
monthly_summary_display['평균기온'] = monthly_summary_display['평균기온'].round(1)
st.dataframe(monthly_summary_display[['연', '월', '평균기온', '공급량', '공휴일']])
