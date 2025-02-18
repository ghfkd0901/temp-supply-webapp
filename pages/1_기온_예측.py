import streamlit as st
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
import pickle
from datetime import datetime, timedelta

if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.error("⚠️ 접근 권한이 없습니다. 메인 페이지에서 비밀번호 인증을 해주세요.")
    st.stop()

st.set_page_config(layout="wide")
st.title("일별 기온 예측")


@st.cache_data
def load_data():
    file_path = r"data\날씨공급량.xlsx"
    sheet_name = "일별기온공급량"
    df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')
    return df[['날짜', '최고기온', '최저기온', '평균기온']]

data = load_data()

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



st.markdown("""     
## 📄 모델 설명 (기온 예측)

### 1️⃣ 모델 목적
기온 예측 모델은 **최고기온과 최저기온**을 기반으로 **평균기온**을 예측하기 위해 만들어졌습니다.  
사용자가 특정 기간 동안 최고기온과 최저기온을 입력하면, 해당 기간의 **평균기온을 예측**해줍니다.

### 2️⃣ 모델 특성(입력 변수)
| 변수명   | 설명                                  |
|---------|-------------------------------------|
| 최고기온 | 해당 날짜의 최고기온 (°C)              |
| 최저기온 | 해당 날짜의 최저기온 (°C)              |

### 3️⃣ 모델 타깃(출력 변수)
| 변수명   | 설명                                  |
|---------|-------------------------------------|
| 평균기온 | 해당 날짜의 평균기온 (°C)              |

### 4️⃣ 사용한 모델 종류
| 모델명          | 설명                                                                      |
|-----------------|--------------------------------------------------------------------------|
| 선형회귀 (Linear Regression) | 최고기온과 최저기온이 평균기온에 **직선 관계**가 있다고 가정하는 단순한 모델입니다. |
| 랜덤포레스트 (Random Forest) | 여러 개의 결정트리를 조합하여 예측 성능을 높이는 **앙상블 학습 모델**입니다. |

### 5️⃣ 학습 데이터 기간
- **2013년부터 최근 데이터까지 전 기간** 사용하여 학습했습니다.

### 6️⃣ 결측치 처리 방법
- **최고기온, 최저기온, 평균기온 중 결측치(NaN)**가 있는 경우 **해당 행을 삭제**하고 모델을 학습했습니다.

### 7️⃣ 모델 저장
- 훈련한 모델은 **피클 파일(.pkl)**로 저장되어, 이후 다시 실행할 때 빠르게 불러와 사용할 수 있습니다.
  - temp_model_linear.pkl    (선형회귀)
  - temp_model_rf.pkl        (랜덤포레스트)
""")

