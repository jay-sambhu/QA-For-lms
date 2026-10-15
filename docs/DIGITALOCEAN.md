# Deploying JASUSS on a single DigitalOcean droplet

This runs the whole stack (Caddy, Next.js, FastAPI, Celery worker with Chromium, Redis, Postgres) on one droplet using `docker-compose.yml`.

## 1. Pick a droplet

| Droplet | Monthly | Fits |
| --- | --- | --- |
| Basic, 2 GB / 1 vCPU / 50 GB | ~$12 | **Recommended.** One scan at a time with room to spare. |
| Basic, 1 GB / 1 vCPU / 25 GB | ~$6 | Possible with 2 GB swap and `QA_VIEWPORTS=desktop`; scans are slower and may hit swap. |

Approximate memory at rest / during a scan:

| Service | Idle | Scan peak | Limit |
| --- | --- | --- | --- |
| caddy | ~15 MB | — | 64 MB |
| web (Next.js standalone) | ~45 MB | ~100 MB | 256 MB |
| api (uvicorn, 1 process) | ~110 MB | ~150 MB | 384 MB |
| worker (Celery + Chromium) | ~120 MB | 500–900 MB | `WORKER_MEM_LIMIT` (1 GB) |
| redis | ~5 MB | — | 64 MB |
| postgres | ~30 MB | ~60 MB | 160 MB |

Choose Ubuntu 24.04 and add your SSH key.

## 2. Prepare the server

```bash
# Swap (protects against OOM during Chromium peaks)
fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
sysctl vm.swappiness=10 && echo 'vm.swappiness=10' >> /etc/sysctl.conf

# Docker
curl -fsSL https://get.docker.com | sh

# Firewall: only SSH + HTTP(S)
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw --force enable
```

## 3. Configure

```bash
git clone git@github.com:jay-sambhu/QA-For-lms.git jasuss && cd jasuss
cp .env.example .env
nano .env
```

Required in `.env`:

- `SITE_ADDRESS` — your domain (e.g. `jasuss.tech`) for automatic HTTPS, or `:80` to use the droplet IP over HTTP. Point the domain's A record at the droplet first.
- `NEXT_PUBLIC_APP_URL`, `ALLOWED_ORIGINS` — `https://your-domain`.
- `POSTGRES_PASSWORD` — long random string (`openssl rand -hex 24`).
- `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`.
- `ALLOW_LOCAL_TARGETS=false` (blocks scanning internal addresses).

In Supabase → Authentication → URL Configuration, set the Site URL to your domain and add `https://your-domain/auth/callback` to the redirect URLs.

`NEXT_PUBLIC_*` values are compiled into the web build, so rebuild `web` after changing them.

## 4. Run

```bash
docker compose up -d --build
docker compose ps
curl -s https://your-domain/healthz
```

Logs: `docker compose logs -f worker` (or `api`, `web`). Log files are rotated at 3 × 10 MB per service.

## 5. Update

```bash
git pull && docker compose up -d --build && docker image prune -f
```

## 6. Backups

```bash
docker compose exec -T db pg_dump -U jasuss jasuss | gzip > backup-$(date +%F).sql.gz
```

Scan artifacts live in the `user_data` volume. Screenshots and intermediate files older than `QA_ARTIFACT_RETENTION_DAYS` (default 7) are deleted automatically; final reports are kept and also uploaded to Supabase Storage.

## Tuning knobs

| Variable | Default | Effect |
| --- | --- | --- |
| `WORKER_CONCURRENCY` | 1 | Parallel scans. Each needs ~600–900 MB. |
| `WORKER_MEM_LIMIT` | 1g | Worker container memory cap. |
| `QA_VIEWPORTS` | all | e.g. `desktop` to crawl one viewport — much less RAM and time. |
| `QA_RENDERER_PROCESS_LIMIT` | 2 | Chromium renderer processes. |
| `QA_PIPELINE_TIMEOUT` | 1800 | Max seconds per scan. |
| `QA_ARTIFACT_RETENTION_DAYS` | 7 | Disk cleanup window; 0 disables. |

To save a further ~60 MB, point `DATABASE_URL` at Supabase's Postgres and remove the `db` service.
