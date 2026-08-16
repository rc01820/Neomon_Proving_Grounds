#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# Neomon Proving Grounds — Package for Customer Delivery
#
# Creates a standalone tar.gz for one or more apps that can be
# shipped to a customer without the rest of the suite.
# ──────────────────────────────────────────────────────────────
set -euo pipefail

BOLD="\033[1m"
DIM="\033[2m"
GREEN="\033[32m"
AMBER="\033[33m"
RED="\033[31m"
RESET="\033[0m"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="${SCRIPT_DIR}/dist"

VALID_APPS=(aviondash codeblue blackledger sitedown)

declare -A APP_NAMES=(
    [aviondash]="AvionDash"
    [codeblue]="CodeBlue"
    [blackledger]="BlackLedger"
    [sitedown]="SiteDown"
)

usage() {
    echo ""
    echo -e "${BOLD}Usage:${RESET} ./package.sh <app> [app2] [app3] [--all] [--output <dir>]"
    echo ""
    echo "Apps:  aviondash  codeblue  blackledger  sitedown"
    echo ""
    echo "Examples:"
    echo "  ./package.sh codeblue                  # Package CodeBlue for a healthcare customer"
    echo "  ./package.sh aviondash blackledger      # Package two apps together"
    echo "  ./package.sh --all                      # Package each app as a separate archive"
    echo "  ./package.sh codeblue --output ~/drops  # Custom output directory"
    echo ""
}

validate_app() {
    local app="$1"
    for valid in "${VALID_APPS[@]}"; do
        [ "$valid" = "$app" ] && return 0
    done
    return 1
}

package_single() {
    local app="$1"
    local name="${APP_NAMES[$app]}"
    local timestamp=$(date +%Y%m%d)
    local archive_name="${app}-${timestamp}.tar.gz"
    local staging_dir=$(mktemp -d)

    echo -e "  ${BOLD}Packaging ${name}...${RESET}"

    # Create staging structure
    local dest="${staging_dir}/${app}"
    mkdir -p "$dest"

    # Copy app files
    cp -r "${SCRIPT_DIR}/${app}/." "$dest/"

    # Create a standalone README header
    cat > "${dest}/INSTALL.md" << EOF
# ${name} — Neomon Proving Grounds

## Quick Install

\`\`\`bash
# Extract the archive
tar -xzf ${archive_name}
cd ${app}

# (Optional) Edit .env to customize ports and config
cp .env.example .env
vi .env

# Build and run
docker compose up -d --build
\`\`\`

## Verify

Open your browser to the URL shown after startup (default: http://localhost:\$(grep APP_PORT .env.example | cut -d= -f2)).

Check health:
\`\`\`bash
curl http://localhost:\$(grep APP_PORT .env.example | cut -d= -f2)/api/health
\`\`\`

## Stop

\`\`\`bash
docker compose down
\`\`\`

## Fault Injection

Open the Fault Console tab in the UI, or use the API:

\`\`\`bash
# List all faults
curl http://localhost:\$(grep APP_PORT .env.example | cut -d= -f2)/api/faults

# Activate a fault
curl -X POST http://localhost:\$(grep APP_PORT .env.example | cut -d= -f2)/api/faults/APP-01/activate

# Deactivate
curl -X POST http://localhost:\$(grep APP_PORT .env.example | cut -d= -f2)/api/faults/APP-01/deactivate
\`\`\`

## Requirements

- Docker Engine 20.10+
- Docker Compose v2+
- 1 GB RAM
- Datadog Agent (optional)

---

See README.md for full documentation, fault catalog, and Datadog integration details.

© 2026 Neomon Labs
EOF

    # Create the archive
    mkdir -p "$OUTPUT_DIR"
    tar -czf "${OUTPUT_DIR}/${archive_name}" -C "$staging_dir" "$app"

    local size=$(du -h "${OUTPUT_DIR}/${archive_name}" | cut -f1)
    echo -e "  ${GREEN}✓${RESET} ${archive_name}  ${DIM}(${size})${RESET}"

    # Cleanup
    rm -rf "$staging_dir"
}

package_bundle() {
    local apps=("$@")
    local timestamp=$(date +%Y%m%d)
    local bundle_name
    local staging_dir=$(mktemp -d)

    if [ ${#apps[@]} -eq ${#VALID_APPS[@]} ]; then
        bundle_name="neomon-proving-grounds-${timestamp}.tar.gz"
    else
        bundle_name="proving-grounds-$(IFS=-; echo "${apps[*]}")-${timestamp}.tar.gz"
    fi

    echo -e "  ${BOLD}Creating bundle: ${bundle_name}${RESET}"

    local dest="${staging_dir}/proving-grounds"
    mkdir -p "$dest"

    # Copy selected apps
    for app in "${apps[@]}"; do
        cp -r "${SCRIPT_DIR}/${app}" "${dest}/"
    done

    # Generate a custom docker-compose that only includes selected apps
    cat > "${dest}/docker-compose.yml" << 'HEADER'
version: "3.9"

services:
HEADER

    for app in "${apps[@]}"; do
        local port=$(grep APP_PORT "${SCRIPT_DIR}/${app}/.env.example" | cut -d= -f2)
        cat >> "${dest}/docker-compose.yml" << EOF
  ${app}:
    build: ./${app}
    container_name: proving-grounds-${app}
    ports:
      - "\${${app^^}_PORT:-${port}}:${port}"
    env_file:
      - ./${app}/.env
    volumes:
      - ${app}-data:/app/data
    restart: unless-stopped

EOF
    done

    echo "volumes:" >> "${dest}/docker-compose.yml"
    for app in "${apps[@]}"; do
        echo "  ${app}-data:" >> "${dest}/docker-compose.yml"
    done

    # Bundle README
    cat > "${dest}/README.md" << EOF
# Neomon Proving Grounds — Custom Bundle

This bundle contains the following applications:

EOF
    for app in "${apps[@]}"; do
        local name="${APP_NAMES[$app]}"
        local port=$(grep APP_PORT "${SCRIPT_DIR}/${app}/.env.example" | cut -d= -f2)
        echo "- **${name}** — http://localhost:${port}" >> "${dest}/README.md"
    done

    cat >> "${dest}/README.md" << 'EOF'

## Quick Start

```bash
docker compose up -d --build
```

## Stop

```bash
docker compose down
```

See each app's README.md for full documentation.

© 2026 Neomon Labs
EOF

    mkdir -p "$OUTPUT_DIR"
    tar -czf "${OUTPUT_DIR}/${bundle_name}" -C "$staging_dir" "proving-grounds"

    local size=$(du -h "${OUTPUT_DIR}/${bundle_name}" | cut -f1)
    echo -e "  ${GREEN}✓${RESET} ${bundle_name}  ${DIM}(${size})${RESET}"

    rm -rf "$staging_dir"
}

# ── Parse args ──
SELECTED_APPS=()
PACKAGE_ALL=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --all|-a)
            PACKAGE_ALL=true
            shift ;;
        --output|-o)
            OUTPUT_DIR="$2"
            shift 2 ;;
        --help|-h)
            usage
            exit 0 ;;
        *)
            if validate_app "$1"; then
                SELECTED_APPS+=("$1")
            else
                echo -e "${RED}Error:${RESET} Unknown app '$1'"
                usage
                exit 1
            fi
            shift ;;
    esac
done

echo ""
echo -e "${BOLD}  Neomon Proving Grounds — Packager${RESET}"
echo ""

if $PACKAGE_ALL; then
    echo -e "  ${BOLD}Packaging all apps individually...${RESET}\n"
    for app in "${VALID_APPS[@]}"; do
        package_single "$app"
    done
    echo ""
    echo -e "  ${BOLD}Creating full suite bundle...${RESET}\n"
    package_bundle "${VALID_APPS[@]}"
elif [ ${#SELECTED_APPS[@]} -eq 0 ]; then
    usage
    exit 1
elif [ ${#SELECTED_APPS[@]} -eq 1 ]; then
    package_single "${SELECTED_APPS[0]}"
else
    echo -e "  ${BOLD}Packaging ${#SELECTED_APPS[@]} apps as bundle...${RESET}\n"
    package_bundle "${SELECTED_APPS[@]}"
fi

echo ""
echo -e "  ${GREEN}${BOLD}Done.${RESET} Archives in: ${OUTPUT_DIR}"
echo ""
