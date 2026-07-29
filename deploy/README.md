# deploy — Web app packaging

Everything needed to run AViD as a web service. The container bundles Lean 4, a
precompiled Mathlib, the Python pipeline and the web frontend.

## Contents

| Path | Role |
|---|---|
| `Dockerfile` | Builds the full image: Lean toolchain, Mathlib oleans, the REPL binary, and the `Papers` root that D3 needs. |
| `landing.html` | The single-page frontend (Google sign-in, submit form, live progress via SSE). |
| `requirements_web.txt` | Python deps for the web server. |
| `assets/` | Static images used by the landing page. |
| `SETUP.md` | Hosting-specific setup notes. |
| `HF_README.md` | Hugging Face Space card / notes (legacy hosting target). |

## Quick deploy

From the repo root:

```bash
cp .env.example .env         # fill in OPENCODE_GO_API_KEY, GOOGLE_CLIENT_ID, …
docker compose up -d --build
docker compose logs -f       # wait for "REPL pool started" / "Analysis queue ready"
```

The container listens on port **7860**. `docker-compose.yaml` also wires up a Cloudflare
tunnel if `CLOUDFLARE_TUNNEL_TOKEN` is set.

> Full sizing (RAM/disk), concurrency tuning, Google OAuth setup, persistence and
> operations are in the **deploy guide** shared out-of-band — ask Ayrton for it.
> Persistent data lives in Docker volumes (`avid_users`, `avid_submissions`,
> `avid_lean`, `avid_cache`); back up the first two.
