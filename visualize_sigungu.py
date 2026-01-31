"""
시군구 Shapefile 시각화 스크립트
- 입력 좌표계: EPSG:5186
- 시각화 좌표계: Lat/Lon (EPSG:4326)
- 단순화: 위상 보존 (Topology Preserving) - simplify_coverage
- 사용자 입력: 단순화 정도 (단위: km)
"""

import geopandas as gpd
import matplotlib.pyplot as plt
import os
import warnings

# 경고 메시지 억제
warnings.filterwarnings('ignore')

# 한글 폰트 설정
# Mac: AppleGothic, Windows: Malgun Gothic, Linux: NanumGothic 등 환경에 맞게 조정 필요
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

def visualize_sigungu():
    # 1. Shapefile 경로 및 설정
    shapefile_path = "./datasets/spatial/sigungu/BND_SIGUNGU_PG.shp"
    export_dir = "./export"
    
    if not os.path.exists(shapefile_path):
        print(f"Error: 파일이 존재하지 않습니다: {shapefile_path}")
        return

    # 2. Shapefile 로딩 (EPSG:5186 명시)
    print("Shapefile 로딩 중 (EPSG:5186)...")
    try:
        gdf = gpd.read_file(shapefile_path, encoding='cp949') # 한글 깨짐 방지용 encoding 확인 필요할 수 있음. 보통 'euc-kr' or 'cp949'
    except Exception as e:
        print(f"파일 로딩 실패: {e}")
        # geopandas 최신 버전은 encoding 자동 탐지하거나 기본 utf-8일 수 있음. 
        # 실패시 기본값으로 재시도
        gdf = gpd.read_file(shapefile_path)

    # 좌표계 설정 (누락된 경우)
    if gdf.crs is None:
        gdf.set_crs(epsg=5186, inplace=True)
    else:
        # 이미 좌표계가 있다면, 사용자가 명시한 5186과 일치하는지 확인하거나 신뢰
        # 여기서는 요구사항에 따라 5186으로 간주
        pass

    print(f"데이터 로드 완료: {len(gdf)}행")

    # ---------------------------------------------------------
    # 3. 작은 섬 제거 (Optional)
    # ---------------------------------------------------------
    try:
        min_area_input = input("\n제거할 작은 섬의 최소 면적을 km² 단위로 입력하세요 (기본값: 0, 엔터 시 생략): ").strip()
        if not min_area_input:
            min_area_sq_km = 0.0
        else:
            min_area_sq_km = float(min_area_input)
    except ValueError:
        print("잘못된 입력입니다. 제거하지 않습니다.")
        min_area_sq_km = 0.0

    if min_area_sq_km > 0:
        min_area_sq_m = min_area_sq_km * 1e6  # km² -> m²
        print(f"작은 섬 제거 중... (기준: {min_area_sq_km}km² = {min_area_sq_m:,.0f}m²)")
        
        # 1) Explode: MultiPolygon -> Polygon 분해
        gdf_exploded = gdf.explode(index_parts=False)
        original_parts = len(gdf_exploded)
        
        # 2) Filter: 면적 기준 제거
        gdf_filtered = gdf_exploded[gdf_exploded.geometry.area >= min_area_sq_m]
        filtered_parts = len(gdf_filtered)
        print(f"  - 전체 폴리곤 파트: {original_parts} -> {filtered_parts} (제거됨: {original_parts - filtered_parts}개)")
        
        # 3) Dissolve: SIGUNGU_CD 기준으로 다시 합치기
        #    속성 데이터 유지를 위해 aggregate 방식 지정 필요할 수 있으나, 
        #    여기서는 단순히 기하학적 결합과 첫 번째 행의 속성을 가져옴
        gdf = gdf_filtered.dissolve(by='SIGUNGU_CD', as_index=False)
        print(f"  - 재결합 완료: {len(gdf)}개 시군구")
    else:
        print("작은 섬 제거 단계를 건너뜁니다.")

    # ---------------------------------------------------------
    # 4. 사용자 입력 (Tolerance in km)
    # ---------------------------------------------------------
    try:
        user_input = input("\n단순화 정도를 km 단위로 입력하세요 (기본값: 1): ").strip()
        if not user_input:
            tolerance_km = 1.0
        else:
            tolerance_km = float(user_input)
    except ValueError:
        print("잘못된 입력입니다. 기본값 1km를 사용합니다.")
        tolerance_km = 1.0
    
    # km -> m 변환
    tolerance_m = tolerance_km * 1000.0
    print(f"단순화 정도: {tolerance_km}km ({tolerance_m}m)")

    # ---------------------------------------------------------
    # 5. 단순화 (Topology Preserving)
    # ---------------------------------------------------------
    # 5186 좌표계(미터 단위)에서 수행해야 정확함
    print("위상 보존 단순화(simplify_coverage) 수행 중...")
    
    gdf_simplified = gdf.copy()
    try:
        # GeoPandas 1.0+ / Shapely 2.1+ 기능
        gdf_simplified['geometry'] = gdf_simplified.geometry.simplify_coverage(tolerance=tolerance_m)
    except AttributeError:
        print("Warning: simplify_coverage를 지원하지 않는 버전입니다. 일반 simplify(preserve_topology=True)를 사용합니다.")
        gdf_simplified['geometry'] = gdf_simplified.geometry.simplify(tolerance_m, preserve_topology=True)

    # 5. 좌표계 변환 (EPSG:5186 -> EPSG:4326)
    print("좌표계 변환 (WGS84) 중...")
    gdf_wgs84 = gdf.to_crs(epsg=4326)
    gdf_simplified_wgs84 = gdf_simplified.to_crs(epsg=4326)

    # 6. 시각화
    print("시각화 생성 중...")
    fig, axes = plt.subplots(1, 2, figsize=(18, 10))

    # 원본 Plot
    gdf_wgs84.plot(ax=axes[0], edgecolor='black', linewidth=0.2, facecolor='lightblue')
    axes[0].set_title("원본 (Original)", fontsize=15)
    axes[0].set_aspect('equal')
    axes[0].grid(True, alpha=0.3, linestyle='--')

    # 단순화 Plot
    gdf_simplified_wgs84.plot(ax=axes[1], edgecolor='black', linewidth=0.2, facecolor='lightgreen')
    axes[1].set_title(f"단순화 (Simplified, Tolerance: {tolerance_km}km)", fontsize=15)
    axes[1].set_aspect('equal')
    axes[1].grid(True, alpha=0.3, linestyle='--')
    
    plt.suptitle(f"시군구 경계 시각화 비교 (Topology Preserved)", fontsize=20)
    plt.tight_layout()

    # 7. 저장
    if not os.path.exists(export_dir):
        os.makedirs(export_dir)
        print(f"폴더 생성: {export_dir}")
    
    output_filename = "sigungu_visualization.png"
    output_path = os.path.join(export_dir, output_filename)
    plt.savefig(output_path, dpi=150)
    print(f"\n이미지 저장 완료: {output_path}")

    # ---------------------------------------------------------
    # 8. GeoJSON 저장
    # ---------------------------------------------------------
    print("\nGeoJSON 저장 중...")
    
    # 저장 경로 설정
    geojson_export_dir = "./export/spatial/sigungu"
    if not os.path.exists(geojson_export_dir):
        os.makedirs(geojson_export_dir)
        print(f"폴더 생성: {geojson_export_dir}")
    
    # 파일명 생성 (BASE_DATE 기반)
    # 데이터에 BASEDATE 컬럼이 있다고 가정 (insturction 문서 참고)
    # 첫 번째 행의 날짜를 대표 날짜로 사용
    try:
        # 컬럼명이 'BASEDATE' 인지 'BASE_DATE' 인지 확인 필요 (로드 시 컬럼 출력했으므로 확인 가능)
        # instruction에는 'BASEDATE'라고 되어 있으나, 실제 로드 로그에는 'BASE_DATE'로 나올 수 있음.
        # 안전하게 컬럼 확인
        date_col = 'BASE_DATE' if 'BASE_DATE' in gdf.columns else 'BASEDATE'
        
        if date_col in gdf.columns:
            base_date = str(gdf[date_col].iloc[0])
            # 날짜 형식 정제 (예: 20240603)
            base_date = base_date.replace('-', '').replace('.', '')[:8]
        else:
            base_date = "unknown_date"
            print(f"Warning: 기준일자 컬럼({date_col})을 찾을 수 없습니다.")
            
    except Exception as e:
        base_date = "unknown_date"
        print(f"Warning: 날짜 정보 추출 실패 ({e})")

    geojson_filename = f"{base_date}_sigungu_simplified.json"
    geojson_path = os.path.join(geojson_export_dir, geojson_filename)

    # GeoJSON 저장 (UTF-8)
    try:
        gdf_simplified_wgs84.to_file(geojson_path, driver='GeoJSON', encoding='utf-8')
        print(f"GeoJSON 저장 완료: {geojson_path}")
    except Exception as e:
        print(f"GeoJSON 저장 실패: {e}")

if __name__ == "__main__":
    visualize_sigungu()
