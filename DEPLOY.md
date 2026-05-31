# Deploying SYNK

SYNK splits into a **server** (FastAPI/WebSocket) and a **static client** (the Three.js
demo). Deploy the server somewhere it can hold a WebSocket; host the client as static files
pointing at the server. Configs for two common paths are in the repo.

> Local instead? `docker compose up --build` runs both (see the README).

## 1. Server — Render (Blueprint)

`render.yaml` is committed. In Render: **New → Blueprint**, select this repo. It builds
`server/Dockerfile`, exposes `/healthz`, and mounts a 1 GB disk at `/data` so the SQLite
world (`SYNK_DB_PATH=/data/synk.db`) survives restarts. After the client is up, set
`ALLOWED_ORIGINS` to the client URL.

## 1-alt. Server — Fly.io

`server/fly.toml` is committed. From `server/`:

```bash
fly launch --no-deploy   # accept the existing fly.toml; create a volume named synk_data
fly deploy
fly secrets set ALLOWED_ORIGINS=https://<your-client-host>
```

Your server is now at `https://<app>.fly.dev` (WebSocket: `wss://<app>.fly.dev/ws`).

## 2. Client — Cloudflare Pages

Connect the repo in Cloudflare Pages with:

| Setting | Value |
| --- | --- |
| Root directory | `client` |
| Build command | `npm run build` |
| Build output directory | `dist` |
| Environment variable | `VITE_SYNK_WS = wss://<your-server-host>/ws` |

The client reads `VITE_SYNK_WS` at build time (falling back to `ws://localhost:8000/ws` for
local dev). `client/public/_redirects` provides the SPA fallback. Any static host works
(Netlify, GitHub Pages, S3+CloudFront) — just build with `VITE_SYNK_WS` set and serve `dist/`.

## 3. Wire the two together

1. Deploy the server; note its host.
2. Build/deploy the client with `VITE_SYNK_WS=wss://<server-host>/ws`.
3. Set the server's `ALLOWED_ORIGINS` to the client's origin (e.g. `https://synk.pages.dev`)
   so the WebSocket Origin check and CORS allow it.
4. Open the client URL — WASD to move, walk up to an NPC, talk.

**Security note:** always set `ALLOWED_ORIGINS` in production (unset = allow-all, dev only),
and put a real LLM behind a key via `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` if you want
LLM dialogue instead of the offline MockProvider.
