"""화면을 전부 파일로 구워 정적 사이트를 만든다 (GitHub Pages, 002).

    tools/build_site.sh                     # 보통은 이것 — 임시 DB · collectstatic · 이것 · 링크 검사
    python web/manage.py build_site OUT     # DB 가 이미 차 있고 collectstatic 이 끝났을 때

Django 시험 클라이언트로 경로마다 GET 해서 응답을 그대로 적는다. 화면 코드는 개발
서버와 하나다 — 그래서 **뷰는 요청과 무관해야 한다**(views.py 머리말). 슬래시로
끝나는 경로는 `…/index.html`, 아니면 그 이름의 파일이 된다.

끝에 구운 HTML 의 href·src 를 전부 따라가 파일이 있는지 본다. 하나라도 없으면 실패로
끝낸다 — Pages 에 올라간 뒤 404 로 알게 되는 것보다 빌드에서 멈추는 것이 낫다.
"""
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.test import Client
from django.urls import reverse

from conference.models import Conference

LINK_RE = re.compile(r'(?:href|src)="([^"#]+)"')


def _paths():
    """구울 경로 전부 (reverse 가 서브경로를 단 것)."""
    yield reverse("home")
    yield reverse("search_all")
    yield reverse("plan_all")
    yield reverse("settings")
    yield reverse("talks_all")
    yield reverse("search_index_all")
    yield reverse("not_found")
    for c in Conference.objects.all():
        s = c.slug
        yield reverse("program", args=[s])
        for d in c.talks.order_by("date").values_list("date", flat=True).distinct():
            yield reverse("program_day", args=[s, d.isoformat()])
        yield reverse("sessions", args=[s])
        for code in c.sessions.values_list("code", flat=True):
            yield reverse("session_detail", args=[s, code])
        for pk, kind in c.talks.values_list("pk", "kind"):
            yield reverse("talk_detail", args=[s, pk])
            if kind != "break":
                yield reverse("talk_ics", args=[s, pk])
        for pk in c.abstracts.values_list("pk", flat=True):
            yield reverse("abstract_detail", args=[s, pk])
        yield reverse("search", args=[s])
        yield reverse("plan", args=[s])
        yield reverse("talks", args=[s])
        yield reverse("search_index", args=[s])


class Command(BaseCommand):
    help = "화면을 전부 파일로 굽는다 (GitHub Pages)."

    def add_arguments(self, parser):
        parser.add_argument("out", help="구운 사이트를 둘 디렉토리 (STATIC_ROOT 가 그 안의 static/ 이어야 한다)")

    def handle(self, *args, **opts):
        out = Path(opts["out"]).resolve()
        prefix = settings.FORCE_SCRIPT_NAME or ""
        client = Client(HTTP_HOST="localhost")
        n = 0
        for url in _paths():
            assert url.startswith(prefix + "/"), url
            rel = unquote(url[len(prefix) + 1:])
            # 시험 클라이언트는 SCRIPT_NAME 을 떼고 경로를 받는다 (nginx 가 하던 일과 같다)
            resp = client.get("/" + rel)
            if resp.status_code != (404 if rel == "404.html" else 200):
                raise CommandError(f"{url} → {resp.status_code}")
            dest = out / (rel + "index.html" if rel == "" or rel.endswith("/") else rel)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(resp.content)
            n += 1
        # 밑줄로 시작하는 경로를 Jekyll 이 숨기지 않게
        (out / ".nojekyll").write_text("")
        self.stdout.write(f"{n}개 파일을 {out} 에 구웠다")

        missing = self._check_links(out, prefix)
        if missing:
            for page, link in missing[:30]:
                self.stderr.write(f"  ✗ {page}: {link}")
            self.stderr.write(f"깨진 링크 {len(missing)}개")
            sys.exit(1)
        self.stdout.write("링크 검사 통과")

    def _check_links(self, out, prefix):
        missing, seen = [], {}
        for page in out.rglob("*.html"):
            for link in LINK_RE.findall(page.read_text(encoding="utf-8")):
                parts = urlsplit(link)
                if parts.scheme or parts.netloc or not parts.path.startswith(prefix + "/"):
                    continue          # 바깥 링크 · 학회 사이트
                rel = unquote(parts.path[len(prefix) + 1:])
                if rel not in seen:
                    target = out / rel
                    seen[rel] = target.is_file() or (target / "index.html").is_file()
                if not seen[rel]:
                    missing.append((page.relative_to(out), link))
        return missing
