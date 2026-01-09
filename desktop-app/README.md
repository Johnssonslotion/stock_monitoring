# Stock Monitoring Desktop App (Mac)

This is a lightweight Electron app that creates a System Tray icon and receives real-time stock notifications from your Docker backend.

## 🚀 Setup Steps (On Your Mac)

1. **Prerequisites**:
   - Node.js installed on your Mac.

2. **Copy Files**:
   - Copy this entire `desktop-app` folder to your Mac (e.g., `~/Projects/stock-monitor-desktop`).

3. **Install Dependencies**:
   ```bash
   cd stock-monitor-desktop
   npm install
   ```

4. **Configuration**:
   - Open `main.js` configuration section.
   - Change `SERVER_URL` if your Docker VM is not on `localhost`.
     ```javascript
     // If accessing remote VM:
     const SERVER_URL = 'ws://<YOUR_VM_IP>:8000/ws';
     ```

5. **Icon Setup**:
   - Place a PNG file named `icon.png` in this folder to see it in the tray.

6. **Run App**:
   ```bash
   npm start
   ```
   - You should see a "Connecting..." status in your standardized Mac system tray.
   - Once connected, it will show "Connected 🟢".

## 🛠 Features
- **System Tray**: Shows connection status and lets you open the Dashboard.
- **Notifications**: Native Mac notifications when backend sends alerts.
- **Background Run**: Hides from Dock, lives in the top bar.

## ⚠️ Troubleshooting
- **Connection Failed**: check if port `8000` is allowed in Oracle Cloud Security List (Ingress TCP 8000).
- **Websocket Error**: Ensure `api-server` container is running (`docker ps`).
