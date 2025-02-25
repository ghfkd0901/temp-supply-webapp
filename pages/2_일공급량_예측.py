import os
import streamlit as st
from pathlib import Path
import pandas as pd
import holidays
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.tree import DecisionTreeRegressor
from sklearn.neighbors import KNeighborsRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline
from datetime import datetime, timedelta

st.set_page_config(layout="wide")
st.title("일별 공급량 예측")

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

# ✅ 2️⃣ 모델 학습 및 저장 함수
def train_models():
    """선택된 모델 학습 및 저장"""
    selected_years = st.session_state.get("selected_years", sorted(data['연'].unique()))
    selected_months = st.session_state.get("selected_months", list(range(1, 13)))
    selected_days = st.session_state.get("selected_days", data['요일'].unique())

    train_data = data[
        (data['연'].isin(selected_years)) &
        (data['월'].isin(selected_months)) &
        (data['요일'].isin(selected_days))
    ].dropna(subset=['평균기온', '공급량(M3)', '공급량(MJ)'])

    X_train = train_data[['평균기온']]
    y_train_m3 = train_data['공급량(M3)']
    y_train_mj = train_data['공급량(MJ)']

    models = {
        "다항회귀": lambda: make_pipeline(PolynomialFeatures(3), LinearRegression()),
        "랜덤포레스트": lambda: RandomForestRegressor(random_state=42),
        "KNN": lambda: KNeighborsRegressor(),
        "결정트리": lambda: DecisionTreeRegressor(random_state=42),
        "그레디언트부스팅": lambda: GradientBoostingRegressor(random_state=42)
    }

    trained_models = {}
    for name, model_fn in models.items():
        trained_models[name + "_m3"] = model_fn().fit(X_train, y_train_m3)
        trained_models[name + "_mj"] = model_fn().fit(X_train, y_train_mj)

    return trained_models

# ✅ 3️⃣ UI - 사이드바 설정
st.sidebar.title("📚 학습 데이터 설정")
selected_years = st.sidebar.multiselect("학습 연도 선택", sorted(data['연'].unique()), default=sorted(data['연'].unique())[-3:])
selected_months = st.sidebar.multiselect("학습 월 선택", list(range(1, 13)), default=list(range(1, 13)))
selected_days = st.sidebar.multiselect("학습 요일 선택", data['요일'].unique(), default=data['요일'].unique())

st.sidebar.title("📅 예측 기간 설정")
today = datetime.today()
start_date = st.sidebar.date_input("시작일", today)
end_date = st.sidebar.date_input("종료일", datetime(today.year, today.month + 1, 1) - timedelta(days=1))

if start_date > end_date:
    st.sidebar.error("시작일은 종료일보다 이전이어야 합니다.")

# ✅ 4️⃣ 모델 선택
selected_models = st.sidebar.multiselect(
    "모델 선택",
    ["다항회귀", "랜덤포레스트", "KNN", "결정트리", "그레디언트부스팅"],
    default=["다항회귀", "랜덤포레스트", "KNN", "결정트리", "그레디언트부스팅"]
)

# ✅ 5️⃣ 세션 상태 관리 및 모델 학습
if "trained_models" not in st.session_state or \
   st.session_state.get("selected_years") != selected_years or \
   st.session_state.get("selected_months") != selected_months or \
   st.session_state.get("selected_days") != selected_days or \
   st.sidebar.button("모델 다시 학습하기"):
    
    st.session_state["selected_years"] = selected_years
    st.session_state["selected_months"] = selected_months
    st.session_state["selected_days"] = selected_days
    st.session_state["trained_models"] = train_models()
    st.session_state["training_info"] = f"학습 데이터 연도: {', '.join(map(str, selected_years))}, 월: {selected_months}, 요일: {selected_days}"
    st.success("✅ 모델 학습 완료")

# ✅ 6️⃣ 사용자 입력 데이터 생성 (예측 기간에 따라 갱신)
def update_pred_df(start_date, end_date):
    date_range = pd.date_range(start=start_date, end=end_date)
    new_df = pd.DataFrame({'날짜': date_range, '평균기온': None})
    return new_df

if "pred_df" not in st.session_state or \
   st.session_state["pred_df"]['날짜'].min().date() != start_date or \
   st.session_state["pred_df"]['날짜'].max().date() != end_date:
    st.session_state["pred_df"] = update_pred_df(start_date, end_date)

# ✅ 7️⃣ UI - 평균기온 입력
st.write("### 평균기온 입력")
edited_df = st.data_editor(
    st.session_state["pred_df"],
    num_rows="dynamic",
    column_config={
        "평균기온": st.column_config.NumberColumn(format="%.1f")
    },
    key="temperature_editor"
)

# ✅ 8️⃣ 예측 수행
if st.button("예측하기"):
    st.session_state["pred_df"].update(edited_df)

    if st.session_state["pred_df"]['평균기온'].isnull().any():
        st.error("❌ 모든 날짜의 평균기온을 입력해주세요.")
    else:
        X_pred = st.session_state["pred_df"][['평균기온']]

        result_df = st.session_state["pred_df"].copy()
        result_df['날짜'] = result_df['날짜'].dt.strftime('%Y-%m-%d')

        for model_name in selected_models:
            model_m3 = st.session_state["trained_models"][model_name + "_m3"]
            model_mj = st.session_state["trained_models"][model_name + "_mj"]

            result_df[model_name + '_M3'] = model_m3.predict(X_pred).astype(int)
            result_df[model_name + '_MJ'] = model_mj.predict(X_pred).astype(int)

        # 예측 결과 데이터프레임에 필요한 열들만 포함
        result_df_m3 = result_df[['날짜', '평균기온'] + [f"{model}_M3" for model in selected_models]]
        result_df_mj = result_df[['날짜', '평균기온'] + [f"{model}_MJ" for model in selected_models]]

        result_df_m3.columns = ['날짜', '평균기온'] + selected_models
        result_df_mj.columns = ['날짜', '평균기온'] + selected_models

        st.session_state["result_df_m3"] = result_df_m3
        st.session_state["result_df_mj"] = result_df_mj

# ✅ 9️⃣ 예측 결과 출력
if "result_df_m3" in st.session_state and "result_df_mj" in st.session_state:
    st.write("### 예측 결과 - 부피 (M3)")
    st.dataframe(st.session_state["result_df_m3"])

    st.write("### 예측 결과 - 열량 (MJ)")
    st.dataframe(st.session_state["result_df_mj"])

st.markdown(f"**🔍 현재 학습 데이터 설정:** {st.session_state.get('training_info', '아직 학습 안됨')}")