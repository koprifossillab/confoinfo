#!/usr/bin/env bash
# icamg.org 의 프로그램·세션 소개 페이지를 raw/ 로 받는다. 받은 뒤 to_confoinfo.py.
#
#   sources/icamg2026/fetch.sh && python sources/icamg2026/to_confoinfo.py
#
# 받은 HTML 을 커밋한다 — 학회 사이트는 고쳐지고 사라진다. 어느 판에서 뽑았는지
# git 이 말해 준다.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p raw
for page in program proposed-session; do
    curl -sSfL --retry 3 -A "Mozilla/5.0" -o "raw/$page.html" "https://icamg.org/$page"
    echo "raw/$page.html  $(wc -c < "raw/$page.html") bytes"
done
