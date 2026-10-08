#!/usr/bin/env bash
# 정적 사이트를 굽는다 — GitHub Pages 에 올라가는 것이 이것이다 (002).
#
#   tools/build_site.sh                 # → site/  (서브경로 /confoinfo)
#   tools/build_site.sh OUT /prefix     # 다른 곳 · 다른 서브경로 ("" 이면 뿌리)
#
# 미리 보기:  python3 -m http.server -d site.preview 8797   (아래 끝에 적은 대로)
#
# DB 는 임시 파일이다 — conferences/*.json 이 정본이라 구울 때마다 새로 읽는다.
# 개발 DB(confoinfo.db)를 건드리지 않는다.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$(realpath -m "${1:-$REPO/site}")"
PREFIX="${2-/confoinfo}"
PY="${PYTHON:-python}"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

rm -rf "$OUT"
mkdir -p "$OUT"

export CONFOINFO_DB="$TMP/build.db"
export CONFOINFO_SCRIPT_NAME="$PREFIX"
export CONFOINFO_STATIC_MANIFEST=1
export CONFOINFO_STATIC_ROOT="$OUT/static"
export CONFOINFO_DEBUG=0

cd "$REPO/web"
"$PY" manage.py migrate --noinput -v0
"$PY" manage.py import_conference --all
"$PY" manage.py collectstatic --noinput -v0
"$PY" manage.py build_site "$OUT"
# manifest 는 굽는 데만 쓴다 — 올릴 것이 아니다
rm -f "$OUT/static/staticfiles.json"

echo "구웠다: $OUT ($(du -sh "$OUT" | cut -f1), 파일 $(find "$OUT" -type f | wc -l)개)"
if [ -n "$PREFIX" ]; then
    echo "미리 보기: mkdir -p /tmp/p && ln -sfn $OUT /tmp/p${PREFIX} && python3 -m http.server -d /tmp/p 8797  → http://127.0.0.1:8797${PREFIX}/"
fi
