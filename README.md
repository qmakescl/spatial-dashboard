
# Spatial Dashboard: 시군구별 세대이동 시각화

이 프로젝트는 대한민국 시군구 데이터를 기반으로 **2024년 인구(세대) 이동** 흐름을 인터랙티브하게 탐색할 수 있는 웹 대시보드입니다.

## 🚀 주요 기능
*   **OD (Origin-Destination) 시각화**: 특정 시군구를 선택하면 해당 지역으로의 **전입(Inflow)** 및 타 지역으로의 **전출(Outflow)** 현황을 지도에 시각화합니다.
*   **지역별 심층 지표 (Deep Analysis)**:
    *   **순이동 (Net Migration)**: 전입-전출 차이를 계산하여 실질적인 인구 증감을 표시합니다.
    *   **세대당 평균 인원**: 이동 세대수 대비 인구수를 분석하여 가구 특성을 제공합니다.
*   **Top/Bottom 20 분석**:
    *   선택된 지역 기준으로 이동량이 가장 많은/적은 상위 20개 지역 리스트를 제공합니다.
    *   **Excel 내보내기**: 분석된 테이블 데이터를 `.xlsx` 파일로 다운로드할 수 있습니다.
*   **변화 추이 (YoY)**: 2023년 데이터와 비교하여 전년 대비 이동량의 증감(▲/▼)을 제공합니다.

---

## 🛠️ 설치 및 실행 (Installation & Usage)

### 1. 필수 요구사항 (Prerequisites)
*   **Python**: 3.10 이상 (데이터 전처리용)
*   **Node.js**: 18 이상 (웹 대시보드 실행용)
*   **uv** (Python 패키지 매니저, 권장)

### 2. 프로젝트 설정 (Setup)

#### Repository 준비
```bash
git clone <repository-url>
cd spatial_dashboard
```

#### Python 환경 설정 (데이터 처리용)
```bash
# uv를 사용하는 경우
uv sync

# 또는 pip 사용 시
pip install pandas openpyxl
```

### 3. 데이터 준비 및 처리 (Data Processing)

이 프로젝트는 대용량 통계 데이터(CSV)를 웹 최적화된 JSON 파일로 변환하여 사용합니다.

1.  **데이터 다운로드**
    * (센서스경계)시군구경계 : [브이월드 공간정보 다운로드](https://www.vworld.kr/dtmk/dtmk_ntads_s002.do?searchKeyword=%EC%84%BC%EC%84%9C%EC%8A%A4&searchSvcCde=&searchOrganization=&searchBrmCode=&searchTagList=&searchFrm=&pageIndex=1&gidmCd=&gidsCd=&sortType=00&svcCde=MK&dsId=30015&listPageIndex=1))
    * 인구이동데이터셋 - 세대관련 년간자료 : [데이터처 마이크로데이터 통합서비스](https://mdis.mods.go.kr/ofrData/selectOfrDataDetail.do?survId=23&itmDiv=1&nPage=3&itemId=2001&itemNm=%EC%9D%B8%EA%B5%AC)

2.  **데이터 위치**
    * `datasets/popMove/houseHold/` 경로에 2023년, 2024년의 세대별 인구이동 데이터의 이름을 각각 `2023.csv`, `2024.csv`으로 변경하여 저장합니다.
    * `datasets/spatial/sigungu/` 경로에 시군구 공간정보 파일을 저장합니다.
  
3.  **전처리 스크립트 실행**:
    ```bash
    # 다음 명령어를 실행하여 dashboard/public/od_data.json 파일을 생성합니다.
    uv run python process_od_data.py
    ```
    > **결과**: `dashboard/public/od_data.json` (약 3MB) 생성 완료

4.  **Top/Bottom 20 분석 테이블**:
    *   사이드바의 "Selected Region" 패널 하단에 자동으로 등락폭 상위/하위 20개 지역이 표시됩니다.
    *   `Excel 다운로드` 버튼을 통해 데이터를 저장할 수 있습니다.

### 4. 대시보드 실행 (Running Dashboard)

웹 대시보드는 Vite + Leaflet 기반으로 동작합니다.

```bash
# dashboard 디렉토리로 이동
cd dashboard

# 의존성 설치 (xlsx 라이브러리 포함)
npm install

# 개발 서버 실행
npm run dev
```

브라우저에서 `http://localhost:5173` 접속 시 대시보드를 확인할 수 있습니다.

---

## 📂 데이터 출처 (Data Sources)

1.  **공간정보 (Maps)**
    *   출처: [V-World (브이월드)](https://www.vworld.kr/) 국가공간정보포털
    *   데이터: 시군구 경계 (Shapefile → GeoJSON 변환 사용)

2.  **통계데이터 (Statistics)**
    *   출처: 통계청 MDIS (마이크로데이터 통합서비스) - 국내인구이동통계
    *   기간: 2023년 1월 ~ 2024년 12월

---

> This content was written by Google Antigravity under the guidance of Q.
