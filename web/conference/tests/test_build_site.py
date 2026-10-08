"""build_site 가 모든 화면을 파일로 굽고, 구운 링크가 전부 이어지는가."""
import io
import json
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase, override_settings

from conference.loader import load
from conference.models import Talk

from .base import sample


class BuildSiteTests(TestCase):
    def test_bakes_every_page_and_links_resolve(self):
        load(sample())
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            with override_settings(STATIC_ROOT=out / "static"):
                call_command("collectstatic", "--noinput", verbosity=0)
                buf = io.StringIO()
                call_command("build_site", str(out), stdout=buf)   # 깨진 링크가 있으면 SystemExit
            self.assertIn("링크 검사 통과", buf.getvalue())
            t1 = Talk.objects.get(key="t1")
            for rel in ("index.html", "404.html", ".nojekyll", "talks.json", "search.json",
                        "testconf/index.html", "testconf/day/2026-05-05/index.html",
                        "testconf/session/S1/index.html", f"testconf/talk/{t1.pk}/index.html",
                        f"testconf/talk/{t1.pk}/talk.ics", "testconf/plan/index.html",
                        "testconf/search.json"):
                self.assertTrue((out / rel).is_file(), rel)
            d = json.loads((out / "testconf/talks.json").read_text(encoding="utf-8"))
            self.assertEqual(len(d["talks"]), 7)
            # 휴식에는 캘린더 파일이 없다
            t7 = Talk.objects.get(key="t7")
            self.assertFalse((out / f"testconf/talk/{t7.pk}/talk.ics").exists())
