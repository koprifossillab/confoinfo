#!/usr/bin/env bash
# 저장소의 배포 파일을 /srv/confoinfo 로 옮긴다. 처음 한 번, 그리고 이 파일들이 바뀌었을 때.
#
#   deploy/host/sync_to_srv.sh            # 옮긴다
#   deploy/host/sync_to_srv.sh --list     # 무엇이 다른지만 본다
#
# .env 는 건드리지 않는다 — 없으면 견본에서 만들라고 알려 준다.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
SRV="${CONFOINFO_SRV:-/srv/confoinfo}"
LIST=0; [ "${1:-}" = "--list" ] && LIST=1

FILES=(
    "deploy/srv/docker-compose.yml:docker-compose.yml"
    "deploy/host/deploy.sh:bin/deploy.sh"
    "deploy/host/smoke.sh:bin/smoke.sh"
    "deploy/nginx/maintenance.html:www/confoinfo-maintenance.html"
    "deploy/nginx/unavailable.html:www/confoinfo-unavailable.html"
)

[ -d "$SRV" ] || { echo "$SRV 이 없다 — HANDOFF 0절의 admin 할 일부터" >&2; exit 1; }
for pair in "${FILES[@]}"; do
    src="$REPO/${pair%%:*}"; dst="$SRV/${pair##*:}"
    if [ -f "$dst" ] && cmp -s "$src" "$dst"; then
        echo "  같다    ${pair##*:}"
        continue
    fi
    if [ "$LIST" = 1 ]; then
        echo "  다르다  ${pair##*:}"
        continue
    fi
    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
    case "$dst" in *.sh) chmod +x "$dst" ;; esac
    echo "  옮겼다  ${pair##*:}"
done
mkdir -p "$SRV/db" "$SRV/backup"
[ -f "$SRV/.env" ] || echo "!! $SRV/.env 가 없다 — cp $REPO/deploy/srv/env.template $SRV/.env 하고 비밀키를 채울 것" >&2
