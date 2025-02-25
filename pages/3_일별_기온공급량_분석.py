import os
import streamlit as st
import pandas as pd
from pathlib import Path
import holidays
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(layout="wide")

st.title("일별 기온 및 공급량 분석")
st.markdown("""
데이터 출처:  
- **기온 데이터**: [기상자료개방포털](https://data.kma.go.kr/climate/RankState/selectRankStatisticsDivisionList.do?pgmNo=179)  
- **공급량 데이터**: 대성에너지 고객지원시스템 → 월별 영업실적/현황조회 → 일별공급량  
- **공휴일 데이터**: Python `holidays` 패키지 활용
""")

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

st.sidebar.title("🗓 필터 선택")
default_years = [2024, 2025]
current_month = datetime.today().month

selected_years = st.sidebar.multiselect("연도 선택", sorted(data['연'].unique()), default=default_years)
selected_months = st.sidebar.multiselect("월 선택", sorted(data['월'].unique()), default=[current_month])

st.sidebar.title("🗒 마커 표시 설정")
show_day_info = st.sidebar.checkbox("요일/공휴일 표시", value=True)

filtered_data = data[(data['연'].isin(selected_years)) & (data['월'].isin(selected_months))]
filtered_data['월일'] = filtered_data['월'].astype(str) + '-' + filtered_data['일'].astype(str)

color_map = {2023: 'blue', 2024: 'deepskyblue', 2025: 'red'}

# (1) 일별 평균기온 변화 그래프
temp_fig = go.Figure()
# (2) 일별 공급량 변화 그래프
supply_fig = go.Figure()
# (3) 기온 vs 공급량 상관관계 그래프
scatter_fig = go.Figure()
# (4) 공급량 누적 그래프
cumulative_fig = go.Figure()

# ✅ 요일 및 공휴일 표시 개선
if not filtered_data.empty:
    for year in selected_years:
        year_data = filtered_data[filtered_data['연'] == year].copy()
        year_data['누적공급량(M3)'] = year_data['공급량(M3)'].cumsum()

        # ✅ 마커 설정
        marker_texts = []  # 요일 또는 공휴일 텍스트
        marker_sizes = []  # 마커 크기 조정 (공휴일 강조)

        for _, row in year_data.iterrows():
            if show_day_info:
                if row['공휴일']:  # 공휴일이 있으면 공휴일 이름을 표시
                    marker_texts.append(row['공휴일'])
                    marker_sizes.append(12)  # 공휴일 강조 (크기 증가)
                else:
                    marker_texts.append(row['요일'])
                    marker_sizes.append(8)  # 일반 요일 (기본 크기)

            else:
                marker_texts.append("")  # 표시하지 않음
                marker_sizes.append(8)

        # (1) 평균기온 변화 그래프 (꺾은선 + 마커)
        temp_fig.add_trace(go.Scatter(
            x=year_data['월일'], y=year_data['평균기온'],
            mode='lines+markers+text' if show_day_info else 'lines+markers',
            name=f"{year} 평균기온",
            line=dict(color=color_map.get(year)),
            marker=dict(size=marker_sizes, symbol='circle'),
            text=marker_texts, textposition='top center', textfont=dict(size=9)
        ))

        # (2) 공급량 변화 그래프 (막대그래프)
        supply_fig.add_trace(go.Bar(
            x=year_data['월일'], y=year_data['공급량(M3)'],
            name=f"{year} 공급량(M3)",
            marker=dict(color=color_map.get(year), opacity=0.5),
            width=0.3
        ))

        # (3) 기온 vs 공급량 상관관계 그래프
        scatter_fig.add_trace(go.Scatter(
            x=year_data['평균기온'], y=year_data['공급량(M3)'],
            mode='markers+text' if show_day_info else 'markers',
            name=f"{year} 상관관계",
            marker=dict(size=10, color=color_map.get(year), line=dict(width=0.5, color='black')),
            text=marker_texts, textposition='top center', textfont=dict(size=9)
        ))

        # (4) 공급량 누적 그래프
        cumulative_fig.add_trace(go.Scatter(
            x=year_data['월일'], y=year_data['누적공급량(M3)'],
            mode='lines+markers',
            name=f"{year} 누적공급량",
            line=dict(color=color_map.get(year), width=2),
            marker=dict(size=6)
        ))


col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(temp_fig, use_container_width=True)
    st.plotly_chart(scatter_fig, use_container_width=True)

with col2:
    st.plotly_chart(supply_fig, use_container_width=True)
    st.plotly_chart(cumulative_fig, use_container_width=True)