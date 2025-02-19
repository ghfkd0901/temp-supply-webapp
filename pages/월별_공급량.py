import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.error("⚠️ 접근 권한이 없습니다. 메인 페이지에서 비밀번호 인증을 해주세요.")
    st.stop()
    
st.title("월별 공급량 및 기온 분석")
st.markdown("데이터 출처: [기상자료개방포털](https://data.kma.go.kr/climate/RankState/selectRankStatisticsDivisionList.do?pgmNo=179)")

@st.cache_data
def load_data():
    file_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'weather_supply.xlsx')
    sheet_name = "일별기온공급량"
    df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')
    df = df[['날짜', '평균기온', '연', '월', '공급량(M3)', '공급량(MJ)']]
    df['연'] = df['연'].astype(int)
    df['월'] = df['월'].astype(int)
    return df

data = load_data()

# 연도 선택 필터
default_years = [2020, 2021, 2022, 2023, 2024, 2025]
selected_years = st.multiselect("연도 선택", sorted(data['연'].unique()), default=default_years)

# 월 선택 필터
months = sorted(data['월'].unique())
selected_month = st.selectbox("월 선택", months, index=months.index(2))

# 필터링 적용
filtered_data = data[
    (data['연'].isin(selected_years)) & (data['월'] == selected_month)
]

# 월별 데이터 집계 (피벗테이블 유사 형태)
monthly_summary = filtered_data.groupby(['연', '월']).agg(
    평균기온=('평균기온', 'mean'),
    공급량_M3=('공급량(M3)', 'sum')
).reset_index()

# 그래프 그리기 (엑셀처럼 막대+선 그래프)
fig = go.Figure()

# 막대그래프: 공급량(M3)
fig.add_trace(go.Bar(
    x=monthly_summary['연'].astype(str),
    y=monthly_summary['공급량_M3'],
    name='공급량(M3)',
    yaxis='y1',
    marker_color='orange'
))

# 선그래프: 평균기온
fig.add_trace(go.Scatter(
    x=monthly_summary['연'].astype(str),
    y=monthly_summary['평균기온'],
    name='평균기온',
    yaxis='y2',
    mode='lines+markers',
    marker=dict(color='blue')
))

# 레이아웃 설정 (이중 축)
fig.update_layout(
    title=f"{selected_month}월 연도별 공급량 및 평균기온",
    xaxis_title='연도',
    yaxis=dict(
        title='공급량(M3)',
        side='left'
    ),
    yaxis2=dict(
        title='평균기온(℃)',
        side='right',
        overlaying='y',
        showgrid=False
    ),
    barmode='group'
)

st.plotly_chart(fig)

# 표 형태로 요약 결과 출력
st.write(f"### {selected_month}월 연도별 공급량 및 평균기온 데이터")
st.dataframe(monthly_summary)
