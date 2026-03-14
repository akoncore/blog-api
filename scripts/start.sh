#!/usr/bin/env bash
# =============================================================================
#  bin/start.sh — Blog API: zero to running in one command
# =============================================================================
set -euo pipefail

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

# ── Helpers ───────────────────────────────────────────────────────────────────
step()  { echo -e "\n${CYAN}${BOLD}▶  $*${RESET}"; }
ok()    { echo -e "${GREEN}  ✔  $*${RESET}"; }
warn()  { echo -e "${YELLOW}  ⚠  $*${RESET}"; }
die()   {
    echo -e "\n${RED}${BOLD}  ✘  FAILED: $*${RESET}\n" >&2
    exit 1
}

# ── Banner ────────────────────────────────────────────────────────────────────
clear
echo -e "${CYAN}${BOLD}"
echo "  ╔══════════════════════════════════════════╗"
echo "  ║         🚀  Blog API  — Setup            ║"
echo "  ╚══════════════════════════════════════════╝"
echo -e "${RESET}"

# ─────────────────────────────────────────────────────────────────────────────
# 1. .env FILE
# ─────────────────────────────────────────────────────────────────────────────
step "Loading .env"

if [ ! -f ".env" ]; then
    die ".env file not found in $(pwd)"
fi

set -o allexport
# shellcheck source=/dev/null
source .env
set +o allexport

ok ".env loaded"

# ─────────────────────────────────────────────────────────────────────────────
# 2. VALIDATE REQUIRED VARIABLES
# ─────────────────────────────────────────────────────────────────────────────
step "Validating environment variables"

REQUIRED_VARS="SECRET_KEY BLOG_ENV_ID"
MISSING=0

for var in $REQUIRED_VARS; do
    if [ -z "${!var:-}" ]; then
        echo -e "${RED}  ✘  Missing required variable: ${BOLD}$var${RESET}"
        MISSING=1
    fi
done

if [ "$MISSING" -eq 1 ]; then
    echo -e "\n${YELLOW}  Tip: add the missing variables to your .env file.${RESET}\n"
    exit 1
fi

ok "All required environment variables are present"

# ─────────────────────────────────────────────────────────────────────────────
# 3. VIRTUAL ENVIRONMENT
# ─────────────────────────────────────────────────────────────────────────────
step "Setting up virtual environment"

if [ ! -d "venv" ]; then
    python3 -m venv venv || die "Failed to create virtual environment"
    ok "Virtual environment created"
else
    ok "Virtual environment already exists — skipping"
fi

# shellcheck source=/dev/null
source venv/bin/activate || die "Failed to activate virtual environment"
ok "Virtual environment active"

# ─────────────────────────────────────────────────────────────────────────────
# 4. DEPENDENCIES
# ─────────────────────────────────────────────────────────────────────────────
step "Installing dependencies"

pip install -q -r requirements/base.txt || die "pip install failed"
ok "Dependencies installed"

# ─────────────────────────────────────────────────────────────────────────────
# 5. MIGRATIONS
# ─────────────────────────────────────────────────────────────────────────────
step "Running migrations"

python manage.py migrate --noinput || die "migrate failed"
ok "Migrations done"

# ─────────────────────────────────────────────────────────────────────────────
# 6. STATIC FILES
# ─────────────────────────────────────────────────────────────────────────────
step "Collecting static files"

python manage.py collectstatic --noinput -v 0 || die "collectstatic failed"
ok "Static files collected"

# ─────────────────────────────────────────────────────────────────────────────
# 7. TRANSLATIONS
# ─────────────────────────────────────────────────────────────────────────────
step "Compiling translations"

PO_COUNT=$(find . -name "*.po" -not -path "./venv/*" | wc -l)
if [ "$PO_COUNT" -gt 0 ]; then
    python manage.py compilemessages || die "compilemessages failed"
    ok "Translations compiled"
else
    warn "No .po files found — skipping compilemessages"
fi

# ─────────────────────────────────────────────────────────────────────────────
# 8. SUPERUSER
# ─────────────────────────────────────────────────────────────────────────────
step "Creating superuser"

python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='admin@blog.com').exists():
    User.objects.create_superuser(
        email='admin@blog.com',
        full_name='Admin',
        password='admin1234'
    )
    print('CREATED')
else:
    print('EXISTS')
" | grep -q "CREATED" \
    && ok "Superuser created: admin@blog.com" \
    || warn "Superuser already exists — skipping"

# ─────────────────────────────────────────────────────────────────────────────
# 9. SEED TEST DATA
# ─────────────────────────────────────────────────────────────────────────────
step "Seeding test data"

python manage.py generate_users || die "generate_users command failed"
ok "Test data seeded"

# ─────────────────────────────────────────────────────────────────────────────
# 10. SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}  ╔══════════════════════════════════════════════════════════╗"
echo -e "  ║                  ✔  Blog API is ready!                  ║"
echo -e "  ╚══════════════════════════════════════════════════════════╝${RESET}"
echo ""
echo -e "${BOLD}  Endpoints${RESET}"
echo -e "  ${CYAN}●${RESET}  API        →  http://127.0.0.1:8000/api/"
echo -e "  ${CYAN}●${RESET}  Swagger    →  http://127.0.0.1:8000/api/docs/"
echo -e "  ${CYAN}●${RESET}  ReDoc      →  http://127.0.0.1:8000/api/redoc/"
echo -e "  ${CYAN}●${RESET}  Admin      →  http://127.0.0.1:8000/admin/"
echo ""
echo -e "${BOLD}  Superuser credentials${RESET}"
echo -e "  ${CYAN}●${RESET}  Email      →  admin@blog.com"
echo -e "  ${CYAN}●${RESET}  Password   →  admin1234"
echo ""
echo -e "${YELLOW}  Press Ctrl+C to stop the server.${RESET}"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# 11. START SERVER
# ─────────────────────────────────────────────────────────────────────────────
step "Starting development server"

python manage.py runserver || die "runserver failed"