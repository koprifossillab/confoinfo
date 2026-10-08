from django.test import SimpleTestCase, TestCase

from conference import changelog


class ChangelogTests(SimpleTestCase):
    def test_parse_table(self):
        text = """# CHANGELOG

| 판 | 날짜 | 무엇 |
|---|---|---|
| 0.4.0 | 2026-10-08 | 번역 `code` · **굵게** · <script> ([004](devlog/x.md)) |
| — | 2026-10-07 | 판 없음 |
"""
        notes = changelog.parse(text)
        self.assertEqual([(n["version"], n["date"]) for n in notes], [("0.4.0", "2026-10-08"), ("", "2026-10-07")])
        h = notes[0]["html"]
        self.assertIn("<code>code</code>", h)
        self.assertIn("<b>굵게</b>", h)
        self.assertIn("&lt;script&gt;", h)          # 이스케이프
        self.assertIn("(004)", h)                    # 링크는 글자만
        self.assertNotIn("devlog", h)


class SettingsPageTests(TestCase):
    def test_shows_release_notes_from_repo(self):
        r = self.client.get("/settings/")
        self.assertContains(r, "Release notes")
        self.assertContains(r, "v0.1.0")             # 저장소의 CHANGELOG.md
        self.assertContains(r, 'data-look="theme"')
        self.assertContains(r, 'data-look="font"')
