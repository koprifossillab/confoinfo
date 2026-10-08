import datetime as dt
import json
from unittest import mock

from django.test import TestCase, override_settings
from django.urls import clear_script_prefix, reverse, set_script_prefix
from django.utils import timezone

from conference.loader import load
from conference.models import Conference, Talk
from conference.views import derive_breaks

from .base import sample


def at(y, m, d, h=10):
    return dt.datetime(y, m, d, h, tzinfo=dt.timezone.utc)


class ViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        load(sample())
        load(sample(slug="later", short_name="LATER 2027", name="Later",
                    start_date="2027-01-10", end_date="2027-01-11"))
        cls.t = {t.key: t for t in Talk.objects.filter(conference__slug="testconf")}

    def test_home_lists_cards_with_dates(self):
        r = self.client.get("/")
        # 진행 중·지난 갈래는 JS 가 가른다 — 서버는 시작일 순으로 카드만
        self.assertEqual([c.slug for c in r.context["confs"]], ["testconf", "later"])
        self.assertContains(r, 'data-start="2026-05-04" data-end="2026-05-05"')
        self.assertContains(r, 'data-tz="Asia/Seoul"')

    def test_program_days_rooms_breaks(self):
        r = self.client.get("/testconf/day/2026-05-04/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["selected"], dt.date(2026, 5, 4))
        self.assertEqual([t.key for t in r.context["plenary"]], ["t5"])
        (room, items), = r.context["columns"]
        self.assertEqual(room.name, "Hall A")
        breaks = [i for k, i in items if k == "break"]
        self.assertEqual([(b["start"].strftime("%H:%M"), b["label"]) for b in breaks],
                         [("09:40", "Break"), ("12:10", "Lunch")])

    def test_program_root_is_first_day_and_independent_of_now(self):
        # 구운 사이트에서 같은 파일이 나와야 한다 — 오늘을 고르는 것은 JS 다
        with mock.patch.object(timezone, "now", return_value=at(2026, 5, 5)):
            r = self.client.get("/testconf/")
        self.assertEqual(r.context["selected"], dt.date(2026, 5, 4))
        self.assertContains(r, '"2026-05-05": "/testconf/day/2026-05-05/"')
        self.assertContains(r, 'href="/testconf/day/2026-05-05/"')

    def test_program_bad_day_404(self):
        self.assertEqual(self.client.get("/testconf/day/2026-05-09/").status_code, 404)
        self.assertEqual(self.client.get("/testconf/day/nope/").status_code, 404)

    def test_explicit_break_is_not_doubled(self):
        r = self.client.get("/testconf/day/2026-05-05/")
        (room, items), = r.context["columns"]
        self.assertEqual([(k, i["label"] if k == "break" else i.key) for k, i in items],
                         [("talk", "t6"), ("break", "Coffee"), ("talk", "t8")])
        self.assertNotContains(r, 'data-id="%d" aria-label="bookmark"' % self.t["t7"].pk)

    def test_program_without_talks(self):
        Talk.objects.filter(conference__slug="later").delete()
        r = self.client.get("/later/")
        self.assertContains(r, "No timetable")

    def test_unknown_conference_404(self):
        self.assertEqual(self.client.get("/nope/").status_code, 404)
        self.assertEqual(self.client.get(f"/later/talk/{self.t['t1'].pk}/").status_code, 404)

    def test_sessions_and_detail(self):
        r = self.client.get("/testconf/sessions/")
        self.assertEqual([[s.code for s in items] for g, items in r.context["groups"]], [["S2", "S1"]])
        r = self.client.get("/testconf/session/S2/")
        self.assertEqual([a.key for a in r.context["extra"]], ["a2"])
        self.assertEqual([t.key for t in r.context["talks"]], ["t6", "t8"])

    def test_talk_and_abstract_detail(self):
        r = self.client.get(f"/testconf/talk/{self.t['t1'].pk}/")
        self.assertContains(r, "Isabel Montañez")
        self.assertContains(r, "Corresponding: Kim Ex")
        a2 = self.t["t1"].conference.abstracts.get(key="a2")
        r = self.client.get(f"/testconf/abstract/{a2.pk}/")
        self.assertContains(r, "A poster only abstract")

    def test_search_index(self):
        d = json.loads(self.client.get("/testconf/search.json").content)
        by_title = {t["title"]: t for t in d["talks"]}
        self.assertNotIn("Coffee", by_title)                        # 휴식은 안 찾는다
        self.assertIn("Montañez", by_title["Trilobites of somewhere"]["x"])   # 공저자
        self.assertIn("First", by_title["Trilobites of somewhere"]["x"])      # 세션 제목
        self.assertEqual([a["title"] for a in d["abstracts"]], ["A poster only abstract"])
        d = json.loads(self.client.get("/search.json").content)
        self.assertEqual({t["conf"] for t in d["talks"]}, {"testconf", "later"})

    def test_talks_json_and_breaks(self):
        d = json.loads(self.client.get("/testconf/talks.json").content)
        self.assertEqual(len(d["talks"]), 7)                        # 휴식(t7)은 북마크할 수 없다
        t1 = next(t for t in d["talks"] if t["title"].startswith("Tri"))
        self.assertEqual((t1["conf"], t1["tz"], t1["room"], t1["floor"], t1["session"]),
                         ("testconf", "Asia/Seoul", "Hall A", "1F", "S1"))
        self.assertEqual(t1["url"], f"/testconf/talk/{self.t['t1'].pk}/")
        got = sorted((b["date"], b["start"], b["end"], b["label"]) for b in d["breaks"])
        self.assertEqual(got, [("2026-05-04", "09:40", "11:50", "Break"),
                               ("2026-05-04", "12:10", "13:00", "Lunch"),
                               ("2026-05-05", "09:20", "09:40", "Coffee")])   # 적힌 휴식도
        d = json.loads(self.client.get("/talks.json").content)
        self.assertEqual(len(d["talks"]), 14)

    def test_talk_ics_uses_venue_timezone(self):
        r = self.client.get(f"/testconf/talk/{self.t['t1'].pk}/talk.ics")
        body = r.content.decode()
        self.assertIn("DTSTART:20260504T000000Z", body)   # 서울 09:00 = UTC 00:00
        self.assertIn("X-WR-CALNAME:TEST 2026", body)
        self.assertEqual(self.client.get(f"/testconf/talk/{self.t['t7'].pk}/talk.ics").status_code, 404)

    def test_pages_render(self):
        for url in ("/search/", "/testconf/search/", "/plan/", "/testconf/plan/", "/settings/",
                    "/testconf/sessions/"):
            self.assertEqual(self.client.get(url).status_code, 200, url)
        self.assertEqual(self.client.get("/404.html").status_code, 404)


class SubpathTests(TestCase):
    """nginx 서브경로(/confoinfo/) 아래에서 링크·JS 뿌리가 맞는가."""

    @classmethod
    def setUpTestData(cls):
        load(sample())

    def test_links_carry_prefix(self):
        set_script_prefix("/confoinfo/")
        try:
            self.assertEqual(reverse("program", args=["testconf"]), "/confoinfo/testconf/")
            r = self.client.get("/testconf/", SCRIPT_NAME="/confoinfo")
            self.assertContains(r, 'root: "/confoinfo/"')
            self.assertContains(r, 'href="/confoinfo/testconf/sessions/"')
        finally:
            clear_script_prefix()


class DeriveBreaksTests(TestCase):
    def test_short_gap_is_not_a_break(self):
        class T:
            def __init__(self, s, e):
                self.start, self.end = dt.time(*s), dt.time(*e)
        items = [T((9, 0), (9, 20)), T((9, 25), (9, 40)), T((10, 0), (10, 20))]
        out = derive_breaks(items, dt.time(12, 30))
        self.assertEqual([(b["start"], b["end"]) for b in out], [(dt.time(9, 40), dt.time(10, 0))])


class StaticUnderSubpathTests(TestCase):
    """STATIC_URL 이 서브경로를 달고 있는가 — 상대경로로 두면 기동 때 캐시된 값이 접두를 잃는다."""

    def test_static_url_has_prefix(self):
        import importlib
        import os
        from unittest import mock as m
        import confoinfoweb.settings as st
        with m.patch.dict(os.environ, {"CONFOINFO_SCRIPT_NAME": "/confoinfo/"}):
            fresh = importlib.reload(st)
            self.assertEqual(fresh.STATIC_URL, "/confoinfo/static/")
        importlib.reload(st)
