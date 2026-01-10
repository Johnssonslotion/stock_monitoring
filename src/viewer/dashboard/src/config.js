/**
 * 동적 API 설정
 * 브라우저의 호스트 주소(window.location.hostname)를 기반으로 API 서버 주소를 결정합니다.
 * 이를 통해 Tailscale IP, Localhost 등 어떤 환경에서도 별도 설정 없이 접속 가능합니다.
 */

const API_PORT = 8000;
const HOST = window.location.hostname;

export const API_SERVER = `http://${HOST}:${API_PORT}`;
export const WS_SERVER = `ws://${HOST}:${API_PORT}/ws`;

console.log(`[Config] API: ${API_SERVER}, WS: ${WS_SERVER}`);
