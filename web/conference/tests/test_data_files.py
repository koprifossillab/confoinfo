"""저장소의 자료 파일이 전부 검사를 통과하고 읽혀 들어가는가."""
import json

from django.conf import settings
from django.test import TestCase

from conference.loader import load, validate
from conference.models import Conference


class DataFileTests(TestCase):
    def test_every_file_validates_and_loads(self):
        files = sorted(settings.CONFERENCES_DIR.glob("*.json"))
        self.assertTrue(files, "conferences/ 가 비었다")
        for path in files:
            with self.subTest(path.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                errors, _ = validate(data)
                self.assertEqual(errors, [])
                self.assertEqual(path.stem, data["conference"]["slug"])   # 파일 이름 = slug
                load(data)
        self.assertEqual(Conference.objects.count(), len(files))

    def test_strati2026_counts(self):
        path = settings.CONFERENCES_DIR / "strati2026.json"
        s = load(json.loads(path.read_text(encoding="utf-8")))
        self.assertEqual((s["rooms"], s["sessions"], s["abstracts"], s["talks"]), (6, 30, 607, 457))
