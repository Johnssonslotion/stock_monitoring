# Antigravity External Status Bridge

This is a standalone monitoring project split from the main traning engine. 
It provides a lightweight dashboard to monitor central infrastructure (A1) from edge nodes.

## Architecture
- **API**: FastAPI (Deploy on Northflank/GCP)
- **Frontend**: Vite + React + Tailwind (Deploy on Netlify)
- **Data Source**: OCI A1 TimescaleDB via Tailscale VPN

## Setup
1. **API**: Build the Docker image in `api/` and deploy to Northflank.
2. **Frontend**: Connect this repo to Netlify, pointing the base directory to `web/`.
3. **Connect**: Set `VITE_STATUS_API_URL` and `VITE_API_KEY` in Netlify ENV.
