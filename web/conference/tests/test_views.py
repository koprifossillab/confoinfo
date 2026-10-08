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

    def test_home_groups_by_status(self):
        with mock.patch.object(timezone, "now", return_value=at(2026, 5, 4)):
            r = self.client.get("/")
        self.assertEqual([s[0] for s in r.context["sections"]], ["ongoing", "upcoming"])
        self.assertContains(r, "LIVE")
        with mock.patch.object(timezone, "now", return_value=at(2026, 9, 1)):
            r = self.client.get("/")
        self.assertEqual([s[0] for s in r.context["sections"]], ["upcoming", "past"])

    def test_program_days_rooms_breaks(self):
        r = self.client.get("/testconf/?day=2026-05-04")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["selected"], dt.date(2026, 5, 4))
        self.assertEqual([t.key for t in r.context["plenary"]], ["t5"])
        (room, items), = r.context["columns"]
        self.assertEqual(room.name, "Hall A")
        breaks = [i for k, i in items if k == "break"]
        self.assertEqual([(b["start"].strftime("%H:%M"), b["label"]) for b in breaks],
                         [("09:40", "Break"), ("12:10", "Lunch")])

    def test_program_defaults_to_venue_today(self):
        # 서울 5월 5일 00:30 = UTC 5월 4일 15:30
        with mock.patch.object(timezone, "now", return_value=at(2026, 5, 4, 15) + dt.timedelta(minutes=30)):
            r = self.client.get("/testconf/")
        self.assertEqual(r.context["selected"], dt.date(2026, 5, 5))

    def test_explicit_break_is_not_doubled(self):
        r = self.client.get("/testconf/?day=2026-05-05")
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

    def test_search(self):
        r = self.client.get("/testconf/search/", {"q": "montañez"})   # 공저자 · 비ASCII
        self.assertEqual([t.key for t in r.context["talks"]], ["t1"])
        r = self.client.get("/testconf/search/", {"q": "poster person"})
        self.assertEqual([a.key for a in r.context["abstracts"]], ["a2"])
        r = self.client.get("/search/", {"q": "Day two"})
        self.assertEqual(len(r.context["talks"]), 2)                    # 두 학회
        r = self.client.get("/testconf/search/", {"q": "Coffee"})
        self.assertEqual([t.key for t in r.context["talks"]], ["t8"])     # 휴식(t7)은 안 찾는다

    def test_api_talks_and_breaks(self):
        ids = f"{self.t['t1'].pk},{self.t['t4'].pk},999999"
        d = json.loads(self.client.get("/api/talks/", {"ids": ids}).content)
        self.assertEqual(sorted(t["title"] for t in d["talks"]), ["After lunch", "Trilobites of somewhere"])
        t1 = next(t for t in d["talks"] if t["title"].startswith("Tri"))
        self.assertEqual((t1["conf"], t1["tz"], t1["room"], t1["floor"], t1["session"]),
                         ("testconf", "Asia/Seoul", "Hall A", "1F", "S1"))
        self.assertEqual(t1["url"], f"/testconf/talk/{self.t['t1'].pk}/")
        # t4 로 이어지는 점심만 (t1 앞에는 휴식이 없다)
        self.assertEqual([(b["start"], b["end"], b["label"]) for b in d["breaks"]],
                         [("12:10", "13:00", "Lunch")])

    def test_ics_uses_venue_timezone(self):
        r = self.client.get("/calendar.ics", {"ids": f"{self.t['t1'].pk},{self.t['t7'].pk}"})
        body = r.content.decode()
        self.assertIn("DTSTART:20260504T000000Z", body)   # 서울 09:00 = UTC 00:00
        self.assertEqual(body.count("BEGIN:VEVENT"), 1)    # 휴식은 빠진다
        self.assertIn("X-WR-CALNAME:TEST 2026", body)

    def test_plan_and_settings_render(self):
        for url in ("/plan/", "/testconf/plan/", "/settings/"):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_healthz(self):
        d = json.loads(self.client.get("/healthz").content)
        self.assertEqual((d["status"], d["conferences"], d["talks"]), ("ok", 2, 16))


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
