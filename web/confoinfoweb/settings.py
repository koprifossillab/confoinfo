"""
confoinfo 설정. strati2026 4972d35 `config/settings.py` 를 바탕으로, 환경 규약
(`.env` · `/srv/<앱>/db/` · 서브경로 · 시험 DB)은 DiaRUGA·ForGIA 를 따랐다 (P01).

학회 자료는 저장소의 `conferences/*.json` 이 정본이고 DB 는 그것을 읽어 들인
사본이다. 기동할 때마다 `import_conference --all` 이 다시 맞춘다(entrypoint).
"""
import os
import tempfile
from pathlib import Path

# web/confoinfoweb/settings.py -> web/ -> 프로젝트 루트
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent


def _load_dotenv(path):
    """프로젝트 루트의 .env 를 환경변수로 올린다 (이미 있는 값은 덮지 않는다).

    ForGIA 의 것과 같다. 컨테이너는 compose 가 환경변수를 직접 주므로 이 파일
    없이도 돈다 — 그래서 없어도 조용히 넘어간다. KEY=VALUE 와 주석뿐이다.
    """
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_dotenv(PROJECT_ROOT / ".env")

SECRET_KEY = os.environ.get("CONFOINFO_SECRET_KEY", "dev-only-not-a-secret")
DEBUG = os.environ.get("CONFOINFO_DEBUG", "1") == "1"

# 이 서버가 실제로 응답할 이름만 명시한다 (ForGIA 와 같은 목록).
# 다른 호스트명으로 붙어야 하면 CONFOINFO_HOSTS 에 콤마로 구분해 넣는다.
ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "[::1]",
    "172.16.116.98",    # 이 서버의 사내망 주소
    "paleo-server",     # 이 머신의 hostname
    "paleolab",         # nginx phyloserver 블록의 server_name
]
ALLOWED_HOSTS += [h.strip() for h in os.environ.get("CONFOINFO_HOSTS", "").split(",") if h.strip()]

# 서브경로 아래에 얹을 때 쓴다 (예: "/confoinfo"). 빈 값이면 뿌리(/)에 붙는다.
# 사내 VPN 이 80 만 통과시켜 DiaRUGA·ForGIA 와 같이 phyloserver 블록 안에
# 서브경로로 들어간다. JS 는 base.html 이 내보내는 window.CONFO.root 를 쓴다 —
# 절대경로를 박아 두면 여기만 바꿔서는 안 돌아간다.
FORCE_SCRIPT_NAME = os.environ.get("CONFOINFO_SCRIPT_NAME", "").rstrip("/") or None

CSRF_TRUSTED_ORIGINS = [
    f"http://{h}" for h in ALLOWED_HOSTS if not h.startswith("[")
]

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "conference",
]

# 로그인도 세션도 없다 — 북마크·메모는 브라우저 localStorage 에 있다.
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "confoinfoweb.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": [
            "django.template.context_processors.request",
            "conference.context.version",
        ]},
    }
]

WSGI_APPLICATION = "confoinfoweb.wsgi.application"

CONFOINFO_DB = Path(os.environ.get("CONFOINFO_DB", PROJECT_ROOT / "confoinfo.db"))
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": CONFOINFO_DB,
        "OPTIONS": {
            "timeout": 20,
            "init_command": (
                "PRAGMA journal_mode=WAL;"
                "PRAGMA synchronous=NORMAL;"
                "PRAGMA foreign_keys=ON;"
            ),
        },
        # 시험 DB 는 파일로 만든다 (DiaRUGA 183 — 공유 캐시 인메모리의 테이블
        # 잠금이 브라우저 레이어에서 풀리지 않았다). 이름의 pid 는 두 벌이 동시에
        # 돌 때 서로 안 밟게 한다.
        "TEST": {
            "NAME": os.environ.get(
                "CONFOINFO_TEST_DB",
                str(Path(tempfile.gettempdir()) / f"confoinfo_test_{os.getpid()}.db")),
        },
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# **서브경로를 직접 붙인다.** 상대경로("static/")로 두면 Django 가 SCRIPT_NAME 을
# 붙여 주기는 하는데, 처음 읽힌 값을 캐시한다 — gunicorn 에서는 whitenoise 가
# 요청이 오기 전에 읽어서 접두 없는 "/static/" 이 굳었고 CSS 가 404 였다(001).
# whitenoise 는 FORCE_SCRIPT_NAME 을 떼고 "/static/" 으로 받는다 — nginx 가
# /confoinfo/ 를 떼고 넘기므로 그것이 맞다.
STATIC_URL = (FORCE_SCRIPT_NAME or "") + "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# 해시가 붙은 파일 이름(캐시 무효화)은 collectstatic 을 거친 이미지에서만 쓴다.
# 개발·시험에서는 manifest 가 없어 Manifest 저장소가 템플릿을 못 그린다.
# Dockerfile 이 빌드 때 collectstatic 을 돌리고 이 값을 1 로 둔다.
_MANIFEST = os.environ.get("CONFOINFO_STATIC_MANIFEST", "0") == "1"
# whitenoise 는 collectstatic 이 끝난 이미지에서만 낀다. 개발은 runserver 가
# 정적 파일을 내주고, 없는 STATIC_ROOT 를 보며 경고를 내지도 않는다.
if _MANIFEST:
    MIDDLEWARE.insert(2, "whitenoise.middleware.WhiteNoiseMiddleware")
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": (
        "whitenoise.storage.CompressedManifestStaticFilesStorage" if _MANIFEST
        else "django.contrib.staticfiles.storage.StaticFilesStorage")},
}

LANGUAGE_CODE = "en-us"
# 서버의 시각. 학회 일정은 학회마다 `Conference.timezone` 으로 따로 다룬다.
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True

# --- confoinfo 전용 -------------------------------------------------------

# 학회 자료(`<slug>.json`)가 놓인 곳. `import_conference --all` 이 이 안을 전부 읽는다.
CONFERENCES_DIR = Path(os.environ.get("CONFOINFO_CONFERENCES_DIR", PROJECT_ROOT / "conferences"))
