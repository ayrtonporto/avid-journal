# AViD Journal — Server Setup

This guide deploys AViD Journal on any Linux/Mac/Windows machine with Docker.
After setup, your domain will serve the full pipeline: upload → analyze → verdicts.

## Prerequisites

- Docker + Docker Compose installed
- `git` installed
- Domain delegated to Cloudflare (`avidjournal.com.ar` or your own)

---

## Step 1 — Clone the repo

```bash
git clone https://github.com/ayrtonporto/avid-journal.git
cd avid-journal
```

---

## Step 2 — Create the Cloudflare Tunnel

1. Go to https://one.dash.cloudflare.com/
2. **Networks** → **Tunnels** → **Create a tunnel**
3. Name: `avid-journal`
4. Save. Copy the **tunnel token** (starts with `eyJ...`)
5. Go to **Public Hostnames** tab, add:
   - `avidjournal.com.ar` → service: `http://avid:7860`
   - `www.avidjournal.com.ar` → service: `http://avid:7860`

---

## Step 3 — Create the `.env` file

```bash
cp .env.example .env
```

Edit `.env` and fill in:

```ini
OPENCODE_GO_API_KEY=sk-xxx
CLOUDFLARE_TUNNEL_TOKEN=eyJ...
```

Optional:
```ini
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
AVID_SMTP_HOST=smtp.gmail.com
AVID_SMTP_PORT=587
AVID_SMTP_USER=you@gmail.com
AVID_SMTP_PASS=your-app-password
AVID_SMTP_FROM=you@gmail.com
```

---

## Step 4 — Start everything

```bash
docker compose up -d
```

First build takes 15-30 minutes (Mathlib ~2 GB download). Subsequent starts are instant.

---

## Step 5 — Verify

Wait 2-3 minutes for the healthcheck to pass, then:

```bash
# Check if the server is alive
curl http://localhost:7860/api/health

# Check via your domain (once DNS propagates)
curl https://avidjournal.com.ar/api/health
```

Visit `https://avidjournal.com.ar` in your browser.

---

## Useful commands

```bash
docker compose logs -f           # follow all logs
docker compose logs avid         # server logs only
docker compose logs cloudflared  # tunnel logs
docker compose restart           # restart everything
docker compose down              # stop (data preserved in volumes)
docker compose pull              # update images
docker compose up -d --build     # rebuild after code changes
```

---

## Troubleshooting

**Server won't start:**
```bash
docker compose logs avid | tail -50
```

**Mathlib cache fails:**
```bash
docker compose exec avid lake exe cache get
```

**Tunnel won't connect:**
- Check token is correct in `.env`
- Check Cloudflare Tunnel status at https://one.dash.cloudflare.com/

**Domain not resolving:**
```bash
nslookup avidjournal.com.ar
```
Should return Cloudflare IPs. If not, DNS delegation hasn't propagated yet (can take up to 48h for `.ar` domains).