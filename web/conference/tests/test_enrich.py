"""미리 받아 둔 덧붙임 자료 — 번역·대표 논문 (006)."""
import json
import tempfile
from pathlib import Path

from django.test import TestCase, override_settings

from conference import enrich, people
from conference.loader import load
from conference.models import Talk

from .base import sample


class EnrichTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        (d / "testconf.ko.json").write_text(json.dumps({"lang": "ko", "t": {
            enrich.text_key("Trilobites of somewhere"): "어딘가의 삼엽충",
            enrich.text_key("Body."): "본문.",
            enrich.text_key("First"): "첫째 세션",
        }}, ensure_ascii=False), encoding="utf-8")
        (d / "testconf.openalex.json").write_text(json.dumps({"people": {
            people.key("Kim Ex", ""): {"name": "Kim Ex", "affiliation": "",
                                       "match": {"id": "A1", "name": "Kim Ex", "hint": "Somewhere Univ",
                                                 "by": "topic"},
                                       "works": [{"title": "Old trilobite paper", "year": 2001,
                                                  "venue": "J. Paleo", "cited": 12, "url": "https://doi.org/x"}]},
        }}), encoding="utf-8")
        (d / "testconf.names.json").write_text(json.dumps({"ko": {"Kim Ex": "김엑스"}}, ensure_ascii=False),
                                               encoding="utf-8")
        self.ov = override_settings(ENRICH_DIR=d)
        self.ov.enable()
        enrich._load.cache_clear()
        load(sample())
        self.t1 = Talk.objects.get(key="t1")

    def tearDown(self):
        self.ov.disable()
        enrich._load.cache_clear()
        self.tmp.cleanup()

    def test_languages_and_translate(self):
        self.assertEqual(enrich.languages("testconf"), ["ko"])          # openalex·names 는 언어가 아니다
        self.assertEqual(enrich.translate("testconf", "Trilobites of somewhere"), {"ko": "어딘가의 삼엽충"})
        self.assertEqual(enrich.translate("testconf", "Trilobites of somewhere, revised"), {})   # 원문이 바뀌면 안 나온다

    def test_detail_bakes_translation_and_works(self):
        r = self.client.get(f"/testconf/talk/{self.t1.pk}/")
        self.assertContains(r, 'data-tr="ko" hidden>어딘가의 삼엽충</p>')
        self.assertContains(r, 'data-tr-body="ko"')
        self.assertContains(r, "본문.")
        self.assertContains(r, "Old trilobite paper")
        self.assertContains(r, "matched by name and research topic")
        self.assertContains(r, 'trLangs: ["ko"]')

    def test_i18n_json(self):
        d = self.client.get("/testconf/i18n/ko.json").json()
        self.assertEqual(d["talks"], {str(self.t1.pk): "어딘가의 삼엽충"})
        self.assertEqual(d["sessions"], {"S1": "첫째 세션"})
        self.assertEqual(self.client.get("/testconf/i18n/ja.json").status_code, 404)
        self.assertIn(str(self.t1.pk), self.client.get("/i18n/ko.json").json()["talks"])

    def test_names_json_and_setting(self):
        """사람 이름의 한글 표기 (011) — 학회를 가로질러 names.json 하나, 설정에 켜는 칸."""
        self.assertEqual(self.client.get("/names.json").json(), {"ko": {"Kim Ex": "김엑스"}})
        r = self.client.get("/settings/")
        self.assertContains(r, 'id="cfg-names"')                         # 원래 이름 · 한글 · 병기 (012)
        self.assertContains(r, 'data-v="both"')
        self.assertContains(r, '<b translate="no">TEST 2026</b>')          # 한글 표기가 있는 학회
        self.assertContains(r, 'namesUrl: "/names.json"')
