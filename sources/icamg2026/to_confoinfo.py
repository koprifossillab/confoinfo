#!/usr/bin/env python3
"""ICAMG-10 2026 (icamg.org/program) → confoinfo 학회 자료(`conferences/icamg2026.json`).

    sources/icamg2026/fetch.sh                      # raw/ 를 새로 받을 때
    python sources/icamg2026/to_confoinfo.py

읽는 것 (raw/, 2026-10-08 받음):

- `program.html` 의 표 셋 — `#programmeGridPanel`(한눈에 보는 표) ·
  `#detailedProgrammeGridPanel`(구두 발표 시간표) · `#posterPresentationsPanel`(포스터)
- `proposed-session.html` — 주제 세션(1-1 …)의 제목·좌장·소개

**구두 세션은 프로그램의 표기(1A … 7B)를 그대로 쓴다.** 그것은 시간 칸 번호이고 주제
세션(1-1 …)과 다르다 — 같은 주제가 두 칸을 쓰기도 한다(1B·2B 가 남극 I·II). 소개 글은
제목이 가장 비슷한 주제 세션에서 가져온다. 포스터는 주제 세션 번호로 묶여 있어 `P1-1`
처럼 앞에 P 를 붙인 세션으로 둔다.

**받은 날 사이트에 없던 것**: 초록 본문(E-abstract Book 이 "Coming Soon"), 층, 답사 일정의
시간. 발표마다 저자 목록은 있어 초록 행을 만들어 저자만 채운다 — 검색이 공저자로 걸리고
상세 화면이 저자를 보여 준다.
"""
import difflib
import html
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
OUT = HERE.parent.parent / "conferences" / "icamg2026.json"

YEAR = 2026
MONTHS = {"October": 10, "November": 11}
HALL = "Event Hall A, B"
POSTER_ROOM = "Seaside Hallway"
POSTER_DAY, POSTER_START, POSTER_END = "2026-11-02", "16:40", "18:00"

ROOMS = [
    (HALL, "Hall A·B"),
    ("Meeting Room 6 & 7", "Room 6·7"),
    ("Meeting Room 8 & 9", "Room 8·9"),
    ("Meeting Room 10", "Room 10"),
    (POSTER_ROOM, "Seaside"),
]


def text(fragment):
    """태그를 걷고 공백을 접는다."""
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment))
    return re.sub(r"\s+", " ", t).strip()


def spans(cell, cls):
    return [text(m) for m in re.findall(
        rf'<span class="{cls}">(.*?)</span>(?=<span|$|\s*</td>)', cell, re.S)]


def panel(src, pid):
    i = src.index(f'id="{pid}"')
    return src[i:src.index("</table>", i)]


def rows(table):
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S):
        cells = re.findall(r'<(td|th)([^>]*)>(.*?)</\1>', tr, re.S)
        yield [(re.search(r'class="([^"]*)"', a).group(1) if 'class="' in a else "",
                int(re.search(r'colspan="(\d+)"', a).group(1)) if "colspan" in a else 1,
                inner) for _, a, inner in cells]


def times(s):
    m = re.match(r"(\d{1,2}:\d{2})\s*[–~-]\s*(\d{1,2}:\d{2})", s)
    return (m.group(1).zfill(5), m.group(2).zfill(5)) if m else (None, None)


def iso_day(label):                     # "Monday, 2 November 2026"
    m = re.search(r"(\d{1,2}) (\w+) (\d{4})", label)
    return f"{int(m.group(3)):04d}-{MONTHS[m.group(2)]:02d}-{int(m.group(1)):02d}"


def theme_sessions():
    """proposed-session.html → {"1-1": {title, conveners, description, theme}}."""
    src = (RAW / "proposed-session.html").read_text(encoding="utf-8")
    out, theme = {}, ""
    for m in re.finditer(r'<div class="theme-group-label"[^>]*>(.*?)</div>|'
                         r'<div class="session-number">(.*?)</div>(.*?)(?=<div class="session-card[ "]|'
                         r'<div class="theme-group-label"|</main>|\Z)', src, re.S):
        if m.group(1):
            theme = text(m.group(1))
            continue
        body = m.group(3)
        title = re.search(r'session-card-title">(.*?)</div>', body, re.S)
        conv = re.search(r'session-conveners">(.*?)</div>', body, re.S)
        desc = re.findall(r"<p>(.*?)</p>", body, re.S)
        out[text(m.group(2))] = {
            "title": text(title.group(1)) if title else "",
            "conveners": text(conv.group(1)).removeprefix("Conveners:").removeprefix("Convener:").strip()
            if conv else "",
            # 문단 안의 <br>(항목 목록)은 줄바꿈으로 살린다 — 화면의 linebreaks 가 <br> 로 되돌린다
            "description": "\n\n".join(
                "\n".join(text(line) for line in re.split(r"<br\s*/?>", p) if text(line))
                for p in desc),
            "theme": theme,
        }
    return out


def keynotes(src):
    """한눈에 보는 표의 "Keynote: Prof. X – 제목 –" 에서 (이름, 제목). 시간표 쪽은 – 가 없다."""
    grid = text(panel(src, "programmeGridPanel"))
    return {name.strip(): title.strip() for name, title in
            re.findall(r"Keynote: (.+?) – (.+?) –", grid)}


def main():
    src = (RAW / "program.html").read_text(encoding="utf-8")
    themes = theme_sessions()
    kn = keynotes(src)

    def people(s):
        return {p.strip().lower() for p in re.split(r",| and ", s) if p.strip()}

    def best_theme(title, conveners):
        """시간표의 세션 → 주제 세션(소개 글을 가져올 곳).

        제목으로만 찾았더니 4C("Carbon cycling and subsurface CO2 storage")가 엉뚱한
        극지 세션에 붙었다 — 시간표의 제목이 주제 세션 제목과 다르게 줄어든 곳이 있다.
        좌장이 겹치는 것이 둘이면(4C 의 두 사람이 5-4 와 6-2 에 다 있다) 명단이 똑같은 것,
        그다음 겹침 수, 그다음 제목 유사도로 고른다.
        """
        mine = people(conveners)

        def score(k):
            theirs = people(themes[k]["conveners"])
            sim = difflib.SequenceMatcher(None, title.lower(), themes[k]["title"].lower()).ratio()
            return (bool(mine) and mine == theirs, len(mine & theirs), sim)
        best = max(themes, key=score, default=None)
        if best is None:
            return None
        exact, overlap, sim = score(best)
        return best if exact or overlap >= 2 or sim >= 0.6 else None

    sessions, talks, abstracts = [], [], []

    def add_talk(**t):
        # key 는 북마크가 붙는 자리다. 행 순서로 매기면 원본에 행 하나가 끼어도 뒤가 전부
        # 밀린다 — 구두는 "세션-시작시각"(1A-1300), 나머지는 "날짜-시작시각-종류"로 둔다.
        # 포스터는 보드 번호(p12)를 넘겨받는다
        if "key" not in t:
            hm = t["start"].replace(":", "")
            t["key"] = (f"{t['session']}-{hm}" if t.get("session")
                        else f"{t['date']}-{hm}-{t.get('kind', 'talk')}")
        talks.append(t)
        return t

    # ── 구두 발표 시간표 ────────────────────────────────────────────────
    day, columns, current = None, [], {}
    for row in rows(panel(src, "detailedProgrammeGridPanel")):
        classes = [c for c, _, _ in row]
        if "day-header-cell" in classes:
            day = iso_day(text(row[0][2]))
            continue
        if not classes[0] and row[0][2].strip() == "Time":           # 룸 머리줄
            columns = [text(inner) for _, _, inner in row[1:]]
            continue
        start, end = times(text(row[0][2]))
        if not start:
            continue
        rest = row[1:]
        cls, span, inner = rest[0]
        if span > 1:                                                  # 모든 룸에 걸친 줄
            main = text(re.sub(r'<span class="event-subline">.*?</span>', "", inner, flags=re.S))
            subs = [text(s) for s in re.findall(r'<span class="event-subline">(.*?)</span>', inner, re.S)]
            title = re.sub(rf"/\s*{re.escape(HALL)}$", "", main).rstrip("/ ").strip()
            title = re.sub(rf"/\s*{POSTER_ROOM}$", "", title).strip()
            if title.lower().endswith("coffee break") or title.startswith("Poster session"):
                continue      # 커피는 빈 시간에서 끌어낸다 · 포스터는 아래에서 한 장씩
            if title.startswith("Registration Desk"):
                add_talk(date=day, start=start, end=end, room=None, title=title, kind="event")
                continue
            if title.startswith("Keynote:"):
                name = next((n for n in kn if title.startswith(f"Keynote: {n}")), "")
                t = add_talk(date=day, start=start, end=end, room=HALL, kind="keynote",
                             title=kn.get(name) or title, speaker=name)
                conv = [s for s in subs if s.startswith("Convener")]
                if conv:
                    t["speaker"] = f"{name} ({conv[0]})"
                continue
            if title == "Lunch":
                add_talk(date=day, start=start, end=end, room=HALL, title="Lunch", kind="break")
                continue
            t = add_talk(date=day, start=start, end=end, room=HALL, title=title, kind="event")
            lineup = [s for s in subs if not s.startswith("Convener")]
            if lineup:
                # 공동 세션의 연사 목록 — 따로 시간이 없어 한 행으로 두고 초록 칸에 적는다
                # 발표자 이름은 "이름 (소속): 제목" 의 앞토막
                t["speaker"] = ", ".join(re.split(r"\s*\(", x)[0] for x in lineup if "TBD" not in x)
                t["abstract"] = t["key"]
                abstracts.append({"key": t["key"], "title": title, "text": "\n\n".join(subs)})
            continue
        for col, (cls, _, inner) in enumerate(rest):
            room = columns[col] if col < len(columns) else None
            if cls == "session-cell":
                code = text(re.search(r'session-code">(.*?)</span>', inner, re.S).group(1)).removeprefix("Session ").strip()
                title = text(re.search(r'session-title">(.*?)</span>', inner, re.S).group(1))
                conv = re.search(r'session-convener">(.*?)</span>', inner, re.S)
                convs = (text(conv.group(1)).split(":", 1)[-1].strip().replace(" and ", ", ")
                         if conv else "")
                th = themes.get(best_theme(title, convs) or "", {})
                sessions.append({
                    "code": code, "group": "Oral sessions", "title": title,
                    "conveners": convs or th.get("conveners", ""),
                    "description": th.get("description", ""),
                })
                current[col] = code
            elif cls == "talk-cell":
                authors = text(re.search(r'talk-authors">(.*?)</span>', inner, re.S).group(1))
                title = text(re.search(r'talk-title">(.*?)</span>', inner, re.S).group(1))
                names = [a.strip() for a in authors.split(",") if a.strip()]
                t = add_talk(date=day, start=start, end=end, room=room, session=current.get(col),
                             title=title, speaker=names[0] if names else "")
                t["abstract"] = t["key"]
                abstracts.append({"key": t["key"], "session": current.get(col), "title": title,
                                  "authors": [{"name": n} for n in names]})

    # ── 포스터 ──────────────────────────────────────────────────────────
    poster_session = None
    for row in rows(panel(src, "posterPresentationsPanel")):
        cls, _, inner = row[0]
        if "poster-session-cell" in cls:
            num = text(inner).removeprefix("Session ").strip()     # "1-1"
            th = themes.get(num, {})
            poster_session = f"P{num}"
            sessions.append({"code": poster_session, "group": "Poster sessions",
                             "title": th.get("title", ""), "conveners": th.get("conveners", ""),
                             "description": th.get("description", "")})
            continue
        if cls != "poster-no-cell":
            continue
        no, title, presenter, affil = (text(c[2]) for c in row[:4])
        key = f"p{no}"
        add_talk(key=key, code=f"P{no}", date=POSTER_DAY, start=POSTER_START, end=POSTER_END,
                 room=POSTER_ROOM, session=poster_session, title=title, speaker=presenter,
                 kind="poster", abstract=key)
        abstracts.append({"key": key, "session": poster_session, "title": title,
                          "authors": [{"name": presenter, "affiliations": [1]}],
                          "affiliations": [affil] if affil else []})

    data = {
        "format": "confoinfo/1",
        "conference": {
            "slug": "icamg2026",
            "short_name": "ICAMG 2026",
            "name": "The 10th International Conference on Asian Marine Geology (ICAMG-10)",
            "start_date": "2026-10-30",
            "end_date": "2026-11-07",
            "timezone": "Asia/Seoul",
            "venue": "BPEX, Busan, Korea",
            "url": "https://icamg.org/program",
            "color": "#1a3a4d",
            "lunch_at": "12:00",
            "source": "icamg.org/program · proposed-session (2026-10-08 받음)",
        },
        "rooms": [{"name": n, "short": s} for n, s in ROOMS],
        "sessions": sessions,
        "abstracts": abstracts,
        "talks": talks,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    kinds = {}
    for t in talks:
        kinds[t.get("kind", "talk")] = kinds.get(t.get("kind", "talk"), 0) + 1
    print(f"{OUT.relative_to(HERE.parent.parent)}: 세션 {len(sessions)} · 발표 {len(talks)} {kinds} · "
          f"초록 {len(abstracts)}")


if __name__ == "__main__":
    main()
