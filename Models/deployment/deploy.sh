#!/bin/bash
# ===========================================================================
#  SwarajDesk Dual-Model EC2 Deployment Script
#  Models: Vision_model (port 8001) + 5_report_generator_AI (port 8000)
#  Gateway: NGINX (domain-based reverse proxy)
#  Domains: gsc-vision.abhasbehera.in | gsc-survey.abhasbehera.in
#
#  Usage:
#    cd ~/SIH_models_monorepo/Models/deployment
#    sudo bash deploy.sh
#
#  Prerequisites:
#    - Ubuntu 22.04+ EC2 instance (t3.large recommended)
#    - IAM role with S3 read access attached
#    - DNS A records pointing both domains to this instance's public IP
# ===========================================================================

set -euo pipefail

# ─── Colors & Logging ─────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log_info()    { echo -e "${CYAN}[INFO]${NC}    $1"; }
log_success() { echo -e "${GREEN}[✅ OK]${NC}    $1"; }
log_warn()    { echo -e "${YELLOW}[⚠ WARN]${NC}  $1"; }
log_error()   { echo -e "${RED}[❌ ERROR]${NC} $1"; }
log_step()    { echo -e "\n${BOLD}${CYAN}═══════════════════════════════════════════════════════════${NC}"; echo -e "${BOLD}  $1${NC}"; echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════${NC}"; }

# ─── Path Configuration ───────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
MODELS_DIR="${REPO_ROOT}/Models"
DEPLOY_DIR="${SCRIPT_DIR}"

# Vision Model paths
VISION_DIR="${MODELS_DIR}/Vision_model"
VISION_APP_DIR="${VISION_DIR}/Fastapi_app"
VISION_MODELS_DIR="${VISION_APP_DIR}/models"
VISION_VENV="${VISION_DIR}/venv"
VISION_PORT=8001

# Survey/Report Model paths
SURVEY_DIR="${MODELS_DIR}/5_report_generator_AI"
SURVEY_VENV="${SURVEY_DIR}/venv"
SURVEY_PORT=8000

# S3 Configuration
S3_BUCKET="vision-model-615645510621"
S3_REGION="ap-south-1"

# Model weight files expected
VISION_MODEL_FILES=("sector_model.pt" "infra_model.pt" "education_model.pt" "environment_model.pt")

# ─── Preflight Checks ────────────────────────────────────────────────────

log_step "Step 0/11 — Preflight Checks"

if [[ $EUID -ne 0 ]]; then
    log_error "This script must be run as root (sudo bash deploy.sh)"
    exit 1
fi

if [[ ! -d "${VISION_DIR}" ]]; then
    log_error "Vision_model directory not found at: ${VISION_DIR}"
    log_error "Make sure you cloned the full SIH_models_monorepo"
    exit 1
fi

if [[ ! -d "${SURVEY_DIR}" ]]; then
    log_error "5_report_generator_AI directory not found at: ${SURVEY_DIR}"
    exit 1
fi

log_success "Repository structure validated"
log_info "Repo root: ${REPO_ROOT}"
log_info "Vision model: ${VISION_DIR}"
log_info "Survey model: ${SURVEY_DIR}"

# ─── Step 1: System Packages ─────────────────────────────────────────────

log_step "Step 1/11 — Installing System Packages"

export DEBIAN_FRONTEND=noninteractive

apt-get update -y
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    nginx \
    git \
    curl \
    unzip \
    awscli \
    jq \
    htop

log_success "System packages installed"

# ─── Step 2: Swap Space (Critical for t3.large with 8GB RAM) ─────────────

log_step "Step 2/11 — Configuring Swap Space"

SWAP_FILE="/swapfile"
SWAP_SIZE="4G"

if [[ -f "${SWAP_FILE}" ]]; then
    log_info "Swap file already exists, skipping creation"
else
    log_info "Creating ${SWAP_SIZE} swap file..."
    fallocate -l ${SWAP_SIZE} ${SWAP_FILE}
    chmod 600 ${SWAP_FILE}
    mkswap ${SWAP_FILE}
    swapon ${SWAP_FILE}

    # Make swap persistent across reboots
    if ! grep -q "${SWAP_FILE}" /etc/fstab; then
        echo "${SWAP_FILE} none swap sw 0 0" >> /etc/fstab
    fi

    log_success "Swap file created and enabled"
fi

# Tune swappiness for this workload (lower = prefer RAM, use swap only when needed)
sysctl vm.swappiness=10
if ! grep -q "vm.swappiness" /etc/sysctl.conf; then
    echo "vm.swappiness=10" >> /etc/sysctl.conf
fi

log_info "Current swap status:"
swapon --show
free -h

# ─── Step 3: Python Virtual Environments ─────────────────────────────────

log_step "Step 3/11 — Creating Python Virtual Environments"

# Vision Model venv
if [[ -d "${VISION_VENV}" ]]; then
    log_info "Vision venv already exists, skipping creation"
else
    log_info "Creating Vision model venv..."
    sudo -u ubuntu python3 -m venv "${VISION_VENV}"
    log_success "Vision venv created"
fi

# Survey Model venv
if [[ -d "${SURVEY_VENV}" ]]; then
    log_info "Survey venv already exists, skipping creation"
else
    log_info "Creating Survey model venv..."
    sudo -u ubuntu python3 -m venv "${SURVEY_VENV}"
    log_success "Survey venv created"
fi

# ─── Step 4: Install Python Dependencies ─────────────────────────────────

log_step "Step 4/11 — Installing Python Dependencies"

log_info "Installing Vision model dependencies (this may take 5-10 minutes)..."
sudo -u ubuntu "${VISION_VENV}/bin/pip" install --upgrade pip
sudo -u ubuntu "${VISION_VENV}/bin/pip" install -r "${VISION_APP_DIR}/requirements.txt"
log_success "Vision model dependencies installed"

log_info "Installing Survey model dependencies (this may take 5-10 minutes)..."
sudo -u ubuntu "${SURVEY_VENV}/bin/pip" install --upgrade pip
sudo -u ubuntu "${SURVEY_VENV}/bin/pip" install -r "${SURVEY_DIR}/requirements.txt"
log_success "Survey model dependencies installed"

# ─── Step 5: Environment Files ────────────────────────────────────────────

log_step "Step 5/11 — Writing Environment Files"

# Vision Model .env
cat > "${VISION_DIR}/.env" << 'VISION_ENV'
HUGGINGFACEHUB_API_TOKEN=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
LANGCHAIN_API_KEY=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
GROQ_API_KEY=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
GEMINI_API_KEY=AQ.Ab8RN6LAbQljVjn1zWTB-gl1jgJAbk5AoP8ejeGzbUtpiOirew
VISION_ENV

chown ubuntu:ubuntu "${VISION_DIR}/.env"
chmod 600 "${VISION_DIR}/.env"
log_success "Vision .env written"

# Survey Model .env
cat > "${SURVEY_DIR}/.env" << 'SURVEY_ENV'
# Gemini
GEMINI_API_KEY=AQ.Ab8RN6LAbQljVjn1zWTB-gl1jgJAbk5AoP8ejeGzbUtpiOirew

# Groq
GROQ_API_KEY=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

# HuggingFace
HUGGINGFACE_API_KEY=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

# LangChain (optional tracing)
LANGCHAIN_API_KEY=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
LANGCHAIN_TRACING_V2=true

# Config
MODEL_NAME=gemini-2.5-flash
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
VECTOR_DB=chroma
SURVEY_ENV

chown ubuntu:ubuntu "${SURVEY_DIR}/.env"
chmod 600 "${SURVEY_DIR}/.env"
log_success "Survey .env written"

# ─── Step 6: Download Vision Model Weights from S3 ───────────────────────

log_step "Step 6/11 — Downloading Vision Model Weights from S3"

# Create models directory if it doesn't exist
sudo -u ubuntu mkdir -p "${VISION_MODELS_DIR}"

MODELS_MISSING=false
for model_file in "${VISION_MODEL_FILES[@]}"; do
    if [[ ! -f "${VISION_MODELS_DIR}/${model_file}" ]]; then
        MODELS_MISSING=true
        log_warn "Missing: ${model_file}"
    else
        log_info "Found: ${model_file} ($(du -h "${VISION_MODELS_DIR}/${model_file}" | cut -f1))"
    fi
done

if [[ "${MODELS_MISSING}" == "true" ]]; then
    log_info "Downloading model weights from S3 bucket: ${S3_BUCKET}..."
    log_info "This will download ~1.3GB — may take a few minutes..."

    sudo -u ubuntu aws s3 sync \
        "s3://${S3_BUCKET}/" \
        "${VISION_MODELS_DIR}/" \
        --region "${S3_REGION}" \
        --exclude "*" \
        --include "*.pt"

    # Verify all files downloaded
    ALL_PRESENT=true
    for model_file in "${VISION_MODEL_FILES[@]}"; do
        if [[ ! -f "${VISION_MODELS_DIR}/${model_file}" ]]; then
            log_error "Failed to download: ${model_file}"
            ALL_PRESENT=false
        fi
    done

    if [[ "${ALL_PRESENT}" == "true" ]]; then
        log_success "All 4 model weights downloaded from S3"
    else
        log_error "Some model weights are missing. Check S3 bucket contents."
        log_error "Expected files in s3://${S3_BUCKET}/: ${VISION_MODEL_FILES[*]}"
        exit 1
    fi
else
    log_success "All 4 model weights already present — skipping S3 download"
fi

# ─── Step 7: Build ChromaDB Embeddings for Report Generator ──────────────

log_step "Step 7/11 — Building ChromaDB Embeddings (Report Generator)"

EMBEDDINGS_DIR="${SURVEY_DIR}/data/embeddings"
RAW_DIR="${SURVEY_DIR}/data/raw"

# Check if raw data exists
if [[ ! -f "${RAW_DIR}/dataset_fixed.json" ]] || [[ ! -f "${RAW_DIR}/swarajdesk_survey_flattened.json" ]]; then
    log_error "Raw dataset files missing in ${RAW_DIR}/"
    log_error "Expected: dataset_fixed.json, swarajdesk_survey_flattened.json"
    exit 1
fi
log_info "Raw datasets found"

# Check if embeddings already built
if [[ -f "${EMBEDDINGS_DIR}/chroma.sqlite3" ]]; then
    DB_SIZE=$(du -h "${EMBEDDINGS_DIR}/chroma.sqlite3" | cut -f1)
    log_info "ChromaDB already exists (${DB_SIZE}) — skipping rebuild"
    log_info "To force rebuild, delete ${EMBEDDINGS_DIR}/ and re-run"
else
    log_info "Building ChromaDB embeddings — this may take 5-15 minutes..."
    sudo -u ubuntu mkdir -p "${EMBEDDINGS_DIR}"

    cd "${SURVEY_DIR}"
    sudo -u ubuntu "${SURVEY_VENV}/bin/python" scripts/build_embeddings.py
    cd "${DEPLOY_DIR}"

    if [[ -f "${EMBEDDINGS_DIR}/chroma.sqlite3" ]]; then
        DB_SIZE=$(du -h "${EMBEDDINGS_DIR}/chroma.sqlite3" | cut -f1)
        log_success "ChromaDB embeddings built successfully (${DB_SIZE})"
    else
        log_error "ChromaDB embedding build failed — chroma.sqlite3 not found"
        exit 1
    fi
fi

# ─── Step 8: Install systemd Services ────────────────────────────────────

log_step "Step 8/11 — Installing systemd Services"

# Vision Model Service
cp "${DEPLOY_DIR}/vision-service.service" /etc/systemd/system/vision-service.service
log_success "vision-service.service installed"

# Survey Model Service
cp "${DEPLOY_DIR}/survey-service.service" /etc/systemd/system/survey-service.service
log_success "survey-service.service installed"

# Reload systemd daemon
systemctl daemon-reload
log_success "systemd daemon reloaded"

# Enable services (auto-start on boot)
systemctl enable vision-service
systemctl enable survey-service
log_success "Services enabled for auto-start on boot"

# ─── Step 9: Configure NGINX ─────────────────────────────────────────────

log_step "Step 9/11 — Configuring NGINX"

# Remove default NGINX site
rm -f /etc/nginx/sites-enabled/default
log_info "Removed default NGINX site"

# Install model configs
cp "${DEPLOY_DIR}/nginx_models.conf" /etc/nginx/sites-available/swarajdesk-models
log_info "NGINX config copied to sites-available"

# Enable the site via symlink
ln -sf /etc/nginx/sites-available/swarajdesk-models /etc/nginx/sites-enabled/swarajdesk-models
log_info "NGINX site enabled via symlink"

# Test NGINX config syntax
if nginx -t 2>&1; then
    log_success "NGINX configuration syntax is valid"
else
    log_error "NGINX configuration has syntax errors — aborting"
    nginx -t
    exit 1
fi

# Reload NGINX
systemctl reload nginx
systemctl enable nginx
log_success "NGINX reloaded and enabled"

# ─── Step 10: Start Model Services ───────────────────────────────────────

log_step "Step 10/11 — Starting Model Services"

log_info "Starting Vision model service..."
systemctl restart vision-service
sleep 3

VISION_STATUS=$(systemctl is-active vision-service 2>/dev/null || true)
if [[ "${VISION_STATUS}" == "active" ]]; then
    log_success "vision-service is running"
else
    log_warn "vision-service may still be starting (model weight loading takes time)..."
    log_info "Status: ${VISION_STATUS}"
    log_info "Check logs: sudo journalctl -u vision-service -f"
fi

log_info "Starting Survey model service..."
systemctl restart survey-service
sleep 3

SURVEY_STATUS=$(systemctl is-active survey-service 2>/dev/null || true)
if [[ "${SURVEY_STATUS}" == "active" ]]; then
    log_success "survey-service is running"
else
    log_warn "survey-service may still be starting (embedding model loading takes time)..."
    log_info "Status: ${SURVEY_STATUS}"
    log_info "Check logs: sudo journalctl -u survey-service -f"
fi

# ─── Step 11: Health Checks ──────────────────────────────────────────────

log_step "Step 11/11 — Running Health Checks"

log_info "Waiting 30 seconds for models to fully load into memory..."
sleep 30

VISION_HEALTHY=false
SURVEY_HEALTHY=false

# Vision health check (retry up to 5 times)
for i in {1..5}; do
    log_info "Vision health check attempt ${i}/5..."
    RESPONSE=$(curl -sf --max-time 10 "http://127.0.0.1:${VISION_PORT}/" 2>/dev/null || true)
    if [[ -n "${RESPONSE}" ]]; then
        log_success "Vision API responding: ${RESPONSE}"
        VISION_HEALTHY=true
        break
    fi
    sleep 10
done

# Survey health check (retry up to 5 times)
for i in {1..5}; do
    log_info "Survey health check attempt ${i}/5..."
    RESPONSE=$(curl -sf --max-time 10 "http://127.0.0.1:${SURVEY_PORT}/health" 2>/dev/null || true)
    if [[ -n "${RESPONSE}" ]]; then
        log_success "Survey API responding: ${RESPONSE}"
        SURVEY_HEALTHY=true
        break
    fi
    sleep 10
done

# ─── Final Summary ───────────────────────────────────────────────────────

echo ""
echo -e "${BOLD}${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║         SwarajDesk Dual-Model Deployment — Summary           ║${NC}"
echo -e "${BOLD}${CYAN}╠═══════════════════════════════════════════════════════════════╣${NC}"
echo -e "${CYAN}║${NC}                                                               ${CYAN}║${NC}"

if [[ "${VISION_HEALTHY}" == "true" ]]; then
    echo -e "${CYAN}║${NC}  ${GREEN}✅${NC} Vision Model                                              ${CYAN}║${NC}"
else
    echo -e "${CYAN}║${NC}  ${RED}❌${NC} Vision Model (check: journalctl -u vision-service -f)      ${CYAN}║${NC}"
fi
echo -e "${CYAN}║${NC}     Internal : http://127.0.0.1:${VISION_PORT}                          ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}     Domain   : https://gsc-vision.abhasbehera.in              ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}     Swagger  : https://gsc-vision.abhasbehera.in/docs         ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}                                                               ${CYAN}║${NC}"

if [[ "${SURVEY_HEALTHY}" == "true" ]]; then
    echo -e "${CYAN}║${NC}  ${GREEN}✅${NC} Survey Report Generator                                   ${CYAN}║${NC}"
else
    echo -e "${CYAN}║${NC}  ${RED}❌${NC} Survey Report Generator (check: journalctl -u survey-service -f)${CYAN}║${NC}"
fi
echo -e "${CYAN}║${NC}     Internal : http://127.0.0.1:${SURVEY_PORT}                          ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}     Domain   : https://gsc-survey.abhasbehera.in              ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}     Swagger  : https://gsc-survey.abhasbehera.in/docs         ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}                                                               ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  ${BOLD}NGINX Gateway${NC}                                                ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}     Status   : $(systemctl is-active nginx)                                     ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}     Config   : /etc/nginx/sites-enabled/swarajdesk-models     ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}                                                               ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  ${BOLD}Useful Commands${NC}                                              ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}     Logs     : sudo journalctl -u vision-service -f           ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}               sudo journalctl -u survey-service -f            ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}     Restart  : sudo systemctl restart vision-service           ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}               sudo systemctl restart survey-service            ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}     Health   : bash ${DEPLOY_DIR}/health_check.sh              ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}     Memory   : free -h && htop                                ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}                                                               ${CYAN}║${NC}"
echo -e "${BOLD}${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

if [[ "${VISION_HEALTHY}" == "true" ]] && [[ "${SURVEY_HEALTHY}" == "true" ]]; then
    log_success "🎉 Deployment completed successfully! Both models are live."
else
    log_warn "Some services may still be loading. Give them 1-2 more minutes for model weights."
    log_info "Run 'bash ${DEPLOY_DIR}/health_check.sh' to re-check."
fi
