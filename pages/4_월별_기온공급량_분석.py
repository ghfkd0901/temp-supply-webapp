import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.subplots as sp

if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.error("⚠️ 접근 권한이 없습니다. 메인 페이지에서 비밀번호 인증을 해주세요.")
    st.stop()
    
st.title("월별 공급량 및 기온 분석")

@st.cache_data
def load_data():
    file_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'weather_supply.xlsx')
    sheet_name = "일별기온공급량"
    df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')
    df = df[['날짜', '평균기온', '연', '월', '일', '공급량(M3)', '공급량(MJ)', '공휴일']]
    df['연'] = df['연'].astype(int)
    df['월'] = df['월'].astype(int)
    return df

data = load_data()

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
