"""시험의 공통 자료. 저장소의 자료 파일 없이도 돌게 스스로 만든다."""
import copy

SAMPLE = {
    "format": "confoinfo/1",
    "conference": {
        "slug": "testconf", "short_name": "TEST 2026", "name": "Test Conference",
        "start_date": "2026-05-04", "end_date": "2026-05-05",
        "timezone": "Asia/Seoul", "venue": "Seoul", "lunch_at": "12:00",
    },
    "rooms": [{"name": "Hall B", "short": "B", "floor": "2F"},
              {"name": "Hall A", "short": "A", "floor": "1F"}],
    "sessions": [{"code": "S2", "group": "Oral", "title": "Second"},
                 {"code": "S1", "group": "Oral", "title": "First"}],
    "abstracts": [
        {"key": "a1", "session": "S1", "title": "Trilobites of somewhere",
         "text": "Body.", "keywords": ["trilobite"],
         "authors": [{"name": "Kim Ex", "corresponding": True}, {"name": "Isabel Montañez"}]},
        {"key": "a2", "session": "S2", "title": "A poster only abstract",
         "authors": [{"name": "Poster Person"}]},
    ],
    "talks": [
        {"key": "t1", "date": "2026-05-04", "start": "09:00", "end": "09:20",
         "room": "Hall A", "session": "S1", "title": "Trilobites of somewhere",
         "speaker": "Kim Ex", "abstract": "a1"},
        {"key": "t2", "date": "2026-05-04", "start": "09:20", "end": "09:40",
         "room": "Hall A", "session": "S1", "title": "Second talk", "speaker": "Lee"},
        {"key": "t3", "date": "2026-05-04", "start": "11:50", "end": "12:10",
         "room": "Hall A", "session": "S1", "title": "Before lunch", "speaker": "Park"},
        {"key": "t4", "date": "2026-05-04", "start": "13:00", "end": "13:20",
         "room": "Hall A", "session": "S1", "title": "After lunch", "speaker": "Choi"},
        {"key": "t5", "date": "2026-05-04", "start": "08:30", "end": "09:00",
         "room": None, "title": "Opening keynote", "speaker": "Keynote Person", "kind": "keynote"},
        {"key": "t6", "date": "2026-05-05", "start": "09:00", "end": "09:20",
         "room": "Hall B", "session": "S2", "title": "Day two", "speaker": "Yoon"},
        {"key": "t7", "date": "2026-05-05", "start": "09:20", "end": "09:40",
         "room": "Hall B", "title": "Coffee", "kind": "break"},
        {"key": "t8", "date": "2026-05-05", "start": "09:40", "end": "10:00",
         "room": "Hall B", "session": "S2", "title": "After coffee", "speaker": "Han"},
    ],
}


def sample(**conf):
    d = copy.deepcopy(SAMPLE)
    d["conference"].update(conf)
    return d
