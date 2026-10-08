"""
confoinfo 설정. strati2026 4972d35 `config/settings.py` 를 바탕으로, 환경 규약
(`.env` · 서브경로 · 시험 DB)은 DiaRUGA·ForGIA 를 따랐다 (P01).

학회 자료는 저장소의 `conferences/*.json` 이 정본이고 DB 는 그것을 읽어 들인
사본이다. 운영 서버는 없다 — `tools/build_site.sh` 가 화면을 파일로 구워
GitHub Pages 에 올린다 (002).
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

# 서브경로 아래에 얹을 때 쓴다. GitHub Pages 는 koprifossillab.github.io/confoinfo/
# 라 build_site 가 "/confoinfo" 로 굽는다. 개발 서버는 빈 값(뿌리). JS 는 base.html 이
# 내보내는 window.CONFO.root 와 {% url %} 을 쓴다 — 절대경로를 박지 않는다.
FORCE_SCRIPT_NAME = os.environ.get("CONFOINFO_SCRIPT_NAME", "").rstrip("/") or None

CSRF_TRUSTED_ORIGINS = [
    f"http://{h}" for h in ALLOWED_HOSTS if not h.startswith("[")
]

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "conference",
]

# 로그인도 세션도 없다 — 북마크·메모는 브라우저 localStorage 에 있다.
# 운영 서버가 없다(GitHub Pages, 002). 이것은 개발 서버와 build_site 의 것이다.
MIDDLEWARE = [
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
            "conference.context.translations",
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
# 붙여 주기는 하는데 처음 읽힌 값을 캐시해, 요청 밖(build_site)이나 기동 때 먼저
# 읽히면 접두 없는 "/static/" 이 굳는다 — 실제로 CSS·JS 가 404 였다(001).
STATIC_URL = (FORCE_SCRIPT_NAME or "") + "/static/"
# build_site 가 collectstatic 을 구운 사이트 안(site/static)으로 돌린다
STATIC_ROOT = Path(os.environ.get("CONFOINFO_STATIC_ROOT", BASE_DIR / "staticfiles"))

# 해시가 붙은 파일 이름(캐시 무효화)은 구운 사이트에서만 쓴다. 개발·시험에서는
# manifest 가 없어 Manifest 저장소가 템플릿을 못 그린다.
_MANIFEST = os.environ.get("CONFOINFO_STATIC_MANIFEST", "0") == "1"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": (
        "django.contrib.staticfiles.storage.ManifestStaticFilesStorage" if _MANIFEST
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

# 미리 받아 둔 덧붙임 자료 — 저자의 대표 논문(OpenAlex) 같은 것 (006, conference/enrich.py)
ENRICH_DIR = Path(os.environ.get("CONFOINFO_ENRICH_DIR", PROJECT_ROOT / "enrich"))
