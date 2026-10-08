#!/usr/bin/env bash
# 배포한 것이 실제로 사는지 본다. ForGIA deploy/host/smoke.sh 를 줄인 것이다.
#
#   /srv/confoinfo/bin/smoke.sh              # .env 의 IMAGE_TAG 를 기대값으로
#   /srv/confoinfo/bin/smoke.sh v0.1.1
#
#   1. /healthz 200            컨테이너가 떴는가
#   2. 판이 기대한 것인가      배포가 실제로 갈렸는가
#   3. 학회·발표가 있는가      빈 DB 를 물고도 200 은 나온다 (import 실패 · 마운트 어긋남)
#   4. nginx 를 거쳐서 첫 화면 → 학회 하나 → 내 계획까지 그려지는가
set -uo pipefail

SRV="${CONFOINFO_SRV:-/srv/confoinfo}"
HEALTH="${CONFOINFO_HEALTH:-http://127.0.0.1:8096/healthz}"
SITE="${CONFOINFO_SITE:-http://127.0.0.1/confoinfo/}"
SMOKE_HOST="${CONFOINFO_SMOKE_HOST:-172.16.116.98}"

WANT="${1:-}"
if [ -z "$WANT" ] && [ -f "$SRV/.env" ]; then
    WANT=$(grep -oP '^IMAGE_TAG=\K.*' "$SRV/.env" 2>/dev/null || true)
fi

fails=0
ok()  { echo "  ✓ $*"; }
bad() { echo "  ✗ $*" >&2; fails=$((fails + 1)); }

echo "=== smoke $(date '+%F %T') ==="
[ -f "$SRV/maintenance.flag" ] && echo "  ! 유지보수 깃발이 서 있다 — 배포가 도는 중일 수 있다"

json=$(curl -s --max-time 10 "$HEALTH" 2>/dev/null || true)
if [ -z "$json" ]; then
    bad "/healthz 가 응답하지 않는다 — docker compose -f $SRV/docker-compose.yml logs --tail 50 web"
    exit 1
fi
eval "$(printf '%s' "$json" | python3 -c '
import json, sys, shlex
try:
    d = json.load(sys.stdin)
except ValueError:
    print("S_OK=0"); sys.exit()
for k, v in {"S_OK": 1, "S_STATUS": d.get("status", ""), "S_VER": d.get("version", ""),
             "S_CONF": d.get("conferences", -1), "S_TALKS": d.get("talks", -1)}.items():
    print(f"{k}={shlex.quote(str(v))}")
')"
if [ "${S_OK:-0}" != "1" ]; then
    bad "/healthz 가 JSON 이 아니다: ${json:0:120}"
    exit 1
fi
[ "$S_STATUS" = "ok" ] && ok "status=ok" || bad "status=$S_STATUS"

# 이미지의 판은 v 없이(0.1.0) 적혀 있고 태그는 v0.1.0 이다
if [ -z "$WANT" ]; then
    echo "  ! 기대하는 판을 모른다 — 뜬 것: $S_VER"
elif [ "v${S_VER#v}" = "v${WANT#v}" ]; then
    ok "판 $WANT"
else
    bad "판이 다르다 — 기대 $WANT · 실제 $S_VER"
fi

if [ "$S_CONF" -gt 0 ] && [ "$S_TALKS" -gt 0 ]; then
    ok "자료 있음 (학회 $S_CONF · 발표 $S_TALKS)"
else
    bad "자료가 비었다 (학회 $S_CONF · 발표 $S_TALKS) — 기동 로그의 import_conference 를 볼 것"
fi

get() { curl -s --max-time 10 -H "Host: $SMOKE_HOST" -w '\n%{http_code}' "$1" 2>/dev/null || true; }
resp=$(get "$SITE"); code=$(printf '%s' "$resp" | tail -n1); html=$(printf '%s' "$resp" | sed '$d')
case "$code" in
    200)
        ok "nginx 경유 $SITE 200"
        origin=$(printf '%s' "$SITE" | grep -oE '^https?://[^/]+')
        # 첫 화면의 학회 카드 하나를 따라간다 — 링크를 만들 수 있는가와 그 화면이
        # 그려지는가는 다른 물음이다
        link=$(printf '%s' "$html" | grep -oE 'class="conf-card" href="[^"]+"' | head -n1 \
               | sed 's/.*href="//; s/"$//')
        if [ -z "$link" ]; then
            bad "첫 화면에 학회 카드가 없다"
        else
            for path in "$link" "${link}plan/" "${link}sessions/"; do
                c=$(get "$origin$path" | tail -n1)
                [ "$c" = "200" ] && ok "$path 200" || bad "$path 가 $c"
            done
        fi
        ;;
    503) echo "  ! nginx 가 503 — 유지보수 안내 중이다 (깃발을 볼 것)" ;;
    *)   bad "nginx 경유가 200 이 아니다 (받은 것: ${code:-없음}) — nginx 조각이 들어갔는가? (HANDOFF 0절)" ;;
esac

echo
if [ "$fails" -eq 0 ]; then echo "smoke 통과."; exit 0; fi
echo "smoke 실패 — $fails 건." >&2
exit 1
