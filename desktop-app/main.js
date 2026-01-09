const { app, BrowserWindow, Tray, Menu, Notification, ipcMain } = require('electron');
const path = require('path');
const WebSocket = require('ws');

let mainWindow = null;
let tray = null;
let ws = null;
// Server URL (Configurable)
const SERVER_URL = 'ws://localhost:8000/ws';

// Ensure single instance lock (optional but good for tray apps)
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
    app.quit();
}

function createMainWindow() {
    mainWindow = new BrowserWindow({
        width: 400,
        height: 600,
        show: false, // Don't show until ready
        frame: false, // Frameless for custom clean look
        resizable: false,
        skipTaskbar: true, // Don't show in dock/taskbar (Tray only feel)
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false // For simple IPC in this prototype
        },
        backgroundColor: '#050510'
    });

    mainWindow.loadFile('index.html');

    // Hide instead of close
    mainWindow.on('close', (event) => {
        if (!app.isQuitting) {
            event.preventDefault();
            mainWindow.hide();
        }
    });

    mainWindow.once('ready-to-show', () => {
        // Position window near tray or center? For now, center but maybe allow move
        // mainWindow.show(); // Optional: Start hidden
    });
}

function createTray() {
    const iconPath = path.join(__dirname, 'icon.png');
    tray = new Tray(iconPath);

    const contextMenu = Menu.buildFromTemplate([
        { label: '주식 모니터 (Stock Monitor)', enabled: false },
        { type: 'separator' },
        { label: '대시보드 열기', click: toggleWindow },
        { label: '상태: 연결 중...', enabled: false, id: 'status' },
        { type: 'separator' },
        {
            label: '종료', click: () => {
                app.isQuitting = true;
                app.quit();
            }
        }
    ]);

    tray.setToolTip('주식 모니터');
    tray.setContextMenu(contextMenu);

    tray.on('click', toggleWindow);
}

function toggleWindow() {
    if (mainWindow.isVisible()) {
        mainWindow.hide();
    } else {
        const { x, y } = tray.getBounds();
        const { width, height } = mainWindow.getBounds();
        // Simple logic to place near tray (macOS usually top right)
        // Adjust based on OS if needed. For now, just show center or remembered pos.
        // mainWindow.setBounds({ x: x - width / 2, y: y + 20, width, height });
        mainWindow.show();
        mainWindow.focus();
    }
}

function connectWebSocket() {
    ws = new WebSocket(SERVER_URL);

    ws.on('open', () => {
        console.log('Connected to Stock Server');
        updateTrayStatus('Status: Connected 🟢');
        if (mainWindow) mainWindow.webContents.send('ws-status', { state: 'connected', url: SERVER_URL });
    });

    ws.on('message', (data) => {
        try {
            const message = JSON.parse(data);
            // Forward to Renderer
            if (mainWindow) mainWindow.webContents.send('ws-data', message);

            // Optional: Tray tooltip update
            if (message.type === 'ticker' && (message.symbol === '005930' || message.symbol === 'TSLA')) {
                tray.setToolTip(`${message.symbol}: ${message.price}`);
            }

            // News Notification
            if (message.type === 'alert') {
                new Notification({
                    title: `[${message.source}] ${message.symbol || 'Market'}`,
                    body: message.headline,
                    silent: false
                }).show();
            }
        } catch (e) {
            console.error('Parse error:', e);
        }
    });

    ws.on('close', () => {
        console.log('Disconnected');
        updateTrayStatus('Status: Disconnected 🔴');
        if (mainWindow) mainWindow.webContents.send('ws-status', { state: 'disconnected' });
        setTimeout(connectWebSocket, 5000);
    });

    ws.on('error', (err) => {
        console.error('WS Error:', err);
    });
}

function updateTrayStatus(label) {
    if (!tray) return;
    // Note: Rebuilding menu can be expensive/flickery. Better to get item by ID if Electron version supports it better.
    // For simple menu, rebuild is fine.
    const contextMenu = Menu.buildFromTemplate([
        { label: '주식 모니터 (Stock Monitor)', enabled: false },
        { type: 'separator' },
        { label: mainWindow?.isVisible() ? '대시보드 숨기기' : '대시보드 열기', click: toggleWindow },
        { label: label, enabled: false, id: 'status' },
        { type: 'separator' },
        {
            label: '종료', click: () => {
                app.isQuitting = true;
                app.quit();
            }
        }
    ]);
    tray.setContextMenu(contextMenu);
}

// IPC from Renderer
ipcMain.on('window-action', (event, action) => {
    if (action === 'hide') {
        mainWindow.hide();
    }
});

ipcMain.on('open-url', (event, url) => {
    require('electron').shell.openExternal(url);
});

// Hide Dock Icon (MacOS)
if (process.platform === 'darwin') {
    app.dock.hide();
}

app.whenReady().then(() => {
    createMainWindow();
    createTray();
    connectWebSocket();
});

app.on('window-all-closed', () => {
    // Keep running
});
