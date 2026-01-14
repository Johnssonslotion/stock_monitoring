import { ipcRenderer, contextBridge } from 'electron'

// --------- Allowed IPC Channels (Whitelist) ---------
const VALID_CHANNELS = [
    'main-process-message',
    'system-status-request',
    'notification-show',
]

// --------- Expose restricted API to the Renderer process ---------
contextBridge.exposeInMainWorld('ipcRenderer', {
    on(channel: string, listener: (event: any, ...args: any[]) => void) {
        if (VALID_CHANNELS.includes(channel)) {
            // @ts-ignore
            return ipcRenderer.on(channel, (event, ...args) => listener(event, ...args))
        }
    },
    off(channel: string, ...args: any[]) {
        if (VALID_CHANNELS.includes(channel)) {
            // @ts-ignore
            return ipcRenderer.off(channel, ...args)
        }
    },
    send(channel: string, ...args: any[]) {
        if (VALID_CHANNELS.includes(channel)) {
            ipcRenderer.send(channel, ...args)
        }
    },
    invoke(channel: string, ...args: any[]) {
        if (VALID_CHANNELS.includes(channel)) {
            return ipcRenderer.invoke(channel, ...args)
        }
    },
})
