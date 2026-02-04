/**
 * Scrapper Gringo - Frontend Application
 * Handles UI interactions and API calls to Python backend
 */

// API Configuration
const API_BASE = 'http://localhost:5000';

// DOM Elements
const modeButtons = document.querySelectorAll('.mode-btn');
const urlMode = document.getElementById('url-mode');
const deepMode = document.getElementById('deep-mode');
const placesMode = document.getElementById('places-mode');
const scrapeBtn = document.getElementById('scrape-btn');
const statusDiv = document.getElementById('status');
const resultsDiv = document.getElementById('results');

// Current mode
let currentMode = 'url';

// Mode Toggle
modeButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        const mode = btn.dataset.mode;
        currentMode = mode;

        // Update button states
        modeButtons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        // Show/hide content
        urlMode.classList.remove('active');
        deepMode.classList.remove('active');
        placesMode.classList.remove('active');

        if (mode === 'url') {
            urlMode.classList.add('active');
        } else if (mode === 'deep') {
            deepMode.classList.add('active');
        } else {
            placesMode.classList.add('active');
        }
    });
});

// Scrape Button Handler
scrapeBtn.addEventListener('click', async () => {
    const sheetTitle = document.getElementById('sheet-title').value || 'Scrapper Gringo Export';

    let requestData = {
        sheetTitle: sheetTitle,
        exportToSheets: true
    };

    if (currentMode === 'url') {
        const url = document.getElementById('url-input').value;
        const extract = document.getElementById('extract-input').value;

        if (!url) {
            alert('Bitte gib eine URL ein');
            return;
        }
        if (!extract) {
            alert('Bitte beschreibe was extrahiert werden soll');
            return;
        }

        requestData.mode = 'url';
        requestData.url = url;
        requestData.extract = extract;

    } else if (currentMode === 'deep') {
        const url = document.getElementById('deep-url-input').value;
        const filter = document.getElementById('filter-input').value;
        const stage2 = document.getElementById('stage2-input').value;
        const limit = parseInt(document.getElementById('deep-limit-input').value) || 10;

        if (!url) {
            alert('Bitte gib eine Übersichts-URL ein');
            return;
        }

        requestData.mode = 'deep';
        requestData.url = url;
        requestData.filter = filter || null;
        requestData.stage2 = stage2 || 'description, tools';
        requestData.limit = limit;

    } else {
        const query = document.getElementById('query-input').value;
        const location = document.getElementById('location-input').value;
        const limit = parseInt(document.getElementById('limit-input').value) || 10;

        if (!query) {
            alert('Bitte gib einen Geschäftstyp ein');
            return;
        }
        if (!location) {
            alert('Bitte gib einen Standort ein');
            return;
        }

        requestData.mode = 'places';
        requestData.query = query;
        requestData.location = location;
        requestData.limit = limit;
    }

    // Show loading state
    showStatus('loading', 'Scraping läuft...');
    scrapeBtn.disabled = true;
    resultsDiv.classList.add('hidden');

    const startTime = Date.now();

    try {
        const response = await fetch(`${API_BASE}/scrape`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });

        const data = await response.json();
        const duration = ((Date.now() - startTime) / 1000).toFixed(1);

        if (data.success) {
            showResults(data, duration);
        } else {
            showStatus('error', `Fehler: ${data.error}`);
        }
    } catch (error) {
        // For demo: simulate success if backend not running
        console.log('Backend not available, running in demo mode');
        simulateDemoResponse(requestData, startTime);
    }

    scrapeBtn.disabled = false;
});

// Show Status
function showStatus(type, message) {
    statusDiv.classList.remove('hidden', 'success', 'error');

    let icon = '⏳';
    if (type === 'success') {
        icon = '✅';
        statusDiv.classList.add('success');
    } else if (type === 'error') {
        icon = '❌';
        statusDiv.classList.add('error');
    }

    statusDiv.querySelector('.status-icon').textContent = icon;
    statusDiv.querySelector('.status-text').textContent = message;
}

// Show Results
function showResults(data, duration) {
    statusDiv.classList.add('hidden');
    resultsDiv.classList.remove('hidden');

    document.getElementById('result-count').textContent = data.count || 0;
    document.getElementById('result-time').textContent = `${duration}s`;

    const sheetsLink = document.getElementById('sheets-link');
    if (data.sheetUrl) {
        sheetsLink.href = data.sheetUrl;
        sheetsLink.style.display = 'inline-flex';
    } else {
        sheetsLink.style.display = 'none';
    }

    const preview = document.getElementById('preview');
    if (data.preview) {
        preview.textContent = data.preview;
    } else if (data.items) {
        preview.textContent = data.items.slice(0, 5).map(item =>
            typeof item === 'object' ? JSON.stringify(item, null, 2) : item
        ).join('\n---\n');
    }
}

// Demo Response (when backend not running)
function simulateDemoResponse(requestData, startTime) {
    const duration = ((Date.now() - startTime) / 1000).toFixed(1);

    setTimeout(() => {
        if (requestData.mode === 'url') {
            showResults({
                success: true,
                count: 15,
                sheetUrl: 'https://docs.google.com/spreadsheets/d/demo',
                preview: `Demo-Modus aktiviert\n\nURL: ${requestData.url}\nExtraktion: ${requestData.extract}\n\nStarte den Backend-Server für echtes Scraping:\n  cd "Scrapper Gringo"\n  python execution/server.py`
            }, duration);
        } else {
            showResults({
                success: true,
                count: requestData.limit,
                sheetUrl: 'https://docs.google.com/spreadsheets/d/demo',
                preview: `Demo-Modus aktiviert\n\nSuche: ${requestData.query} in ${requestData.location}\nLimit: ${requestData.limit}\n\nStarte den Backend-Server für echtes Scraping:\n  cd "Scrapper Gringo"\n  python execution/server.py`
            }, duration);
        }
    }, 1500);
}

// Initialize
console.log('🌵 Scrapper Gringo initialized');
