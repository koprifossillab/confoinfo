#!/usr/bin/env python3
"""STRATI 2026 핸드북 학술 프로그램(p7-25) → output/program.json.

각 페이지는 좌/우 2단, 각 단은 독립된 (날짜·룸·세션) 헤더를 가짐.
일반 세션 컬럼: Time | Session | Title | First Author
개회/기조(p7) 컬럼: Time | Title | Speakers

발표(talk) 레코드: {date, room, session, time_start, time_end, title,
                    first_author, kind, page}
타임테이블 기능을 위해 초록(title/first_author)과 연결되는 시간·장소 정보.

strati2026 4972d35 scripts/parse_program.py 에서 왔다. 경로(ROOT)만 바꿨다.
"""
import difflib
import json
import re
from pathlib import Path

import pymupdf

# confoinfo: 이 디렉토리가 뿌리다 (strati2026 에서는 scripts/ 의 부모였다)
ROOT = Path(__file__).resolve().parent
PDF = ROOT / "data" / "strati2026_handbook.pdf"
ABSTRACTS = ROOT / "output" / "abstracts.json"
OUT = ROOT / "output" / "program.json"

PROGRAM_PAGES = range(7, 26)   # 1-indexed p7..p25
MID_X = 635
TIME_RE = re.compile(r"(\d{1,2}:\d{2})-(\d{1,2}:\d{2})")
DATE_RE = re.compile(r"(June|July)\s+\d+")
ROOM_RE = re.compile(r"\(([^)]+)\)")
SESS_RE = re.compile(r"[GS]\d+")
SKIP_TITLE = re.compile(r"\b(break|lunch|coffee|photo|opening|closing|"
                        r"ceremony|guests?|introduction|formal)\b", re.I)
# decoy(시간앵커 없는 구분행) 감지용 — 실제 발표 제목 오탐을 줄이려 좁게.
BREAK_RE = re.compile(r"\b(break|lunch|coffee|tea)\b", re.I)


def words_of(page):
    # (x0,y0,x1,y1,text)
    return [w[:5] for w in page.get_text("words") if w[4].strip()]


def find_header_y(side_words):
    for w in side_words:
        if w[4] == "Time":
            return w[1]
    return None


def col_bounds(side_words, header_y, side_x1):
    """헤더 단어 위치로 컬럼 x경계 산출."""
    h = {w[4]: w[0] for w in side_words if abs(w[1] - header_y) < 4}
    time_x = h.get("Time", side_words[0][0])
    title_x = h.get("Title")
    sess_x = h.get("Session")
    auth_x = h.get("First", h.get("Speakers"))
    return {
        "time": (time_x - 2, (sess_x or title_x) - 2),
        "session": (sess_x - 2, title_x - 2) if sess_x else None,
        "title": (title_x - 2, auth_x - 2),
        "author": (auth_x - 2, side_x1 + 2),
    }


def in_range(x, rng):
    return rng is not None and rng[0] <= x < rng[1]


FOOTER_Y = 775


def collect_col(side_words, rng, y_top):
    """컬럼 영역 단어를 (y, x, text)로 반환."""
    out = []
    for x0, y0, x1, y1, t in side_words:
        if y_top < y0 < FOOTER_Y and in_range(x0, rng):
            out.append((y0, x0, t))
    out.sort(key=lambda r: (round(r[0]), r[1]))
    return out


def assign_by_anchor(words, anchors_y, decoy_ys=()):
    """각 단어를 y기준 '가장 가까운' 앵커에 귀속(centroid).
    decoy_ys(브레이크 줄 등)에 가까운 단어는 흡수 후 폐기 → 인접 talk 제목 오염 방지."""
    combined = [(ay, i) for i, ay in enumerate(anchors_y)] + [(d, None) for d in decoy_ys]
    groups = {i: [] for i in range(len(anchors_y))}
    for y, x, t in words:
        _, idx = min(combined, key=lambda c: abs(c[0] - y))
        if idx is not None:
            groups[idx].append((y, x, t))
    return groups


def detect_break_ys(words):
    """제목 컬럼에서 Break/Lunch/Coffee 줄의 y 위치(시간앵커 없는 구분행)."""
    from collections import defaultdict
    byline = defaultdict(list)
    for y, x, t in words:
        byline[round(y)].append((x, t))
    ys = []
    for yy, ws in byline.items():
        line = " ".join(t for _, t in sorted(ws))
        if BREAK_RE.search(line):
            ys.append(float(yy))
    return ys


def join_words(group):
    group.sort(key=lambda r: (round(r[0] / 4), r[1]))
    s = re.sub(r"\s+", " ", " ".join(t for _, _, t in group)).strip()
    s = re.sub(r"(\w)-\s+(\w)", r"\1\2", s)   # 줄바꿈 하이픈 분절 복원
    return s


def parse_side(side_words, side_x1, page_no):
    header_y = find_header_y(side_words)
    if header_y is None:
        return None, []
    # 헤더(날짜/룸/세션): header_y 위쪽
    head_txt = join_words([(y, x, t) for x, y, x1, y1, t in side_words
                           if y < header_y - 3])
    dm = DATE_RE.search(head_txt)
    rm = ROOM_RE.search(head_txt)
    date = dm.group(0) if dm else None
    room = rm.group(1).strip() if rm else None
    before_room = head_txt.split("Session")[0] if "Session" in head_txt else head_txt
    head_sessions = SESS_RE.findall(before_room)
    kind = "plenary" if ("Plenary" in head_txt or "Ceremony" in head_txt) else "talk"

    bounds = col_bounds(side_words, header_y, side_x1)
    time_words = [(y, x, t) for x, y, x1, y1, t in side_words
                  if in_range(x, bounds["time"]) and y > header_y]
    anchors = []
    for y, x, t in sorted(time_words):
        m = TIME_RE.search(t)
        if m:
            anchors.append((y, m.group(1), m.group(2)))
    anchors_y = [a[0] for a in anchors]
    if not anchors:
        return {"date": date, "room": room}, []

    title_col = collect_col(side_words, bounds["title"], header_y)
    titles = assign_by_anchor(title_col, anchors_y, detect_break_ys(title_col))
    authors = assign_by_anchor(collect_col(side_words, bounds["author"], header_y), anchors_y)
    sessions = assign_by_anchor(collect_col(side_words, bounds["session"], header_y), anchors_y) \
        if bounds["session"] else {}

    talks = []
    for i, (y, ts, te) in enumerate(anchors):
        title = join_words(titles.get(i, []))
        if not title or SKIP_TITLE.search(title):
            continue
        author = join_words(authors.get(i, []))
        sess_cell = join_words(sessions.get(i, [])) if sessions else ""
        sess = (SESS_RE.findall(sess_cell) or head_sessions or [None])[0]
        talks.append({
            "date": date, "room": room, "session": sess,
            "time_start": ts, "time_end": te,
            "title": title, "first_author": author or None,
            "kind": kind, "page": page_no,
        })
    return {"date": date, "room": room}, talks


def _norm(s):
    s = s.lower().replace("–", "-").replace("—", "-").replace("’", "'")
    return re.sub(r"[^a-z0-9]", "", s)


def link_abstracts(talks):
    """talk → abstract_id 연결: 정규화 정확매칭 후 동일세션 내 퍼지 폴백."""
    abstracts = json.loads(ABSTRACTS.read_text(encoding="utf-8"))["abstracts"]
    exact = {}
    by_sess = {}
    for a in abstracts:
        exact.setdefault(_norm(a["title"]), a["id"])
        by_sess.setdefault(a["session"], []).append((_norm(a["title"]), a["id"]))
    n_exact = n_fuzzy = 0
    for t in talks:
        t["abstract_id"] = None
        if t["kind"] == "plenary":
            continue
        n = _norm(t["title"])
        if n in exact:
            t["abstract_id"] = exact[n]
            n_exact += 1
            continue
        best, score = None, 0.0
        for an, aid in by_sess.get(t["session"], []):
            r = difflib.SequenceMatcher(None, n, an).ratio()
            if r > score:
                best, score = aid, r
        if best and score >= 0.90:
            t["abstract_id"] = best
            t["link_fuzzy"] = round(score, 3)
            n_fuzzy += 1
            continue
        # 접두사 매칭: 저자명이 제목칸에 번지거나(초록⊂talk) talk제목이 잘린 경우(talk⊂초록)
        for an, aid in by_sess.get(t["session"], []):
            short, long = sorted((n, an), key=len)
            if len(short) >= 25 and long.startswith(short):
                t["abstract_id"] = aid
                t["link_fuzzy"] = "prefix"
                n_fuzzy += 1
                break
    linked = sum(1 for t in talks if t["abstract_id"])
    nonp = sum(1 for t in talks if t["kind"] != "plenary")
    print(f"linked {linked}/{nonp} (exact={n_exact} fuzzy={n_fuzzy})")


def main():
    doc = pymupdf.open(PDF)
    all_talks = []
    for p in PROGRAM_PAGES:
        page = doc[p - 1]
        ws = words_of(page)
        left = [w for w in ws if w[0] < MID_X]
        right = [w for w in ws if w[0] >= MID_X]
        _, lt = parse_side(left, MID_X, p)
        _, rt = parse_side(right, doc[p - 1].rect.width, p)
        all_talks.extend(lt)
        all_talks.extend(rt)
    doc.close()

    for i, t in enumerate(all_talks, 1):
        t["id"] = i

    link_abstracts(all_talks)

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({"count": len(all_talks), "talks": all_talks},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"parsed {len(all_talks)} talks -> {OUT}")

    from collections import Counter
    print("by date:", dict(Counter(t["date"] for t in all_talks)))
    print("by room:", dict(Counter(t["room"] for t in all_talks)))
    print("by session:", dict(sorted(Counter(t["session"] for t in all_talks).items(),
                                      key=lambda kv: str(kv[0]))))
    print("no_author:", sum(1 for t in all_talks if not t["first_author"]))
    print("no_session:", sum(1 for t in all_talks if not t["session"]))


if __name__ == "__main__":
    main()
