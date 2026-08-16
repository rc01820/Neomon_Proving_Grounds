#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# Neomon Proving Grounds — Installer
# Deploy one or more apps depending on customer requirements
# ──────────────────────────────────────────────────────────────
set -euo pipefail

BOLD="\033[1m"
DIM="\033[2m"
GREEN="\033[32m"
BLUE="\033[34m"
AMBER="\033[33m"
RED="\033[31m"
PURPLE="\033[35m"
RESET="\033[0m"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

declare -A APPS=(
    [aviondash]="AvionDash|Aviation / FAA|8001|${GREEN}"
    [codeblue]="CodeBlue|Healthcare|8002|${RED}"
    [blackledger]="BlackLedger|Financial Services|8003|${BLUE}"
    [sitedown]="SiteDown|IT Operations|8004|${PURPLE}"
)

APP_ORDER=(aviondash codeblue blackledger sitedown)

print_banner() {
    echo ""
    echo -e "${BOLD}  ╔══════════════════════════════════════════╗${RESET}"
    echo -e "${BOLD}  ║     NEOMON PROVING GROUNDS — INSTALL     ║${RESET}"
    echo -e "${BOLD}  ╚══════════════════════════════════════════╝${RESET}"
    echo ""
}

print_app_menu() {
    echo -e "  ${BOLD}Available applications:${RESET}"
    echo ""
    local i=1
    for key in "${APP_ORDER[@]}"; do
        IFS='|' read -r name theme port color <<< "${APPS[$key]}"
        echo -e "    ${BOLD}${i})${RESET}  ${color}${name}${RESET}  ${DIM}—${RESET}  ${theme}  ${DIM}(port ${port})${RESET}"
        ((i++))
    done
    echo ""
    echo -e "    ${BOLD}5)${RESET}  All applications"
    echo -e "    ${BOLD}0)${RESET}  Exit"
    echo ""
}

get_app_info() {
    local key="$1"
    local field="$2"
    IFS='|' read -r name theme port color <<< "${APPS[$key]}"
    case "$field" in
        name)  echo "$name" ;;
        theme) echo "$theme" ;;
        port)  echo "$port" ;;
    esac
}

check_port() {
    local port="$1"
    if command -v ss &>/dev/null; then
        ss -tuln 2>/dev/null | grep -q ":${port} " && return 1
    elif command -v netstat &>/dev/null; then
        netstat -tuln 2>/dev/null | grep -q ":${port} " && return 1
    fi
    return 0
}

deploy_app() {
    local key="$1"
    local custom_port="${2:-}"
    local name=$(get_app_info "$key" name)
    local default_port=$(get_app_info "$key" port)
    local port="${custom_port:-$default_port}"
    local app_dir="${SCRIPT_DIR}/${key}"

    if [ ! -d "$app_dir" ]; then
        echo -e "  ${RED}Error:${RESET} Directory ${app_dir} not found"
        return 1
    fi

    echo -e "  ${BOLD}Deploying ${name}...${RESET}"

    # Create .env if it doesn't exist
    if [ ! -f "${app_dir}/.env" ]; then
        cp "${app_dir}/.env.example" "${app_dir}/.env" 2>/dev/null || true
    fi

    # Override port if custom
    if [ -n "$custom_port" ] && [ "$custom_port" != "$default_port" ]; then
        echo -e "  ${DIM}Custom port: ${port}${RESET}"
        APP_PORT="$port" docker compose -f "${app_dir}/docker-compose.yml" \
            --project-name "proving-grounds-${key}" up -d --build
    else
        docker compose -f "${app_dir}/docker-compose.yml" \
            --project-name "proving-grounds-${key}" up -d --build
    fi

    echo -e "  ${GREEN}✓${RESET} ${name} running at ${BOLD}http://localhost:${port}${RESET}"
    echo ""
}

stop_app() {
    local key="$1"
    local name=$(get_app_info "$key" name)
    local app_dir="${SCRIPT_DIR}/${key}"

    echo -e "  Stopping ${name}..."
    docker compose -f "${app_dir}/docker-compose.yml" \
        --project-name "proving-grounds-${key}" down 2>/dev/null || true
    echo -e "  ${GREEN}✓${RESET} ${name} stopped"
}

do_install() {
    print_banner
    print_app_menu

    echo -ne "  ${BOLD}Select app(s) to deploy${RESET} ${DIM}(comma-separated, e.g. 1,3):${RESET} "
    read -r selection

    if [ "$selection" = "0" ]; then
        echo -e "\n  Exiting.\n"
        exit 0
    fi

    local selected_keys=()

    if [ "$selection" = "5" ]; then
        selected_keys=("${APP_ORDER[@]}")
    else
        IFS=',' read -ra choices <<< "$selection"
        for choice in "${choices[@]}"; do
            choice=$(echo "$choice" | tr -d ' ')
            case "$choice" in
                1) selected_keys+=(aviondash) ;;
                2) selected_keys+=(codeblue) ;;
                3) selected_keys+=(blackledger) ;;
                4) selected_keys+=(sitedown) ;;
                *) echo -e "  ${AMBER}Skipping invalid selection: ${choice}${RESET}" ;;
            esac
        done
    fi

    if [ ${#selected_keys[@]} -eq 0 ]; then
        echo -e "\n  ${RED}No valid apps selected.${RESET}\n"
        exit 1
    fi

    echo ""
    echo -e "  ${BOLD}Port configuration${RESET}"
    echo -e "  ${DIM}Press Enter to accept defaults, or type a custom port.${RESET}"
    echo ""

    declare -A port_overrides
    for key in "${selected_keys[@]}"; do
        local name=$(get_app_info "$key" name)
        local default_port=$(get_app_info "$key" port)
        echo -ne "    ${name} [${default_port}]: "
        read -r custom_port
        if [ -n "$custom_port" ]; then
            port_overrides[$key]="$custom_port"
        fi
    done

    echo ""
    echo -e "  ${BOLD}Checking prerequisites...${RESET}"

    if ! command -v docker &>/dev/null; then
        echo -e "  ${RED}Error:${RESET} Docker is not installed."
        exit 1
    fi

    if ! docker info &>/dev/null 2>&1; then
        echo -e "  ${RED}Error:${RESET} Docker daemon is not running."
        exit 1
    fi

    echo -e "  ${GREEN}✓${RESET} Docker is available"
    echo ""

    # Port conflict check
    for key in "${selected_keys[@]}"; do
        local port="${port_overrides[$key]:-$(get_app_info "$key" port)}"
        if ! check_port "$port"; then
            echo -e "  ${AMBER}Warning:${RESET} Port ${port} is already in use"
        fi
    done

    echo -e "\n  ${BOLD}Building and starting containers...${RESET}\n"

    for key in "${selected_keys[@]}"; do
        deploy_app "$key" "${port_overrides[$key]:-}"
    done

    echo -e "  ${GREEN}${BOLD}Deployment complete.${RESET}"
    echo ""
    echo -e "  ${BOLD}Installed apps:${RESET}"
    for key in "${selected_keys[@]}"; do
        local name=$(get_app_info "$key" name)
        local port="${port_overrides[$key]:-$(get_app_info "$key" port)}"
        echo -e "    → ${name}  http://localhost:${port}"
    done
    echo ""
    echo -e "  ${DIM}To stop:  ./install.sh stop${RESET}"
    echo -e "  ${DIM}To stop one:  cd <app> && docker compose down${RESET}"
    echo ""
}

do_stop() {
    print_banner
    echo -e "  ${BOLD}Stopping all Proving Grounds containers...${RESET}\n"
    for key in "${APP_ORDER[@]}"; do
        stop_app "$key"
    done
    echo ""
    echo -e "  ${GREEN}${BOLD}All apps stopped.${RESET}\n"
}

do_status() {
    print_banner
    echo -e "  ${BOLD}Status:${RESET}\n"
    for key in "${APP_ORDER[@]}"; do
        IFS='|' read -r name theme port color <<< "${APPS[$key]}"
        local state=$(docker inspect --format='{{.State.Status}}' "proving-grounds-${key}" 2>/dev/null || \
                      docker inspect --format='{{.State.Status}}' "${key}" 2>/dev/null || \
                      echo "not running")
        if [ "$state" = "running" ]; then
            echo -e "    ${GREEN}●${RESET}  ${color}${name}${RESET}  ${DIM}port ${port}${RESET}  ${GREEN}running${RESET}"
        else
            echo -e "    ${DIM}○  ${name}  port ${port}  ${state}${RESET}"
        fi
    done
    echo ""
}

# ── Main ──
case "${1:-install}" in
    install|start|up|deploy)  do_install ;;
    stop|down)                do_stop ;;
    status|ps)                do_status ;;
    *)
        echo ""
        echo "Usage: ./install.sh [command]"
        echo ""
        echo "Commands:"
        echo "  install   Select and deploy apps (default)"
        echo "  stop      Stop all running apps"
        echo "  status    Show running status"
        echo ""
        ;;
esac
