#!/usr/bin/env python3
"""STRATI 2026 의 파싱 산출물 → confoinfo 학회 자료(`conferences/strati2026.json`).

    python sources/strati2026/to_confoinfo.py

읽는 것은 `output/` 의 셋이다 — `sessions.json`(학회 사이트에서 받은 세션 제목) ·
`abstracts.json`(`parse_abstracts.py`) · `program.json`(`parse_program.py`).
PDF 에서 다시 뽑으려면 `data/` 에 원본을 두고 두 파서를 먼저 돌린다.

**학회마다 다른 것은 전부 여기서 끝낸다.** 날짜 표기(`June 29`), 룸 순서와 층,
세션 코드의 정렬 규칙(G1..G18, S1..S14)이 strati2026 의 `congress/models.py`·
`views.py` 에 흩어져 있던 것을 여기 모았다 — 뷰어는 이것을 모른다.
형식은 `docs/data-format.md`.
"""
import datetime as dt
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent.parent / "conferences" / "strati2026.json"

YEAR = 2026
MONTHS = {"June": 6, "July": 7}

# 핸드북 p28 Floor Plan. 순서가 곧 프로그램 화면의 룸 탭 순서다
# (strati2026 views.ROOM_ORDER · models.ROOM_FLOOR · short_room()).
ROOMS = [
    ("International Room I", "Int'l I", "7F"),
    ("International Room II", "Int'l II", "7F"),
    ("International Room III", "Int'l III", "7F"),
    ("Room 773", "773", "7F"),
    ("Room 775", "775", "7F"),
    ("Room 776", "776", "7F"),
]

GROUPS = {"G": "General", "S": "Special"}


def load(name):
    return json.loads((HERE / "output" / name).read_text(encoding="utf-8"))


def iso_day(label):
    month, day = label.split()
    return dt.date(YEAR, MONTHS[month], int(day)).isoformat()


def session_order(code):
    m = re.fullmatch(r"([A-Z]+)(\d+)", code)
    return (m.group(1), int(m.group(2))) if m else (code, 0)


def main():
    sessions = sorted(load("sessions.json")["sessions"],
                      key=lambda s: session_order(s["code"]))
    codes = {s["code"] for s in sessions}
    abstracts = load("abstracts.json")["abstracts"]
    talks = load("program.json")["talks"]

    # 초록집에는 있는데 사이트 콤보박스에 없던 세션(G18·S14)도 세션으로 세운다.
    # 제목은 비워 둔다 — 화면이 "(title TBD)" 를 낸다.
    for code in sorted({a["session"] for a in abstracts if a.get("session")} - codes,
                       key=session_order):
        sessions.append({"code": code, "category": code[0], "title": ""})
    sessions.sort(key=lambda s: session_order(s["code"]))

    used_rooms = {t["room"] for t in talks if t.get("room")}
    data = {
        "format": "confoinfo/1",
        "conference": {
            "slug": "strati2026",
            "short_name": "STRATI 2026",
            "name": "5th International Congress on Stratigraphy",
            "start_date": "2026-06-28",
            "end_date": "2026-07-03",
            "timezone": "Asia/Shanghai",
            "venue": "Suzhou, China",
            "url": "https://www.strati2026.org/",
            "color": "#0d3b66",
            "source": "STRATI 2026 Handbook + Abstract Volume (PDF), strati2026.org session list",
        },
        "rooms": [{"name": n, "short": s, "floor": f}
                  for n, s, f in ROOMS if n in used_rooms],
        "sessions": [{
            "code": s["code"],
            "group": GROUPS.get(s.get("category", ""), ""),
            "title": s.get("title") or "",
            "poster_count": s.get("poster_count", 0),
        } for s in sessions],
        "abstracts": [{
            "key": str(a["id"]),
            "session": a.get("session"),
            "page": a.get("page"),
            "title": a["title"],
            "text": a.get("abstract", ""),
            "keywords": a.get("keywords", []),
            "authors": [{"name": au["name"],
                         "affiliations": au.get("affil_refs", []),
                         "corresponding": bool(au.get("corresponding"))}
                        for au in a.get("authors", [])],
            "affiliations": a.get("affiliations_raw", []),
        } for a in abstracts],
        "talks": [{
            "key": str(t["id"]),
            "date": iso_day(t["date"]),
            "start": t["time_start"],
            "end": t.get("time_end"),
            "room": t.get("room"),
            "session": t.get("session"),
            "title": t["title"],
            "speaker": t.get("first_author") or "",
            "kind": t.get("kind", "talk"),
            "abstract": str(t["abstract_id"]) if t.get("abstract_id") else None,
            "page": t.get("page"),
        } for t in talks if t.get("date") and t.get("time_start")],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{OUT.relative_to(HERE.parent.parent)}: sessions {len(data['sessions'])} · "
          f"abstracts {len(data['abstracts'])} · talks {len(data['talks'])} · "
          f"rooms {len(data['rooms'])}")


if __name__ == "__main__":
    main()
