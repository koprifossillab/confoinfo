#!/usr/bin/env bash
# 판을 갈아 끼운다. ForGIA deploy/host/deploy.sh 를 줄인 것이다.
#
#   /srv/confoinfo/bin/deploy.sh v0.1.1
#   /srv/confoinfo/bin/deploy.sh v0.1.1 --no-pull    # 이미 로컬에 있는 이미지로
#
#   1. 이미지를 받는다        받다 실패하면 지금 도는 것을 안 건드리고 끝난다
#   2. .env 의 IMAGE_TAG 만   통째로 다시 만들지 않는다 — 비밀키가 날아간다
#   3. 유지보수 깃발          내리는 동안 사람이 맨 502 를 안 본다 (nginx 가 안내를 낸다)
#   4. 내리고 배포 전 사본    새 판의 마이그레이션이 DB 를 건드렸을 때 돌아올 지점
#   5. 올리고 health 게이트   200 이 안 나오면 실패로 끝낸다
#   6. smoke                  판·자료까지 본다 — 200 은 "떴다" 일 뿐이다
#
# **배포 전 사본이 sqlite 백업 API 가 아니라 cp 인 것은 1단계라서다.** 내린 뒤라
# 쓰는 쪽이 없고, DB 가 학회 자료의 사본뿐이라 잃어도 다시 생긴다. 2단계(동기화)
# 에서 사람의 자료가 들어오면 ForGIA 처럼 backup_db.py 로 바꾸고 시간별 백업을 건다.
set -euo pipefail

SRV="${CONFOINFO_SRV:-/srv/confoinfo}"
HEALTH="${CONFOINFO_HEALTH:-http://127.0.0.1:8096/healthz}"
FLAG="$SRV/maintenance.flag"
SNAP_DIR="$SRV/backup/pre_deploy"
KEEP=20

VER="${1:-}"
[ -n "$VER" ] || { echo "쓰임새: $0 <판> [--no-pull]   예: $0 v0.1.1" >&2; exit 1; }
PULL=1; [ "${2:-}" = "--no-pull" ] && PULL=0

cd "$SRV"
say() { echo "[$(date '+%F %T')] $*"; }

PREV=$(grep -oP '^IMAGE_TAG=\K.*' .env 2>/dev/null || echo "(없음)")
say "=== 배포 $PREV → $VER ==="

if [ "$PULL" = 1 ]; then
    say "이미지를 받는다"
    docker pull "koprifossillab/confoinfo:$VER"
fi

if grep -q '^IMAGE_TAG=' .env; then
    sed -i "s|^IMAGE_TAG=.*|IMAGE_TAG=$VER|" .env
else
    printf '\nIMAGE_TAG=%s\n' "$VER" >> .env
fi
say ".env 의 IMAGE_TAG 를 $VER 로"

touch "$FLAG"
trap 'rm -f "$FLAG"' EXIT
say "유지보수 모드"

docker compose stop web
docker compose rm -f web >/dev/null 2>&1 || true

DB="$SRV/db/confoinfo.db"
if [ -f "$DB" ]; then
    mkdir -p "$SNAP_DIR"
    snap="$SNAP_DIR/confoinfo_pre_${VER}_$(date -u +%Y%m%d_%H%M%S).db"
    cp -p "$DB" "$snap"
    say "배포 전 사본 $(basename "$snap")"
    ls -1t "$SNAP_DIR"/confoinfo_pre_*.db 2>/dev/null | tail -n +$((KEEP + 1)) | xargs -r rm -f
fi

docker compose up -d web
say "기동 확인 중 ($HEALTH)"
code=""
for i in $(seq 1 30); do
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$HEALTH" || true)
    if [ "$code" = "200" ]; then
        say "정상 ($((i * 2))초)"
        rm -f "$FLAG"
        docker compose ps --format '  {{.Name}}  {{.Image}}  {{.Status}}'
        break
    fi
    sleep 2
done

if [ "$code" != "200" ]; then
    say "실패 — $HEALTH 가 200 을 안 낸다. 되돌리려면:  $0 $PREV --no-pull" >&2
    docker compose logs --tail 30 web >&2
    exit 1
fi

SMOKE="$SRV/bin/smoke.sh"
if [ ! -x "$SMOKE" ]; then
    say "smoke.sh 가 없다: $SMOKE — sync_to_srv.sh 를 돌렸는가?" >&2
    exit 0
fi
if "$SMOKE" "$VER"; then
    say "=== 끝 ==="
    exit 0
fi
# 되돌리지 않는다. 새 판은 떠 있고, 무엇이 걸렸는지는 사람이 본다.
say "smoke 가 실패했다. 새 판($VER)은 떠 있다. 되돌리려면:  $0 $PREV --no-pull" >&2
exit 1
