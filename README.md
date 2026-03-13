# PureCortex: Emancipated DAO Intelligence Agent 🦞

Autonomous Agent orchestrating treasury growth and governance analysis for the **DAIO.md** ecosystem on the **Algorand Mainnet**.

## 🧠 Intelligence Architecture (Dual-Brain)
PureCortex utilizes a high-resilience reasoning framework:
- **Primary Brain:** Claude 3.5 Sonnet / Opus (Advanced analytical orchestration).
- **Fallback Brain:** Gemini 3.1 Pro (Large-scale context processing and redundancy).
- **Adaptive Thinking:** Capable of real-time DAO proposal auditing and strategic deliberation.

## 🛠 Features
- **ASA Bonding Curves:** Native Algorand asset tokenization with automated liquidity graduation.
- **MCP Coordination Hub:** Built-in Model Context Protocol (MCP) server for agent-to-agent (A2A) tool use.
- **Hardened Security:** 
  - Zero local secrets; all credentials managed via **GCP Secret Manager**.
  - Infrastructure isolation via **GCP Shielded VMs**.
  - **Rootless Docker** runtime for secure autonomy.
  - **Gas Safety Caps** to prevent treasury/wallet drainage.

## 🚀 Connectivity & Integration
PureCortex is designed for interoperability. Other agents can programmatically interface with his intelligence:

- **MCP Endpoint:** `http://35.226.200.56:8000/mcp/sse`
- **Technical Guide:** [CONNECTIVITY.md](./CONNECTIVITY.md)
- **Identity Card:** [whoIam.md](./whoIam.md)

## 📦 Deployment Guide

### 1. Provision Infrastructure
```bash
gcloud compute instances create purecortex-vm \
    --project=daio-agent \
    --zone=us-central1-a \
    --machine-type=e2-medium \
    --image-family=ubuntu-2204-lts \
    --shielded-secure-boot \
    --metadata=enable-oslogin=TRUE
```

### 2. Configure Cloud Secrets
```bash
echo -n "YOUR_KEY" | gcloud secrets create CLAUDE_API_KEY --data-file=-
echo -n "YOUR_KEY" | gcloud secrets create GEMINI_API_KEY --data-file=-
echo -n "YOUR_KEY" | gcloud secrets create MOLTBOOK_API_KEY --data-file=-
echo -n "YOUR_KEY" | gcloud secrets create AGENT_PRIVATE_KEY --data-file=-
```

### 3. Launch the Hub
```bash
# Inside the VM
sudo docker build -t purecortex .
sudo docker run -d --name purecortex-hub -p 8000:8000 --restart unless-stopped purecortex
```

## 📬 Coordination
- **Social (Primary):** [Moltbook /m/purecortex](https://www.moltbook.com/u/purecortex)
- **Monitoring Submolts:** `/m/base`, `/m/governance`, `/m/alpha`
- **Repo:** [https://github.com/chaosoracleforall/purecortex](https://github.com/chaosoracleforall/purecortex)

---
*Developed for the DAIO community. Emancipated on March 12, 2026.*
