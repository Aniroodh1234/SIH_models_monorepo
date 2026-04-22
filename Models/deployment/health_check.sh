#!/bin/bash
# ===========================================================================
#  SwarajDesk Deployment — Health Check Script
#  Checks: Vision API, Survey API, NGINX, systemd, memory, disk
#
#  Usage: bash health_check.sh
# ===========================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "\n${BOLD}${CYAN}═══════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  SwarajDesk — System Health Check${NC}"
echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════${NC}\n"

PASS=0
FAIL=0

check() {
    local name="$1"
    local status="$2"
    if [[ "${status}" == "ok" ]]; then
        echo -e "  ${GREEN}✅${NC} ${name}"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}❌${NC} ${name} — ${status}"
        FAIL=$((FAIL + 1))
    fi
}

# ─── systemd Services ─────────────────────────────────────────────────
echo -e "${BOLD}Services:${NC}"

VISION_SVC=$(systemctl is-active vision-service 2>/dev/null || echo "inactive")
check "vision-service (systemd)" "$([ "${VISION_SVC}" = "active" ] && echo ok || echo "${VISION_SVC}")"

SURVEY_SVC=$(systemctl is-active survey-service 2>/dev/null || echo "inactive")
check "survey-service (systemd)" "$([ "${SURVEY_SVC}" = "active" ] && echo ok || echo "${SURVEY_SVC}")"

NGINX_SVC=$(systemctl is-active nginx 2>/dev/null || echo "inactive")
check "nginx (systemd)" "$([ "${NGINX_SVC}" = "active" ] && echo ok || echo "${NGINX_SVC}")"

# ─── API Endpoints ─────────────────────────────────────────────────────
echo -e "\n${BOLD}API Endpoints:${NC}"

VISION_RESP=$(curl -sf --max-time 15 http://127.0.0.1:8001/ 2>/dev/null)
if [[ -n "${VISION_RESP}" ]]; then
    check "Vision API (port 8001)" "ok"
    echo -e "    Response: ${CYAN}${VISION_RESP}${NC}"
else
    check "Vision API (port 8001)" "no response"
fi

SURVEY_RESP=$(curl -sf --max-time 15 http://127.0.0.1:8004/health 2>/dev/null)
if [[ -n "${SURVEY_RESP}" ]]; then
    check "Survey API (port 8004)" "ok"
    echo -e "    Response: ${CYAN}${SURVEY_RESP}${NC}"
else
    check "Survey API (port 8004)" "no response"
fi

# ─── External Domain Check ────────────────────────────────────────────
echo -e "\n${BOLD}Domain Routing (via NGINX):${NC}"

VISION_EXT=$(curl -sf --max-time 10 -H "Host: gsc-vision.abhasbehera.in" http://127.0.0.1/ 2>/dev/null)
check "gsc-vision.abhasbehera.in → port 8001" "$([ -n "${VISION_EXT}" ] && echo ok || echo "no response")"

SURVEY_EXT=$(curl -sf --max-time 10 -H "Host: gsc-survey.abhasbehera.in" http://127.0.0.1/health 2>/dev/null)
check "gsc-survey.abhasbehera.in → port 8004" "$([ -n "${SURVEY_EXT}" ] && echo ok || echo "no response")"

# ─── Resource Usage ───────────────────────────────────────────────────
echo -e "\n${BOLD}Resource Usage:${NC}"

# Memory
MEM_TOTAL=$(free -m | awk '/^Mem:/{print $2}')
MEM_USED=$(free -m | awk '/^Mem:/{print $3}')
MEM_PERCENT=$((MEM_USED * 100 / MEM_TOTAL))
if [[ ${MEM_PERCENT} -lt 85 ]]; then
    check "Memory: ${MEM_USED}MB / ${MEM_TOTAL}MB (${MEM_PERCENT}%)" "ok"
else
    check "Memory: ${MEM_USED}MB / ${MEM_TOTAL}MB (${MEM_PERCENT}%)" "HIGH USAGE"
fi

# Swap
SWAP_TOTAL=$(free -m | awk '/^Swap:/{print $2}')
SWAP_USED=$(free -m | awk '/^Swap:/{print $3}')
if [[ ${SWAP_TOTAL} -gt 0 ]]; then
    SWAP_PERCENT=$((SWAP_USED * 100 / SWAP_TOTAL))
    check "Swap: ${SWAP_USED}MB / ${SWAP_TOTAL}MB (${SWAP_PERCENT}%)" "ok"
else
    check "Swap: not configured" "$(echo "no swap — run deploy.sh to create")"
fi

# Disk
DISK_PERCENT=$(df / | awk 'NR==2{print $5}' | tr -d '%')
DISK_AVAIL=$(df -h / | awk 'NR==2{print $4}')
if [[ ${DISK_PERCENT} -lt 85 ]]; then
    check "Disk: ${DISK_AVAIL} free (${DISK_PERCENT}% used)" "ok"
else
    check "Disk: ${DISK_AVAIL} free (${DISK_PERCENT}% used)" "LOW SPACE"
fi

# ─── Model Files Check ───────────────────────────────────────────────
echo -e "\n${BOLD}Model Files:${NC}"

MODEL_DIR="/home/ubuntu/SIH_models_monorepo/Models/Vision_model/Fastapi_app/models"
for f in sector_model.pt infra_model.pt education_model.pt environment_model.pt; do
    if [[ -f "${MODEL_DIR}/${f}" ]]; then
        SIZE=$(du -h "${MODEL_DIR}/${f}" | cut -f1)
        check "${f} (${SIZE})" "ok"
    else
        check "${f}" "MISSING"
    fi
done

CHROMA="/home/ubuntu/SIH_models_monorepo/Models/5_report_generator_AI/data/embeddings/chroma.sqlite3"
if [[ -f "${CHROMA}" ]]; then
    SIZE=$(du -h "${CHROMA}" | cut -f1)
    check "ChromaDB (${SIZE})" "ok"
else
    check "ChromaDB" "MISSING — run: python scripts/build_embeddings.py"
fi

# ─── Summary ──────────────────────────────────────────────────────────
echo -e "\n${BOLD}${CYAN}═══════════════════════════════════════════════════${NC}"
echo -e "  ${GREEN}Passed: ${PASS}${NC}  |  ${RED}Failed: ${FAIL}${NC}"
if [[ ${FAIL} -eq 0 ]]; then
    echo -e "  ${GREEN}${BOLD}🎉 All checks passed!${NC}"
else
    echo -e "  ${YELLOW}${BOLD}⚠ Some checks failed — review above${NC}"
fi
echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════${NC}\n"
