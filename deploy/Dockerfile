# 뷰어 이미지 (koprifossillab/confoinfo). strati2026 deploy/Dockerfile 과
# ForGIA deploy/Dockerfile.base 를 합쳤다.
#
#   docker build -f deploy/Dockerfile -t koprifossillab/confoinfo:v0.1.0 .
#
# **학회 자료(`conferences/*.json`)가 이미지에 들어간다.** 기동할 때마다
# entrypoint 가 그것을 DB 로 읽어 들이므로, 자료를 고치면 판을 올린다.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements-web.txt ./
RUN pip install -r requirements-web.txt

COPY . .

# 정적 파일을 굽는다 — 해시가 붙은 이름으로(캐시 무효화). 기동 때가 아니라 여기서
# 하는 것은 컨테이너가 uid 1000 으로 돌아 /app 에 못 쓰기 때문이다.
ENV CONFOINFO_STATIC_MANIFEST=1
RUN python web/manage.py collectstatic --noinput -v0

ENV HOME=/tmp \
    XDG_CACHE_HOME=/tmp/.cache

EXPOSE 9090
ENTRYPOINT ["/app/deploy/entrypoint-web.sh"]
