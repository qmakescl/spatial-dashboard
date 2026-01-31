import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Initialize Map using a dark theme tile layer (CartoDB Dark Matter)
const map = L.map('map').setView([36.5, 127.5], 7);

L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 20
}).addTo(map);

// Element references
const infoPanel = document.getElementById('region-details');

// State
let sidoMapping = {};

// Load Data
async function initDashboard() {
    try {
        // 1. Load Sido Mapping
        // Note: In development with Vite, we need to serve these files.
        // For now, assuming they are accessible via relative path if served from root or copied to public.
        // However, since the data is in ../export, we might need to adjust paths or move data to public.
        // For this prototype, let's try reading from the relative path assuming the dev server root is project root.
        // If not, we might need to copy files to dashboard/public.
        // Let's assume we run vite from dashboard/ directory. Then ../export is outside root.
        // Vite denies access to outside files by default unless configured.
        // STRATEGY: We will assume we copy the data to a 'public/data' folder inside dashboard for cleaner web serving.
        // BUT for now, let's try fetching from a path that we will setup.

        // Let's rely on the user or a script to move data. 
        // Or better, I will assume I can run the dev server from the project root?
        // If I run `vite` from project root, `dashboard/index.html` is at `/dashboard/index.html`.
        // Then `export/spatial/...` is at `/export/spatial/...`.

        const mappingResponse = await fetch('/data/sido_mapping.json');
        sidoMapping = await mappingResponse.json();

        // 2. Load GeoJSON
        // Use the specific file created earlier
        const geoResponse = await fetch('/data/20240630_sigungu_simplified.json');
        const geoData = await geoResponse.json();

        // 3. Render Layers
        renderGeoJson(geoData);

    } catch (error) {
        console.error('Failed to load data:', error);
        infoPanel.innerHTML = '<span style="color:red">Error loading data. Check console.</span>';
    }
}

function renderGeoJson(geoData) {
    L.geoJSON(geoData, {
        style: style,
        onEachFeature: onEachFeature
    }).addTo(map);
}

function style(feature) {
    return {
        fillColor: '#3388ff',
        weight: 1,
        opacity: 1,
        color: 'white',
        dashArray: '3',
        fillOpacity: 0.5
    };
}

function highlightFeature(e) {
    const layer = e.target;

    layer.setStyle({
        weight: 3,
        color: '#666',
        dashArray: '',
        fillOpacity: 0.7,
        fillColor: '#9f9eff'
    });

    layer.bringToFront();

    updateInfo(layer.feature.properties);
}

function resetHighlight(e) {
    const layer = e.target;
    // Reset style to default (simplified version of L.geoJSON resetStyle)
    layer.setStyle(style(layer.feature));

    // infoPanel.innerHTML = 'Hover over a region'; 
    // Keep the last info or reset? Let's reset for now.
}

function onEachFeature(feature, layer) {
    layer.on({
        mouseover: highlightFeature,
        mouseout: resetHighlight,
        click: zoomToFeature
    });
}

function zoomToFeature(e) {
    map.fitBounds(e.target.getBounds());
}

function updateInfo(props) {
    const sigunguCode = props.SIGUNGU_CD; // e.g. "11010"
    const sigunguName = props.SIGUNGU_NM; // e.g. "Jongno-gu"

    const sidoCode = sigunguCode.substring(0, 2); // "11"
    const sidoName = sidoMapping[sidoCode] || "Unknown Sido";

    infoPanel.innerHTML = `
    <div><strong>${sidoName}</strong></div>
    <div class="highlight" style="font-size: 1.5rem; margin-top: 5px;">${sigunguName}</div>
    <div style="font-size: 0.8rem; color: #888; margin-top: 5px;">Code: ${sigunguCode}</div>
  `;
}

initDashboard();
