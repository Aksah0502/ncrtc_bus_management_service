# NCRTC frontend

Start the FastAPI service on `127.0.0.1:8000`, then run the frontend from this directory:

```powershell
npm.cmd install
npm.cmd run dev
```

Vite proxies `/api` to the local backend during development. The frontend uses `GET /api/v1/auth/me` and `POST /api/v1/auth/login`; the login request uses the backend's OAuth2 form fields (`username` and `password`).

Control-room operator accounts are sent to `/control-room` after authentication. The dashboard reads vehicles and depots from the fleet endpoints, polls AVLS live locations every five seconds, and requests live details for a selected vehicle. Its map uses OpenStreetMap tiles and needs network access. Incident cards are explicitly marked sample data because the backend does not expose incident endpoints yet. The global search is a visual placeholder.

Set `VITE_API_BASE_URL` in a local `.env` file to change the API prefix or point at another API origin. For a separately hosted frontend and API, the API host must permit the frontend origin through CORS or sit behind a same-origin reverse proxy. The current FastAPI app does not register CORS middleware.
