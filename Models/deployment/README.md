# SwarajDesk Dual-Model EC2 Deployment

Deploy **Vision_model** and **5_report_generator_AI** on a single EC2 with NGINX reverse proxy.

## Architecture

```
Internet → Cloudflare (SSL) → EC2 NGINX (port 80) → Model APIs
                                │
                 ┌──────────────┴──────────────┐
                 │                             │
    gsc-vision.abhasbehera.in     gsc-survey.abhasbehera.in
           ↓                              ↓
    Vision FastAPI (8001)       Survey FastAPI (8004)
    [systemd: vision-service]   [systemd: survey-service]
```

## Prerequisites

| Requirement | Details |
|---|---|
| EC2 Instance | `t3.large` (2 vCPU, 8GB RAM), Ubuntu 22.04 |
| Security Group | Ports 22 (SSH), 80 (HTTP), 443 (HTTPS) |
| IAM Role | S3 read access for `vision-model-615645510621` |
| DNS | Both domains → EC2 public IP (A records) |
| Cloudflare | Proxy enabled, SSL mode: Full |

## Quick Start

```bash
# 1. SSH into EC2
ssh -i your-key.pem ubuntu@<EC2-IP>

# 2. Clone the repository
git clone https://github.com/Aniroodh1234/SIH_models_monorepo.git
cd SIH_models_monorepo

# 3. Run the deployment script
cd Models/deployment
sudo bash deploy.sh

# 4. Verify deployment
bash health_check.sh
```

That's it. The script handles everything automatically (~15 minutes).

## What deploy.sh Does

| Step | Action | Duration |
|---|---|---|
| 1 | Install system packages (python3, nginx, awscli) | ~1 min |
| 2 | Create 4GB swap (safety net for 8GB RAM) | ~10 sec |
| 3 | Create Python virtual environments (isolated) | ~10 sec |
| 4 | pip install requirements for both models | ~5-10 min |
| 5 | Write `.env` files with production API keys | instant |
| 6 | Download Vision `.pt` weights from S3 (~1.3GB) | ~2-3 min |
| 7 | Build ChromaDB embeddings (if needed) | ~5-15 min |
| 8 | Install & enable systemd services | instant |
| 9 | Configure NGINX (domain-based routing) | instant |
| 10 | Start both model services | ~30 sec |
| 11 | Health check (retries up to 5 times) | ~30-60 sec |

## Service Details

### Vision Model (`gsc-vision.abhasbehera.in`)

| Item | Value |
|---|---|
| Port | 8001 |
| systemd | `vision-service` |
| Entry point | `uvicorn Fastapi_app.main:app` |
| Working dir | `Models/Vision_model/` |
| Model weights | 4× ViT `.pt` files (~1.3GB total) |
| Endpoints | `GET /`, `POST /predict`, `POST /predict-from-url` |

### Survey Report Generator (`gsc-survey.abhasbehera.in`)

| Item | Value |
|---|---|
| Port | 8004 |
| systemd | `survey-service` |
| Entry point | `uvicorn main:app` |
| Working dir | `Models/5_report_generator_AI/` |
| Data | ChromaDB (~54MB) + raw JSON datasets (~11MB) |
| Endpoints | `GET /health`, `GET /categories`, `POST /survey-report`, `POST /survey-report/stream` |

## Operations

### View Logs

```bash
# Vision model logs
sudo journalctl -u vision-service -f

# Survey model logs
sudo journalctl -u survey-service -f

# NGINX access logs
sudo tail -f /var/log/nginx/access.log
```

### Restart Services

```bash
sudo systemctl restart vision-service
sudo systemctl restart survey-service
sudo systemctl reload nginx
```

### Check Status

```bash
bash ~/SIH_models_monorepo/Models/deployment/health_check.sh
```

### Update Code (After git pull)

```bash
cd ~/SIH_models_monorepo
git pull origin main
sudo systemctl restart vision-service
sudo systemctl restart survey-service
```

## Memory Optimization Notes

On `t3.large` (8GB RAM) with 4GB swap:

| Component | ~RAM Usage |
|---|---|
| OS + NGINX | ~500MB |
| Vision (4× ViT + PyTorch) | ~2-2.5GB |
| Survey (ChromaDB + embeddings) | ~1-1.5GB |
| **Total** | **~4-4.5GB** |

- Swap at `vm.swappiness=10` ensures rarely-used pages can spill
- 1 uvicorn worker per model prevents memory duplication
- `MemoryMax` in systemd prevents OOM from taking down the instance

## Files

```
Models/deployment/
├── deploy.sh                 # Master bootstrap (run this)
├── nginx_models.conf         # NGINX reverse proxy config
├── vision-service.service    # systemd unit — Vision API
├── survey-service.service    # systemd unit — Survey API
├── health_check.sh           # Health check utility
└── README.md                 # This file
```
