import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.error("⚠️ 접근 권한이 없습니다. 메인 페이지에서 비밀번호 인증을 해주세요.")
    st.stop()
    
st.set_page_config(layout="wide")

st.title("일별 기온 및 공급량 분석")
st.markdown("""
데이터 출처:  
- **기온 데이터**: [기상자료개방포털](https://data.kma.go.kr/climate/RankState/selectRankStatisticsDivisionList.do?pgmNo=179)  
- **공급량 데이터**: 대성에너지 고객지원시스템 → 월별 영업실적/현황조회 → 일별공급량  
- **공휴일 데이터**: Python `holidays` 패키지 활용
""")

@st.cache_data
def load_data():
    file_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'weather_supply.xlsx')
    sheet_name = "일별기온공급량"
    df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')
    df = df[['날짜', '평균기온', '공급량(M3)', '공급량(MJ)', '연', '월', '일', '요일', '공휴일']]
    df['연'] = df['연'].astype(int)
    df['월'] = df['월'].astype(int)
    df['일'] = df['일'].astype(int)
    return df

data = load_data()

st.sidebar.title("🗓 필터 선택")
default_years = [2023, 2024, 2025]
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

if not filtered_data.empty:
    for year in selected_years:
        year_data = filtered_data[filtered_data['연'] == year].copy()
        year_data['누적공급량(M3)'] = year_data['공급량(M3)'].cumsum()

        marker_symbols = []
        marker_sizes = []
        marker_texts = []

        for _, row in year_data.iterrows():
            if pd.notna(row['공휴일']):
                marker_symbols.append('star')
                marker_sizes.append(12)
                marker_texts.append(row['공휴일'])
            else:
                marker_symbols.append('circle')
                marker_sizes.append(8)
                marker_texts.append(row['요일'])

        if not show_day_info:
            marker_texts = [''] * len(marker_texts)

        # (1) 평균기온 변화
        temp_fig.add_trace(go.Scatter(
            x=year_data['월일'], y=year_data['평균기온'],
            mode='lines+markers+text' if show_day_info else 'lines+markers',
            name=f"{year} 평균기온",
            line=dict(color=color_map.get(year)),
            marker=dict(size=marker_sizes, symbol=marker_symbols),
            text=marker_texts, textposition='top center', textfont=dict(size=9)
        ))

        # (2) 공급량 변화 (막대그래프)
        supply_fig.add_trace(go.Bar(
            x=year_data['월일'], y=year_data['공급량(M3)'],
            name=f"{year} 공급량(M3)",
            marker=dict(color=color_map.get(year), opacity=0.5),
            width=0.3
        ))

        # (3) 기온 vs 공급량 상관관계
        scatter_fig.add_trace(go.Scatter(
            x=year_data['평균기온'], y=year_data['공급량(M3)'],
            mode='markers+text',
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

st.write("### 필터링된 데이터")
st.dataframe(
    filtered_data[['날짜', '평균기온', '공급량(M3)', '공급량(MJ)', '요일', '공휴일']],
    height=600
)
