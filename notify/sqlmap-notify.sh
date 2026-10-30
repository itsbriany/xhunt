#!/bin/bash
set -euo pipefail

# Notifications are opt-in; never fall back to notify's default provider file.
if [[ -z "${NOTIFY_PROVIDER_CONFIG:-}" ]]; then
    exit 0
fi

if [[ ! -f "$NOTIFY_PROVIDER_CONFIG" || ! -r "$NOTIFY_PROVIDER_CONFIG" ]]; then
    printf '%s\n' 'NOTIFY_PROVIDER_CONFIG must refer to a readable regular file.' >&2
    exit 2
fi

# Keep the existing provider id for compatibility, including the sqlmap wrapper.
printf '%s\n' "$*" | notify -silent -disable-update-check -id dalfox \
    -provider-config "$NOTIFY_PROVIDER_CONFIG"
