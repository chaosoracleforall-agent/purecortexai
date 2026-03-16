# PURECORTEX Deployment

## Supported Model
PURECORTEX currently deploys to a single GCP VM, `purecortex-master`, using the root `docker-compose.yml` stack plus `nginx.conf` for TLS termination and request routing.

The supported secure topology now includes:
- a dedicated `signer` container connected only by a shared Unix socket,
- an `oauth2-proxy` sidecar for Google SSO on `/admin`,
- and a dual database mode where the VM can run against local fallback Postgres or a managed Cloud SQL instance through the Cloud SQL Auth Proxy.

Cloud Run is not the supported production path in this repository right now. The repo, scripts, and runbooks should assume the VM deployment model until the infrastructure is intentionally redesigned.

## Deployment Assets
- `docker-compose.yml`: backend, signer, frontend, redis, nginx, `oauth2-proxy`, and database proxy/fallback services.
- `nginx.conf`: HTTPS termination, `/api` proxying, `/ws` WebSocket proxying, and `/admin` auth gating through `oauth2-proxy`.
- `scripts/deploy_vm.sh`: run on the VM to build and restart the stack.
- `scripts/deploy_remote_vm.sh`: run locally to deploy over `gcloud compute ssh`.
- `scripts/sync_runtime_env.py`: resolves runtime-only values such as Google OAuth, oauth2-proxy cookie secret, and database connection strings into the VM `.env` before deploy.
- `.env.example`: required environment variables; copy to `.env` on the VM.

## Prerequisites
On the VM:
- Docker engine installed and running.
- Either `docker compose` or `docker-compose` installed.
- Git installed.
- `gcloud` installed and available to the VM host so deploy-time secret sync can read Secret Manager.
- Repo checked out at `/home/davidgarcia/PureCortex`.
- Root `.env` populated from `.env.example`.
- Signer secret files staged under `/home/davidgarcia/PureCortex/.signer-secrets/` with filenames matching the secret names expected by the signer.
- Let's Encrypt certificates mounted at `/etc/letsencrypt`.

On the workstation:
- `gcloud` installed and authenticated for the `purecortexai` project.
- IAM access to SSH into `purecortex-master` through IAP.

## Security-Critical Environment Flags
Production should treat the reverse proxy as an explicit trust boundary. The current secure defaults fail closed unless these flags are intentionally enabled for the VM stack behind `nginx` plus `oauth2-proxy`.

- `PURECORTEX_TRUST_PROXY_HEADERS=1`
  Required only when the backend is reachable exclusively behind the trusted reverse proxy. This allows the backend to honor sanitized `X-Forwarded-For` / `X-Real-IP` values for rate limiting and IP allowlist enforcement.
- `PURECORTEX_TRUSTED_PROXY_CIDRS=...`
  Must contain only the CIDRs of the trusted reverse-proxy hop(s) that can reach the backend container. Do not include broad public ranges.
- `PURECORTEX_TRUST_ADMIN_EMAIL_HEADER=1`
  Required only when the frontend is reachable exclusively through `nginx` routes protected by `oauth2-proxy`, which strips any inbound spoofed header and injects the authenticated owner email on `/admin` and `/admin-api/*`.
- `PURECORTEX_INTERNAL_ADMIN_TOKEN=...`
  Required for the server-only frontend-to-backend admin bridge. Never expose this to browsers, client bundles, or public docs.
- `PURECORTEX_GOOGLE_OAUTH_CLIENT_ID`, `PURECORTEX_GOOGLE_OAUTH_CLIENT_SECRET`, `PURECORTEX_OAUTH2_PROXY_COOKIE_SECRET`
  Required before treating `/admin` as a production owner surface.
- `PURECORTEX_TURNSTILE_SITE_KEY`, `PURECORTEX_TURNSTILE_SECRET_KEY`
  Optional but recommended before exposing `/developers/access` broadly or making the repository public. When both are set, the public developer-access form requires Cloudflare Turnstile and the backend verifies the token before persisting a request.

Local development should leave proxy-header trust disabled unless you are explicitly reproducing the full reverse-proxy topology. Browser admin testing should use the dev-session path at `/admin/login` instead of trusting an identity header directly.

## Deploy From Your Workstation
Use the remote wrapper when you want to deploy the latest checked-out branch on the VM:

```bash
bash scripts/deploy_remote_vm.sh --pull
```

Useful variants:

```bash
# Reuse existing images
bash scripts/deploy_remote_vm.sh --pull --skip-build

# Follow logs after a successful deploy
bash scripts/deploy_remote_vm.sh --pull --tail-logs
```

## Deploy Directly On The VM
SSH to the VM with the managed GCP path, then run:

```bash
cd /home/davidgarcia/PureCortex
bash scripts/deploy_vm.sh --pull
```

Useful variants:

```bash
# Skip image rebuilds when only config or docs changed
bash scripts/deploy_vm.sh --skip-build

# Watch application logs after restart
bash scripts/deploy_vm.sh --tail-logs
```

## What The Script Does
`scripts/deploy_vm.sh` performs the supported deploy sequence:

1. Verifies Docker, Git, and the root `.env` file are available.
2. Detects whether the host uses `docker compose` or `docker-compose`.
3. Syncs runtime-only secrets and derived settings into `.env` using `scripts/sync_runtime_env.py`.
4. Optionally runs `git fetch --all --prune` and `git pull --ff-only`.
5. Builds the images unless `--skip-build` is provided.
6. Starts the supported service set:
   - local `postgres` for fallback environments, or
   - `cloudsql-proxy` when `PURECORTEX_CLOUD_SQL_CONNECTION_NAME` is configured.
7. Applies Alembic migrations after the database path is reachable.
8. Prints service status and waits for the isolated signer socket plus backend `/health` endpoint to pass.

## Verification
After deploy, verify:

```bash
docker compose ps
docker compose logs --tail=50 signer
docker compose logs --tail=50 backend
docker compose logs --tail=50 frontend
```

If the VM only has legacy Compose v1 installed, replace `docker compose` with `docker-compose`.

Externally, confirm:
- `https://purecortex.ai/health` returns `200`.
- `https://purecortex.ai` loads the frontend.
- `https://purecortex.ai/developers/access` loads the public request form.
- `https://purecortex.ai/admin` redirects through Google SSO or fails closed if `oauth2-proxy` is not yet configured.
- WebSocket chat can bootstrap through `POST /api/chat/session` and connect to `/ws/chat`.

Auth-boundary checks:
- Public requests to `/admin-api/control-plane` without authenticated `/admin` access return `403`.
- Direct requests to backend protected routes do not rely on `X-Forwarded-For` unless `PURECORTEX_TRUST_PROXY_HEADERS=1` is explicitly set.
- Admin and internal-admin JSON responses include `Cache-Control: no-store`.
- Public developer-access submissions enforce Turnstile only when both Turnstile keys are configured, while still keeping IP rate limiting and a per-email/per-IP cooldown path in place.

## Notes
- Do not document or depend on raw VM IP addresses in tracked docs.
- Do not use the default Next.js Vercel flow for this frontend; production traffic is served from the VM stack.
- If you need to redeploy a previous commit, check out that commit on a clean VM worktree and rerun `scripts/deploy_vm.sh`.
- Do not mount signer secrets into the backend container. Keep signer-only material inside `.signer-secrets/`, which is mounted only into the isolated signer service.
- Do not enable `PURECORTEX_TRUST_ADMIN_EMAIL_HEADER=1` on any frontend that is directly reachable without the `nginx` `auth_request` boundary.
