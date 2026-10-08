from django.test import TestCase

from conference.loader import load, stable_id, validate
from conference.models import Abstract, Conference, Room, Session, Talk

from .base import sample


class ValidateTests(TestCase):
    def test_sample_is_clean(self):
        self.assertEqual(validate(sample()), ([], []))

    def test_errors(self):
        d = sample(slug="Bad Slug", timezone="Mars/Olympus")
        d["format"] = "other"
        d["talks"][0]["start"] = "9am"
        d["talks"][1]["key"] = "t1"
        d["talks"][2]["abstract"] = "nope"
        d["talks"][3]["kind"] = "party"
        errors, _ = validate(d)
        joined = "\n".join(errors)
        for needle in ("format", "slug", "timezone", "start", "겹친다", "nope", "party"):
            self.assertIn(needle, joined)

    def test_reserved_slug(self):
        errors, _ = validate(sample(slug="search"))
        self.assertTrue(any("경로" in e for e in errors))

    def test_unknown_room_and_session_are_warnings(self):
        d = sample()
        d["talks"][0]["room"] = "Hall Z"
        d["talks"][0]["session"] = "S9"
        errors, warnings = validate(d)
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 2)


class LoadTests(TestCase):
    def test_counts_and_links(self):
        s = load(sample())
        self.assertTrue(s["created"])
        self.assertEqual((s["rooms"], s["sessions"], s["abstracts"], s["talks"], s["linked"]),
                         (2, 2, 2, 8, 1))
        conf = Conference.objects.get(slug="testconf")
        self.assertEqual(conf.tz.key, "Asia/Seoul")
        t1 = Talk.objects.get(key="t1")
        self.assertEqual((t1.room.name, t1.session.code, t1.abstract.key), ("Hall A", "S1", "a1"))
        # 자료 파일의 순서가 곧 순서다 (이름순 아님)
        self.assertEqual([r.name for r in conf.rooms.all()], ["Hall B", "Hall A"])
        self.assertEqual([s.code for s in conf.sessions.all()], ["S2", "S1"])
        self.assertIn("Montañez", Abstract.objects.get(key="a1").search_text)

    def test_reload_keeps_pk_and_prunes(self):
        load(sample())
        pk = Talk.objects.get(key="t2").pk
        d = sample()
        d["talks"] = [t for t in d["talks"] if t["key"] != "t1"]
        d["talks"][0]["title"] = "Second talk (renamed)"
        d["abstracts"] = d["abstracts"][1:]
        s = load(d)
        self.assertFalse(s["created"])
        self.assertEqual(s["removed"], 2)                   # t1 · a1
        t2 = Talk.objects.get(key="t2")
        self.assertEqual(t2.pk, pk)                         # 북마크가 붙은 pk 가 그대로
        self.assertEqual(t2.title, "Second talk (renamed)")
        self.assertFalse(Talk.objects.filter(key="t1").exists())

    def test_pk_does_not_depend_on_load_order(self):
        # 구운 사이트는 빌드마다 빈 DB 에 읽는다 — 앞에 학회가 하나 끼어도 pk 가 같아야 한다 (003)
        load(sample())
        alone = Talk.objects.get(conference__slug="testconf", key="t2").pk
        Conference.objects.all().delete()
        load(sample(slug="aaa", short_name="AAA"))
        load(sample())
        self.assertEqual(Talk.objects.get(conference__slug="testconf", key="t2").pk, alone)
        self.assertEqual(alone, stable_id("testconf", "t2"))
        self.assertLess(alone, 2 ** 53)                     # JS Number 로 정확하다

    def test_two_conferences_same_keys(self):
        load(sample())
        load(sample(slug="other", short_name="OTHER"))
        self.assertEqual(Talk.objects.filter(key="t1").count(), 2)
        self.assertEqual(Conference.objects.count(), 2)

    def test_missing_room_is_appended(self):
        d = sample()
        d["talks"][0]["room"] = "Hall Z"
        load(d)
        self.assertEqual([r.name for r in Room.objects.order_by("order")],
                         ["Hall B", "Hall A", "Hall Z"])

    def test_unknown_session_becomes_null(self):
        d = sample()
        d["talks"][0]["session"] = "S9"
        load(d)
        self.assertIsNone(Talk.objects.get(key="t1").session)
        self.assertEqual(Session.objects.count(), 2)
