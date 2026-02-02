import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import * as XLSX from 'xlsx';

// ---------------------------------------------------------
// 1. Initialization & State
// ---------------------------------------------------------
const map = L.map('map').setView([36.0, 127.8], 7); // Center of Korea roughly

L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; OpenStreetMap &copy; CARTO',
    subdomains: 'abcd',
    maxZoom: 20
}).addTo(map);

let state = {
    mode: 'in', // 'in' (Inflow) or 'out' (Outflow)
    selectedRegion: null, // Census Code of the selected region (from GeoJSON)
    hoveredRegion: null,
};

let data = {
    geoJson: null,
    od: null,
    sidoMap: null,
    codeMap: null
};

let geoJsonLayer = null;

// DOM Elements
const modeInputs = document.querySelectorAll('input[name="flow-mode"]');
const modeDesc = document.getElementById('mode-desc');
const regionDetails = document.getElementById('region-details');
const legendContainer = document.getElementById('legend');

// ---------------------------------------------------------
// 2. Data Loading
// ---------------------------------------------------------
async function init() {
    try {
        const [geoRes, odRes, mapRes, codeMapRes] = await Promise.all([
            fetch('/sigungu.json'),
            fetch('/od_data.json'),
            fetch('/sido_mapping.json'),
            fetch('/code_mapping.json')
        ]);

        data.geoJson = await geoRes.json();
        data.od = await odRes.json();
        data.sidoMap = await mapRes.json();
        data.codeMap = await codeMapRes.json();

        preprocessRegionNames();

        renderMap();
        setupControls();
    } catch (e) {
        console.error("Failed to load data", e);
        alert("Data loading failed. See console.");
    }
}

// ---------------------------------------------------------
// 3. Map Rendering
// ---------------------------------------------------------
function renderMap() {
    if (geoJsonLayer) map.removeLayer(geoJsonLayer);

    geoJsonLayer = L.geoJSON(data.geoJson, {
        style: styleFeature,
        onEachFeature: onEachFeature
    }).addTo(map);
}

function getAdminCode(censusCode) {
    return data.codeMap && data.codeMap[censusCode] ? data.codeMap[censusCode] : censusCode;
}

function styleFeature(feature) {
    const regionCode = feature.properties.SIGUNGU_CD; // Census Code
    const adminCode = getAdminCode(regionCode);       // Admin Code
    const isSelected = state.selectedRegion === regionCode;

    // Default Style
    let style = {
        weight: 1,
        color: '#888', // Lighter border for light mode
        fillOpacity: 0.1,
        fillColor: '#fff'
    };

    // If a region is selected, color others based on flow
    if (state.selectedRegion) {
        if (isSelected) {
            // The selected region itself
            style.weight = 3;
            style.color = 'black';
            style.fillOpacity = 1.0;
            style.fillColor = '#f5da42'; // Yellow/Gold
        } else {
            // Connected regions
            const selectedAdminCode = getAdminCode(state.selectedRegion);
            const flowData = getFlowData(selectedAdminCode, adminCode);

            if (flowData && flowData.val > 0) {
                style.fillColor = getColor(flowData.val);
                style.fillOpacity = 0.7;
                style.weight = 1;
                style.color = '#555';
            } else {
                // Not connected regions -> White
                style.fillOpacity = 0.9;
                style.fillColor = '#ffffff';
                style.weight = 1;
                style.color = '#444'; // Same as default/connected border
            }
        }
    }

    return style;
}

function getFlowData(baseAdminCode, targetAdminCode) {
    if (!data.od[baseAdminCode]) return null;
    const directionData = data.od[baseAdminCode][state.mode]; // 'out' or 'in'
    if (!directionData) return null;
    return directionData[targetAdminCode]; // { val, diff } or undefined
}

function onEachFeature(feature, layer) {
    layer.on({
        click: (e) => {
            L.DomEvent.stopPropagation(e);
            selectRegion(feature.properties.SIGUNGU_CD);
        },
        mouseover: (e) => {
            highlightFeature(e.target);
            updateTooltip(e, feature.properties);
        },
        mouseout: (e) => {
            resetHighlight(e.target);
            layer.closeTooltip();
        }
    });

    // Bind Tooltip (Dynamic content updated on mouseover)
    layer.bindTooltip("", { sticky: true, className: 'custom-tooltip' });
}

// ---------------------------------------------------------
// 4. Interaction Logic
// ---------------------------------------------------------
function selectRegion(code) {
    if (state.selectedRegion === code) {
        state.selectedRegion = null; // Deselect
    } else {
        state.selectedRegion = code;
    }

    updateMapStyle();
    updateInfoPanel();
}

function updateMapStyle() {
    geoJsonLayer.setStyle(styleFeature);
    updateLegend();
}

function highlightFeature(layer) {
    if (state.selectedRegion === layer.feature.properties.SIGUNGU_CD) return;

    layer.setStyle({
        weight: 2,
        color: '#aaa'
    });
    layer.bringToFront();
}

function resetHighlight(layer) {
    geoJsonLayer.resetStyle(layer);
}

function updateTooltip(e, props) {
    const layer = e.target;
    const regionCode = props.SIGUNGU_CD; // Census
    const adminCode = getAdminCode(regionCode); // Admin

    const regionName = getFullRegionName(regionCode, props.SIGUNGU_NM);

    let content = `<div style="font-weight:bold">${regionName}</div>`;

    if (state.selectedRegion && state.selectedRegion !== regionCode) {
        const selectedAdminCode = getAdminCode(state.selectedRegion);
        const flow = getFlowData(selectedAdminCode, adminCode);

        if (flow) {
            const label = state.mode === 'in' ? '전입' : '전출';
            const diffSign = flow.diff > 0 ? '▲' : (flow.diff < 0 ? '▼' : '-');
            const diffColor = flow.diff > 0 ? 'red' : (flow.diff < 0 ? 'blue' : 'gray');

            const estNote = flow.est ? '<div style="color:#f59e0b; font-size:0.8em; margin-top:2px;">* 분구로 인한 변화량 추정</div>' : '';

            content += `
        <div>${label} 인구: ${flow.val.toLocaleString()}명</div>
        <div>${label} 세대: ${flow.hh_cnt.toLocaleString()}세대</div>
        <div style="font-size:0.8em; color:${diffColor}">
          전년대비: ${diffSign} ${Math.abs(flow.diff).toLocaleString()}
        </div>
        ${estNote}
      `;
        }
    }

    layer.setTooltipContent(content);
}

function getFullRegionName(code, name) {
    const sidoCode = code.substring(0, 2);
    const sidoName = data.sidoMap[sidoCode] || "";
    return `${sidoName} ${name}`;
}

function updateInfoPanel() {
    if (!state.selectedRegion) {
        regionDetails.innerHTML = '<div class="placeholder-text">지도에서 지역을 클릭하여<br>이동량을 확인하세요.</div>';
        document.getElementById('sidebar-table-container').classList.add('hidden');
        return;
    }

    // Find props for selected region (inefficient but safe)
    let props = null;
    geoJsonLayer.eachLayer(layer => {
        if (layer.feature.properties.SIGUNGU_CD === state.selectedRegion) {
            props = layer.feature.properties;
        }
    });

    if (!props) return;

    const adminCode = getAdminCode(state.selectedRegion);

    // Calculate Stats
    const totalIn = getTotalFlow(adminCode, 'in');
    const totalOut = getTotalFlow(adminCode, 'out');
    const netMigration = totalIn - totalOut;

    // Avg HH Size
    const totalFlow = state.mode === 'in' ? totalIn : totalOut;
    const totalHH = getTotalHH(adminCode, state.mode);
    const avgHHSize = totalHH > 0 ? (totalFlow / totalHH).toFixed(2) : '-';

    const regionName = getFullRegionName(state.selectedRegion, props.SIGUNGU_NM);
    const modeLabel = state.mode === 'in' ? '총 전입' : '총 전출';

    regionDetails.innerHTML = `
    <div style="margin-bottom:1rem">
      <div style="font-size:1.2rem; font-weight:bold">${regionName}</div>
      <div style="color:#666; font-size:0.9rem">행정동: ${adminCode}</div>
    </div>
    <div class="region-stat">
      <div class="stat-label">${modeLabel} 인구</div>
      <div class="stat-value">${totalFlow.toLocaleString()}명</div>
      <div style="font-size:0.9rem; color:#666">(${totalHH.toLocaleString()} 세대)</div>
    </div>
    <div class="region-stat">
      <div class="stat-label">순이동 (전입 - 전출)</div>
      <div class="stat-value ${netMigration > 0 ? 'diff-up' : (netMigration < 0 ? 'diff-down' : '')}">
        ${netMigration > 0 ? '+' : ''}${netMigration.toLocaleString()}명
      </div>
    </div>
    <div class="region-stat">
      <div class="stat-label">이동 세대 당 평균 인원</div>
      <div class="stat-value" style="font-size: 1.2rem; color: #374151;">${avgHHSize}명</div>
    </div>
  `;

    updateTable(adminCode);
}

function getTotalFlow(adminCode, mode) {
    if (!data.od[adminCode]) return 0;
    const flows = data.od[adminCode][mode];
    if (!flows) return 0;
    return Object.values(flows).reduce((acc, curr) => acc + curr.val, 0);
}

function getTotalHH(adminCode, mode) {
    if (!data.od[adminCode]) return 0;
    const flows = data.od[adminCode][mode];
    if (!flows) return 0;
    return Object.values(flows).reduce((acc, curr) => acc + curr.hh_cnt, 0);
}

// ---------------------------------------------------------
// Table & Export Logic
// ---------------------------------------------------------
let currentTableData = [];

function updateTable(adminCode) {
    const tableContainer = document.getElementById('sidebar-table-container');
    const tableBody = document.getElementById('stats-body');

    if (!data.od[adminCode] || !data.od[adminCode][state.mode]) {
        tableContainer.classList.add('hidden');
        return;
    }

    // Get flows
    const flows = data.od[adminCode][state.mode];
    const targetCodes = Object.keys(flows);

    // Map to array
    const rows = targetCodes.map(code => {
        return {
            code: code,
            name: getRegionNameByAdminCode(code),
            val: flows[code].val,
            hh_cnt: flows[code].hh_cnt,
            val: flows[code].val,
            hh_cnt: flows[code].hh_cnt,
            diff: flows[code].diff,
            est: flows[code].est
        };
    });

    // Sort by diff desc
    rows.sort((a, b) => b.diff - a.diff);

    // Top 20 & Bottom 20
    const top20 = rows.slice(0, 20);
    const bottom20 = rows.slice(-20); // allow overlap if total < 40

    // Combined for display
    let displayRows = [];
    if (rows.length <= 40) {
        displayRows = rows;
    } else {
        displayRows = [...top20, ...bottom20];
    }

    currentTableData = displayRows; // For export

    // Render (Simplified for Sidebar)
    tableBody.innerHTML = displayRows.map((r, i) => `
        <tr>
            <td>${i + 1}</td>
            <td>${r.name}</td>
            <td>${r.val.toLocaleString()}</td>
            <td style="color:${r.diff > 0 ? '#10b981' : (r.diff < 0 ? '#ef4444' : '#9ca3af')}">
                ${r.diff > 0 ? '+' : ''}${r.diff.toLocaleString()}
                ${r.est ? '<span style="color:#f59e0b; font-size:0.75em" title="분구로 인한 변화량 추정">*</span>' : ''}
            </td>
        </tr>
    `).join('');

    tableContainer.classList.remove('hidden');
}

// Helper to get name from Admin Code
let adminCodeToNameMap = {};
function preprocessRegionNames() {
    if (!data.geoJson) return;
    data.geoJson.features.forEach(f => {
        const cCode = f.properties.SIGUNGU_CD;
        const aCode = getAdminCode(cCode);
        const name = getFullRegionName(cCode, f.properties.SIGUNGU_NM);
        adminCodeToNameMap[aCode] = name;
    });
}

function getRegionNameByAdminCode(code) {
    return adminCodeToNameMap[code] || code;
}

function exportExcel() {
    if (!currentTableData || currentTableData.length === 0) return;

    const ws = XLSX.utils.json_to_sheet(currentTableData.map(r => ({
        "지역코드": r.code,
        "지역명": r.name,
        "인구수": r.val,
        "세대수": r.hh_cnt,
        "전년대비증감": r.diff
    })));

    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Data");
    XLSX.writeFile(wb, `od_data_export_${state.selectedRegion}.xlsx`);
}

document.getElementById('btn-export').addEventListener('click', exportExcel);

// ---------------------------------------------------------
// 5. Controls & Styling
// ---------------------------------------------------------
function setupControls() {
    modeInputs.forEach(input => {
        input.addEventListener('change', (e) => {
            state.mode = e.target.value;
            modeDesc.textContent = state.mode === 'in' ? "지역으로 들어오는 인구" : "지역에서 나가는 인구";
            updateMapStyle();
            updateInfoPanel();
        });
    });

    updateLegend();
}

// Color Scale
// Bins: 10, 50, 100, 500, 1000, 5000, 10000
const bins = [10, 50, 100, 500, 1000, 5000];
const colorsIn = ['#dbeafe', '#bfdbfe', '#93c5fd', '#60a5fa', '#3b82f6', '#2563eb', '#1d4ed8']; // Blueish
const colorsOut = ['#fee2e2', '#fecaca', '#fca5a5', '#f87171', '#ef4444', '#dc2626', '#b91c1c']; // Redish

function getColor(d) {
    const palette = state.mode === 'in' ? colorsIn : colorsOut;
    for (let i = 0; i < bins.length; i++) {
        if (d < bins[i]) return palette[i];
    }
    return palette[palette.length - 1]; // Max color
}

function updateLegend() {
    const palette = state.mode === 'in' ? colorsIn : colorsOut;
    let html = '';

    // 0 - 10
    html += createLegendItem(palette[0], `< ${bins[0]}`);

    for (let i = 0; i < bins.length - 1; i++) {
        html += createLegendItem(palette[i + 1], `${bins[i]} - ${bins[i + 1]}`);
    }

    html += createLegendItem(palette[palette.length - 1], `> ${bins[bins.length - 1]}`);

    legendContainer.innerHTML = html;
}

function createLegendItem(color, label) {
    return `
    <div class="legend-item">
      <div class="legend-color" style="background:${color}"></div>
      <span>${label}</span>
    </div>
  `;
}

// Start
init();
