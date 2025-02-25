import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.error("⚠️ 접근 권한이 없습니다. 메인 페이지에서 비밀번호 인증을 해주세요.")
    st.stop()

st.set_page_config(layout="wide")

st.title("일별 기온 및 공급량 분석 (주식차트 느낌 + 날짜/공급량 커스텀)")

@st.cache_data
def load_data():
    file_path = os.path.join("data", "weather_suply.xlsx")
    sheet_name = "일별기온공급량"
    df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')
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

filtered_data = data[(data['연'].isin(selected_years)) & (data['월'].isin(selected_months))]
filtered_data['월일'] = filtered_data['월'].astype(str) + '-' + filtered_data['일'].astype(str)

color_map = {2023: 'blue', 2024: 'deepskyblue', 2025: 'red'}

# 📊 서브플롯 생성 (위/아래)
fig = make_subplots(
    rows=2, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.1,
    subplot_titles=("공급량(M3) 변화", "평균기온(°C) 변화")
)

if not filtered_data.empty:
    for year in selected_years:
        year_data = filtered_data[filtered_data['연'] == year].copy()

        # 날짜표시 및 공급량 천단위 콤마 및 단위 적용
        year_data['날짜표시'] = year_data['월'].astype(str) + '월 ' + year_data['일'].astype(str) + '일'
        year_data['공급량표시'] = year_data['공급량(M3)'].apply(lambda x: f"{x:,.0f}㎥")

        # (1) 공급량 막대 그래프 (위쪽)
        fig.add_trace(go.Bar(
            x=year_data['월일'],
            y=year_data['공급량(M3)'],
            name=f"{year} 공급량(M3)",
            marker=dict(color=color_map.get(year), opacity=0.7),
            customdata=year_data[['연', '평균기온', '날짜표시', '공급량표시']].values,
            hovertemplate="<b>%{customdata[2]}</b><br>연도: %{customdata[0]}<br>평균기온: %{customdata[1]}°C<br>공급량: %{customdata[3]}<extra></extra>",
        ), row=1, col=1)

        # (2) 기온 꺾은선 그래프 (아래쪽)
        fig.add_trace(go.Scatter(
            x=year_data['월일'],
            y=year_data['평균기온'],
            mode='lines+markers',
            name=f"{year} 평균기온",
            line=dict(color=color_map.get(year), width=2),
            customdata=year_data[['연', '공급량표시', '날짜표시']].values,
            hovertemplate="<b>%{customdata[2]}</b><br>연도: %{customdata[0]}<br>평균기온: %{y}°C<br>공급량: %{customdata[1]}<extra></extra>",
        ), row=2, col=1)

fig.update_layout(
    title="일별 평균기온 & 공급량(M3) 위아래 분리 그래프 (주식차트 호버 + 날짜/공급량 포맷 변경)",
    height=800,
    showlegend=True,
    hovermode='x unified',  # x축 따라다니는 호버
)

fig.update_yaxes(title_text="공급량(M3)", row=1, col=1)
fig.update_yaxes(title_text="평균기온(°C)", row=2, col=1)

fig.update_xaxes(
    showgrid=True,
    gridcolor="lightgray",
    gridwidth=1,
    tickmode="array",
    tickvals=filtered_data['월일'].unique(),
    row=1, col=1
)

fig.update_xaxes(
    showgrid=True,
    gridcolor="lightgray",
    gridwidth=1,
    tickmode="array",
    tickvals=filtered_data['월일'].unique(),
    row=2, col=1
)

st.plotly_chart(fig, use_container_width=True)

st.write("### 필터링된 데이터")
st.dataframe(
    filtered_data[['날짜', '평균기온', '공급량(M3)', '공급량(MJ)']],
    height=400
)
