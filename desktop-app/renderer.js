const { ipcRenderer } = require('electron');

const elConnectionStatus = document.getElementById('connection-status');
const elServerUrl = document.getElementById('server-url');
const elClock = document.getElementById('clock');
const elMinimizeBtn = document.getElementById('minimize-btn');
const elAlertList = document.getElementById('alert-list');

// Clock
function updateClock() {
    const now = new Date();
    elClock.textContent = now.toLocaleTimeString();
}
setInterval(updateClock, 1000);
updateClock();

// UI Actions
elMinimizeBtn.addEventListener('click', () => {
    // Send minimize request to main process
    // Actually typically 'Run in Background' might mean hide to tray
    ipcRenderer.send('window-action', 'hide');
});

// IPC Listeners (From Main)
ipcRenderer.on('ws-status', (event, status) => {
    console.log('WS Status:', status); // connected, disconnected, error
    if (status.state === 'connected') {
        elConnectionStatus.classList.remove('disconnected');
        elConnectionStatus.classList.add('connected');
        elServerUrl.textContent = status.url;
    } else {
        elConnectionStatus.classList.remove('connected');
        elConnectionStatus.classList.add('disconnected');
        elServerUrl.textContent = '연결 끊김'; // Translated
    }
});

ipcRenderer.on('ws-data', (event, data) => {
    // Expecting data object
    console.log('Data received:', data);
    updateMarketData(data);
});

function updateMarketData(data) {
    if (data.type === 'ticker') {
        // Find existing ticker element or create one?
        // For now, let's keep it specific to the UI elements in index.html but be more flexible
        const elementIdMap = {
            '005930': 'market-samsung',
            'TSLA': 'market-tsla'
        };
        const elementId = elementIdMap[data.symbol];
        if (elementId) {
            updateTicker(elementId, data);
        }
    } else if (data.type === 'alert') {
        addAlert(`[${data.source}] ${data.headline}`, data.url);
    }
}

function updateTicker(elementId, data) {
    const el = document.getElementById(elementId);
    if (!el) return;

    const valueEl = el.querySelector('.value');
    const oldPrice = parseFloat(valueEl.textContent.replace(/[^0-9.-]+/g, "")) || 0;
    const newPrice = data.price;

    valueEl.textContent = newPrice.toLocaleString();

    // Animation
    if (newPrice > oldPrice) {
        valueEl.className = 'value up';
        el.style.animation = 'flashGreen 0.5s';
    } else if (newPrice < oldPrice) {
        valueEl.className = 'value down';
        el.style.animation = 'flashRed 0.5s';
    }

    // Reset animation
    setTimeout(() => {
        el.style.animation = '';
    }, 500);
}

// E2E Verification Helper
window.verifyUI = () => {
    console.log('Running UI Verification...');
    // Simulate Connect
    ipcRenderer.emit('ws-status', {}, { state: 'connected', url: 'ws://test.local' });

    // Simulate Tick (Up)
    setTimeout(() => updateMarketData({ type: 'ticker', symbol: '005930', price: 79000.0, timestamp: new Date().toISOString() }), 500);
    // Simulate Tick (Down)
    setTimeout(() => updateMarketData({ type: 'ticker', symbol: 'TSLA', price: 238.0, timestamp: new Date().toISOString() }), 1500);
    // Simulate Alert
    setTimeout(() => updateMarketData({ type: 'alert', symbol: 'BTC', price: 105000000 }), 2500);
};

function addAlert(message, url) {
    const li = document.createElement('li');
    li.className = 'alert-item';
    if (url) {
        li.style.cursor = 'pointer';
        li.onclick = () => {
            // Send IPC to open external URL
            ipcRenderer.send('open-url', url);
        };
    }

    const timeSpan = document.createElement('span');
    timeSpan.className = 'alert-time';
    timeSpan.textContent = new Date().toLocaleTimeString();

    const msgSpan = document.createElement('span');
    msgSpan.textContent = message;

    li.appendChild(msgSpan);
    li.appendChild(timeSpan);

    // Remove placeholder if exists
    const placeholder = elAlertList.querySelector('.placeholder');
    if (placeholder) placeholder.remove();

    elAlertList.prepend(li); // Add to top

    // Limit list size
    if (elAlertList.children.length > 50) {
        elAlertList.lastElementChild.remove();
    }
}
