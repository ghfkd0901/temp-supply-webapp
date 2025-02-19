import os
import streamlit as st
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.tree import DecisionTreeRegressor
from sklearn.neighbors import KNeighborsRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline
from datetime import datetime, timedelta

if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.error("⚠️ 접근 권한이 없습니다. 메인 페이지에서 비밀번호 인증을 해주세요.")
    st.stop()
    
st.set_page_config(layout="wide")
st.title("일별 공급량 예측")

@st.cache_data
def load_data():
    file_path = os.path.join(os.path.dirname(__file__), 'data', 'weather_supply.xlsx')
    sheet_name = "일별기온공급량"
    df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')
    df['연'] = df['날짜'].dt.year
    df['월'] = df['날짜'].dt.month
    df['요일'] = df['날짜'].dt.day_name(locale='ko_KR')
    return df[['날짜', '평균기온', '공급량(M3)', '공급량(MJ)', '연', '월', '요일']]

data = load_data()

selected_models = st.sidebar.multiselect(
    "모델 선택",
    ["다항회귀", "랜덤포레스트", "KNN", "결정트리", "그레디언트부스팅"],
    default=["다항회귀", "랜덤포레스트", "KNN", "결정트리", "그레디언트부스팅"]
)

st.sidebar.title("📚 학습 데이터 설정")
selected_years = st.sidebar.multiselect("학습 연도 선택", sorted(data['연'].unique()), default=sorted(data['연'].unique())[-3:])
selected_months = st.sidebar.multiselect("학습 월 선택", list(range(1, 13)), default=list(range(1, 13)))
selected_days = st.sidebar.multiselect("학습 요일 선택", data['요일'].unique(), default=data['요일'].unique())

train_data = data[
    (data['연'].isin(selected_years)) &
    (data['월'].isin(selected_months)) &
    (data['요일'].isin(selected_days))
].dropna(subset=['평균기온', '공급량(M3)', '공급량(MJ)'])

if 'trained_models' not in st.session_state or st.sidebar.button("모델 다시 학습하기"):
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

    st.session_state["trained_models"] = trained_models
    st.session_state["training_info"] = f"학습 데이터 연도: {', '.join(map(str, selected_years))}, 월: {selected_months}, 요일: {selected_days}"
    st.success("✅ 모델 학습 완료")

st.sidebar.title("🗓 예측 기간 설정")
today = datetime.today()
start_date = st.sidebar.date_input("시작일", today)
end_date = st.sidebar.date_input("종료일", datetime(today.year, today.month + 1, 1) - timedelta(days=1))

date_range = pd.date_range(start=start_date, end=end_date)
default_df = pd.DataFrame({'날짜': date_range, '평균기온': None})

st.write("### 평균기온 입력")
edited_df = st.data_editor(
    default_df,
    num_rows="dynamic",
    column_config={
        "평균기온": st.column_config.NumberColumn(format="%.1f")
    }
)

if st.button("예측하기"):
    if edited_df['평균기온'].isnull().any():
        st.error("❌ 모든 날짜의 평균기온을 입력해주세요.")
    else:
        X_pred = edited_df[['평균기온']]

        result_with_preds = edited_df.copy()

        for model_name in selected_models:
            model_m3 = st.session_state["trained_models"][model_name + "_m3"]
            model_mj = st.session_state["trained_models"][model_name + "_mj"]

            result_with_preds[model_name + '_M3'] = model_m3.predict(X_pred).astype(int)
            result_with_preds[model_name + '_MJ'] = model_mj.predict(X_pred).astype(int)

        result_with_preds['날짜'] = result_with_preds['날짜'].dt.strftime('%Y-%m-%d')

        st.session_state["result_with_preds"] = result_with_preds

if "result_with_preds" in st.session_state:
    result_df_m3 = st.session_state["result_with_preds"][['날짜', '평균기온'] + [f"{model}_M3" for model in selected_models]]
    result_df_mj = st.session_state["result_with_preds"][['날짜', '평균기온'] + [f"{model}_MJ" for model in selected_models]]

    result_df_m3.columns = ['날짜', '평균기온'] + selected_models
    result_df_mj.columns = ['날짜', '평균기온'] + selected_models

    st.write("### 예측 결과 - 부피 (M3)")
    st.dataframe(result_df_m3)

    st.write("### 예측 결과 - 열량 (MJ)")
    st.dataframe(result_df_mj)

st.markdown(f"**🔍 현재 학습 데이터 설정:** {st.session_state.get('training_info', '아직 학습 안됨')}")




# st.markdown("""
# ## 📝 모델 설명 (공급량 예측)
# - 특성: 평균기온
# - 목표: 공급량(M3), 공급량(MJ)
# - 사용 모델: 3차 다항회귀, 랜덤포레스트, KNN, 결정트리, 그레디언트부스팅
# - 학습 데이터는 사용자가 설정한 기간에 따라 다름.
# - 결측치는 제거하고 학습함.
# """)








# st.markdown("""
# ## 📄 모델 설명 (공급량 예측)

# ### 1️⃣ 모델 목적
# 공급량 예측 모델은 **평균기온**을 기반으로 **일별 공급량(M3, MJ)**을 예측하기 위해 만들어졌습니다.  
# 사용자가 특정 기간의 **평균기온**을 입력하면, 해당 기간의 **공급량(M3: 부피)**와 **공급량(MJ: 열량)**을 예측합니다.

# ### 2️⃣ 모델 특성(입력 변수)
# | 변수명   | 설명                                  |
# |---------|-------------------------------------|
# | 평균기온 | 해당 날짜의 평균기온 (°C)              |

# ### 3️⃣ 모델 타깃(출력 변수)
# | 변수명         | 설명                                           |
# |----------------|----------------------------------------------|
# | 공급량(M3)     | 해당 날짜의 공급량 (부피, m³ 단위)               |
# | 공급량(MJ)     | 해당 날짜의 공급량 (열량, MJ 단위)               |

# ### 4️⃣ 사용한 모델 종류
# | 모델명          | 설명                                                                      |
# |-----------------|--------------------------------------------------------------------------|
# | 3차 다항회귀 (Polynomial Regression) | 평균기온과 공급량 사이의 **비선형적 관계**를 반영하기 위해 3차항까지 사용한 회귀 모델입니다. |
# | 랜덤포레스트 (Random Forest)         | 여러 개의 결정트리를 조합하여 예측 성능을 높이는 **앙상블 학습 모델**입니다. |
# | KNN (K-Nearest Neighbors)            | 평균기온이 비슷한 과거 데이터(가장 가까운 이웃)를 참고하여 공급량을 예측하는 모델입니다. |
# | 결정트리 (Decision Tree)             | 데이터를 분할하여 의사결정 과정을 모형화하여 공급량을 예측하는 트리 기반 모델입니다. |
# | 그레디언트 부스팅 (Gradient Boosting) | 여러 개의 약한 모델(결정트리)을 순차적으로 학습시켜 오차를 줄여나가는 강력한 예측 모델입니다. |

# ### 5️⃣ 학습 데이터 기간
# - **2013년부터 최근 데이터까지 전 기간** 사용하여 학습했습니다.

# ### 6️⃣ 결측치 처리 방법
# - **평균기온, 공급량(M3), 공급량(MJ)** 중 **결측치(NaN)**가 있는 경우 **해당 행을 삭제**하고 모델을 학습했습니다.

# ### 7️⃣ 모델 저장
# - 훈련한 모델은 **피클 파일(.pkl)**로 저장되어, 이후 다시 실행할 때 빠르게 불러와 사용할 수 있습니다.
#   - supply_model_poly3.pkl
#   - supply_model_랜덤포레스트.pkl
#   - supply_model_KNN.pkl
#   - supply_model_결정트리.pkl
#   - supply_model_그레디언트부스팅.pkl
# """)

