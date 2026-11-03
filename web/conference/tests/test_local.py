"""이 기기에 반입한 학회 (P02) — 서버는 껍데기와 지침만 낸다. 읽고 검사하고 그리는 것은 local.js 다."""
import json

from django.conf import settings
from django.test import TestCase

from conference import loader
from conference.loader import load
from conference.urls import RESERVED

from .base import sample


class LocalImportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        load(sample())

    def test_import_page_knows_published_slugs(self):
        r = self.client.get("/import/")
        self.assertContains(r, 'const PUBLISHED = ["testconf"]')     # 사이트에 있는 학회는 반입하지 않는다
        self.assertContains(r, 'href="/format.txt"')
        self.assertContains(r, "conference/local.js")

    def test_local_page_is_a_shell(self):
        r = self.client.get("/local/")
        self.assertContains(r, 'id="local-root"')
        self.assertContains(r, "conference/program.js")

    def test_guide_and_schema_are_served(self):
        r = self.client.get("/format.txt")
        self.assertEqual(r["Content-Type"], "text/plain; charset=utf-8")
        self.assertContains(r, '"format": "confoinfo/1"')
        s = self.client.get("/confoinfo-1.schema.json").json()
        self.assertEqual(s["properties"]["format"]["const"], loader.FORMAT)
        # 스키마의 kind 가 모델과 같다
        self.assertEqual(s["properties"]["talks"]["items"]["properties"]["kind"]["enum"],
                         ["talk", "plenary", "keynote", "poster", "break", "event"])

    def test_reserved_slugs_match_local_js(self):
        """local.js 의 RESERVED 가 urls.RESERVED 와 같다 — 반입한 학회 slug 가 다른 화면을 가리지 않게."""
        js = (settings.BASE_DIR / "conference" / "static" / "conference" / "local.js").read_text(encoding="utf-8")
        block = js[js.index("const RESERVED"):js.index("]);", js.index("const RESERVED"))]
        names = set(json.loads("[" + block.split("[", 1)[1].replace("\n", " ") + "]"))
        self.assertEqual(names, RESERVED)

    def test_guide_example_is_valid(self):
        """지침의 최소 예시가 loader 의 검사를 통과한다 — AI 가 그대로 본뜬다."""
        text = (settings.PROJECT_ROOT / "docs" / "ai-guide.md").read_text(encoding="utf-8")
        example = text.split("## Minimal example", 1)[1].split("```json", 1)[1].split("```", 1)[0]
        errors, warnings = loader.validate(json.loads(example))
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
