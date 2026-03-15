# PURECORTEX Deployment

## Supported Model
PURECORTEX currently deploys to a single GCP VM, `purecortex-master`, using the root `docker-compose.yml` stack plus `nginx.conf` for TLS termination and request routing.

Cloud Run is not the supported production path in this repository right now. The repo, scripts, and runbooks should assume the VM deployment model until the infrastructure is intentionally redesigned.

## Deployment Assets
- `docker-compose.yml`: backend, frontend, redis, and nginx services.
- `nginx.conf`: HTTPS termination, `/api` proxying, and `/ws` WebSocket proxying.
- `scripts/deploy_vm.sh`: run on the VM to build and restart the stack.
- `scripts/deploy_remote_vm.sh`: run locally to deploy over `gcloud compute ssh`.
- `.env.example`: required environment variables; copy to `.env` on the VM.

## Prerequisites
On the VM:
- Docker engine installed and running.
- Either `docker compose` or `docker-compose` installed.
- Git installed.
- Repo checked out at `/home/davidgarcia/PureCortex`.
- Root `.env` populated from `.env.example`.
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
3. Optionally runs `git fetch --all --prune` and `git pull --ff-only`.
4. Builds the images unless `--skip-build` is provided.
5. Restarts the stack with `up -d --remove-orphans`.
6. Prints service status and waits for the backend `/health` endpoint to pass inside the container.

## Verification
After deploy, verify:

```bash
docker compose ps
docker compose logs --tail=50 backend
docker compose logs --tail=50 frontend
```

If the VM only has legacy Compose v1 installed, replace `docker compose` with `docker-compose`.

Externally, confirm:
- `https://purecortex.ai/health` returns `200`.
- `https://purecortex.ai` loads the frontend.
- WebSocket chat can bootstrap through `POST /api/chat/session` and connect to `/ws/chat`.

## Notes
- Do not document or depend on raw VM IP addresses in tracked docs.
- Do not use the default Next.js Vercel flow for this frontend; production traffic is served from the VM stack.
- If you need to redeploy a previous commit, check out that commit on a clean VM worktree and rerun `scripts/deploy_vm.sh`.
