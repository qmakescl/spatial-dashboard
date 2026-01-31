## 시군구 공간정보 구성
- ./datasets/spatial/sigungu/BND_SIGUNGU_PG.shp 파일을 읽어서 시각화하기
- 좌표계 : EPSG:5186
- dbf 파일의 구성은 다음과 같다.
  - BASEDATE : 데이터기준일자(2024년 6월 3일)
  - SIGUNGU_CD : 시군구코드
  - SIGUNGU_NM : 시군구명
- 시군구코드는 5자리로 구성되어 있으며, 앞의 2자리는 시도코드, 뒤의 3자리는 시군구코드를 의미한다.
- 시도코드, 시군구코드, 읍면동코드의 정보는 "./datasets/spatial/sigungu/센서스 공간정보 지역 코드.xlsx" 파일에 있다.
  - 기준시기 에따라 sheet 가 구성되어 있음 (2024년 6월의 경우 시트명이 "2024년 6월")

  
## 시각화 방법
- Python으로 시각화하는데 다음의 두가지 방식으로 시각화하고 저장해줘
- 시각화시 좌표계는 latlang 사용
- shapefile 의 정보를 그대로 읽어서 시각화
- 대한민국의 경우 해안선이 복잡하여 이를 단순화하여 시각화
  - 단순화시 인접한 polygon 이 서로 겹치거나 떨어지는 경우가 있는 이를 방지하는 방법 필요 (위상보존 단순화(Topology Preserving Simplification))
  - 단순화의 정도를 사용자에게 입력받아 조정할 수 있게 구성
- 단순화한 공간정보를 GeoJSON 파일로 저장
  - 경로는 ./export/spatial/sigungu 에 기준일자를 파일명으로 하여 저장
- 결과 이미지는 ./export 폴더에 저장


## 완료후 조치
- 생성한 코드의 중요 요소 설명
- 실행 방법 설명
- 코드 실행시 발생하는 문제점 및 해결방법 설명
- 이 사항을 "visualize_sigungu_shapefile.md" 파일에 기록