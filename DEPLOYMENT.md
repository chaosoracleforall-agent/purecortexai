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

## Notes
- Do not document or depend on raw VM IP addresses in tracked docs.
- Do not use the default Next.js Vercel flow for this frontend; production traffic is served from the VM stack.
- If you need to redeploy a previous commit, check out that commit on a clean VM worktree and rerun `scripts/deploy_vm.sh`.
- Do not mount signer secrets into the backend container. Keep signer-only material inside `.signer-secrets/`, which is mounted only into the isolated signer service.
