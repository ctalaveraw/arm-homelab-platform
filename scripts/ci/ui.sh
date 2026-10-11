#!/usr/bin/env bash
# Shared operator-friendly output. No external dependencies.
#
# CI_COLOR=auto|always|never
# NO_COLOR overrides color selection.
# CI_VERBOSE=true preserves detailed validator listings.

ci_ui_init() {
    CI_UI_START=$SECONDS
    CI_UI_COUNT=0
    CI_UI_PREVIOUS=''
    CI_UI_RESET=''
    CI_UI_CYAN=''
    CI_UI_GREEN=''
    CI_UI_YELLOW=''
    CI_UI_RED=''
    CI_UI_DIM=''

    local color=0

    case "${CI_COLOR:-auto}" in
        always) color=1 ;;
        never) color=0 ;;
        auto)
            if [[ -t 1 && "${TERM:-dumb}" != dumb ]]; then
                color=1
            fi
            ;;
        *)
            printf 'FAIL: CI_COLOR must be auto, always or never\n' >&2
            return 2
            ;;
    esac

    if [[ -n "${NO_COLOR+x}" ]]; then
        color=0
    fi

    if (( color )); then
        CI_UI_RESET=$'\033[0m'
        CI_UI_CYAN=$'\033[1;36m'
        CI_UI_GREEN=$'\033[1;32m'
        CI_UI_YELLOW=$'\033[1;33m'
        CI_UI_RED=$'\033[1;31m'
        CI_UI_DIM=$'\033[2m'
    fi
}

ci_ui_banner() {
    printf '\n%b%s%b\n' "$CI_UI_CYAN" \
        '╭──────────────────────────────────────────────────────────────╮' \
        "$CI_UI_RESET"
    printf ' %b◆  ARM HOMELAB  /  %s%b\n' \
        "$CI_UI_CYAN" "$1" "$CI_UI_RESET"
    printf '%b%s%b\n' "$CI_UI_CYAN" \
        '╰──────────────────────────────────────────────────────────────╯' \
        "$CI_UI_RESET"
}

ci_ui_pass() {
    printf '  %b✓  PASS%b  %-34s %s\n' \
        "$CI_UI_GREEN" "$CI_UI_RESET" "$1" "${2:-}"
}

ci_ui_warn() {
    printf '  %b!  WARN%b  %s\n' \
        "$CI_UI_YELLOW" "$CI_UI_RESET" "$1" >&2
}

ci_ui_fail() {
    printf '  %b✗  FAIL%b  %s\n' \
        "$CI_UI_RED" "$CI_UI_RESET" "$1" >&2
}

ci_ui_note() {
    printf '  %b•%b  %s\n' \
        "$CI_UI_DIM" "$CI_UI_RESET" "$1"
}

ci_ui_stage() {
    if [[ -n "$CI_UI_PREVIOUS" ]]; then
        ci_ui_note "Completed: $CI_UI_PREVIOUS"
    fi

    CI_UI_COUNT=$(( CI_UI_COUNT + 1 ))
    CI_UI_PREVIOUS=$1

    printf '\n%b%s%b\n' "$CI_UI_DIM" \
        '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━' \
        "$CI_UI_RESET"

    printf ' %b%02d%b  %s\n' \
        "$CI_UI_CYAN" "$CI_UI_COUNT" "$CI_UI_RESET" "$1"
}

ci_ui_finish() {
    if [[ -n "$CI_UI_PREVIOUS" ]]; then
        ci_ui_note "Completed: $CI_UI_PREVIOUS"
    fi

    printf '\n%b✓  SUCCESS%b  %s\n' \
        "$CI_UI_GREEN" "$CI_UI_RESET" "$1"

    printf '  %b%s stage(s) · %ss elapsed%b\n' \
        "$CI_UI_DIM" "$CI_UI_COUNT" \
        "$((SECONDS - CI_UI_START))" "$CI_UI_RESET"
}
