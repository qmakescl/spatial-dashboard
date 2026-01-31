# South Korea Sigungu Spatial Dashboard

대한민국 시군구 경계 데이터를 시각화하고, 웹 기반 대시보드에서 지역 정보를 탐색할 수 있는 프로젝트입니다.

## 1. 데이터 입수 (Data Acquisition)

본 프로젝트는 [V-World (브이월드)](https://www.vworld.kr/)의 공개 공간정보를 활용하였습니다.
*   **데이터셋**: (센서스경계) 시군구경계
*   **다운로드 링크**: [https://www.vworld.kr/dtmk/dtmk_ntads_s002.do?svcCde=MK&dsId=30015](https://www.vworld.kr/dtmk/dtmk_ntads_s002.do?svcCde=MK&dsId=30015)
*   **참고**: 원본 Shapefile 데이터는 `datasets/` 폴더에 저장되지만, 라이선스 및 용량 문제와 로그인이 필요한 다운로드 특성상 git 저장소에는 포함되지 않습니다.

## 2. 처리 과정 (Processing)

원본 데이터를 웹에서 효율적으로 시각화하기 위해 다음의 처리 과정을 거쳤습니다.

1.  **데이터 로드**: `EPSG:5186` 좌표계의 Shapefile 로드 (`datasets/spatial/sigungu/`)
2.  **단순화 (Simplification)**: `simplify_coverage`를 사용하여 인접 구역 간의 위상(Topology)을 보존하며 경계선을 단순화했습니다.
3.  **데이터 매핑**: `센서스 공간정보 지역 코드.xlsx`를 분석하여 시군구 코드와 시도명(예: 강원특별자치도)을 매핑, `sido_mapping.json`을 생성했습니다.
4.  **변환 및 저장**: 최종 결과물을 `EPSG:4326`(위경도) 좌표계의 GeoJSON으로 변환하여 대시보드에서 사용합니다.

## 3. 대시보드 이용 (Dashboard Usage)

Vite와 Leaflet.js를 사용한 경량 웹 대시보드를 제공합니다.

### 실행 방법
```bash
# 1. 대시보드 디렉토리로 이동
cd dashboard

# 2. 의존성 패키지 설치
npm install

# 3. 개발 서버 실행
npm run dev
```

### 기능
*   브라우저에서 `http://localhost:5173` 접속
*   지도 상의 시군구 영역에 마우스 오버 시 **"시도 + 시군구"** (예: 서울특별시 종로구, 강원특별자치도 춘천시) 정보 표시

---

> 이 내용은 Q의 지침하에 Google Antigravity가 작성함.
> This content was written by Google Antigravity under the guidance of Q.
