#!/usr/bin/env bash
set -euo pipefail

# Colors (light usage)
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
RESET='\033[0m'

info() {
  echo -e "${BLUE}→ $1${RESET}"
}

success() {
  echo -e "${GREEN}✓ $1${RESET}"
}

error() {
  echo -e "${RED}✗ $1${RESET}"
}

echo ""
info "Starting project setup"

# -------------------------------------------------
# Load .env
# -------------------------------------------------
if [[ ! -f ".env" ]]; then
  error ".env file not found"
  exit 1
fi

info "Loading environment variables"
set -o allexport
source .env
set +o allexport

# -------------------------------------------------
# Check required variables
# -------------------------------------------------
REQUIRED=("SECRET_KEY" "BLOG_ENV_ID")

for VAR in "${REQUIRED[@]}"; do
  if [[ -z "${!VAR:-}" ]]; then
    error "Missing variable: $VAR"
    exit 1
  fi
done

success "Environment variables loaded"

# -------------------------------------------------
# Virtual environment
# -------------------------------------------------
if [[ ! -d "venv" ]]; then
  info "Creating virtual environment"
  python3 -m venv venv
fi

source venv/bin/activate
success "Virtual environment ready"

# -------------------------------------------------
# Dependencies
# -------------------------------------------------
info "Installing dependencies"
pip install -r requirements/base.txt

# -------------------------------------------------
# Migrations
# -------------------------------------------------
info "Running migrations"
python manage.py migrate --noinput

# -------------------------------------------------
# Static files
# -------------------------------------------------
info "Collecting static files"
python manage.py collectstatic --noinput > /dev/null

# -------------------------------------------------
# Translations
# -------------------------------------------------
if find . -name "*.po" -not -path "./venv/*" | grep -q .; then
  info "Compiling translations"
  python manage.py compilemessages
fi

# -------------------------------------------------
# Optional seed
# -------------------------------------------------
if python manage.py help | grep -q generate_users; then
  info "Generating test users"
  python manage.py generate_users
fi

if python manage.py help | grep -q generate_blog; then
  info "Generating test blog data"
  python manage.py generate_blog
fi

echo ""
success "Setup complete"
echo ""
echo "Run server:"
echo "  source venv/bin/activate"
echo "  python manage.py runserver"
echo ""
