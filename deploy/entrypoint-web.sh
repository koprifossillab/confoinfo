#!/bin/bash
# 뷰어 컨테이너 시작.
set -e

cd /app/web

python manage.py migrate --noinput

# 이미지에 든 학회 자료를 DB 에 맞춘다. pk 를 지키며 고치므로(loader.py) 브라우저에
# 남은 북마크가 그대로 붙는다. 파일 하나가 깨져도 뷰어는 띄운다 — 나머지 학회는
# 볼 수 있어야 하고, 실패는 로그와 smoke 가 잡는다.
python manage.py import_conference --all || echo "!! import_conference 가 실패했다 — 위를 볼 것" >&2

exec gunicorn confoinfoweb.wsgi:application \
    --bind 0.0.0.0:9090 \
    --workers "${GUNICORN_WORKERS:-2}" \
    --timeout 60 \
    --access-logfile - \
    --error-logfile -
