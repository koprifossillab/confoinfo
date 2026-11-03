"""E-abstract Book(2026-11-03 받음)을 사이트판(10-08) 자료 위에 얹는다 — to_confoinfo.py 가 부른다.

읽는 것은 `output/abstract_book.json`(abstract_book.py 가 PDF 에서 뽑은 것)이다. PDF 가 나중 판이라
겹치는 것은 PDF 를 따른다.

**key 는 바꾸지 않는다.** 북마크가 key 에 붙어 있다. 구두 key 는 사이트판의 "세션-시각"(1A-1300)이라
PDF 에서 시각이 옮겨진 발표는 key 와 시각이 어긋난다 — 그래도 둔다. 발표는 제목으로 짝짓는다
(세션 안 순서가 바뀐 것이 많다: 1A·4B·6A). 포스터도 번호가 밀렸다(16번이 빠지고 뒤가 하나씩 당겨짐) —
제목으로 짝짓고 key(p17)는 두고 번호(code)만 새것(P16)으로.

- 사이트판에만 있는 구두·포스터는 **취소로 보고 뺀다**(초록도). PDF 에만 있는 것은 새 key 로 더한다
- 초록 본문·소속은 PDF 에서. **저자 이름은 사이트판(=프로그램 표기)을 둔다** — PDF 의 저자 줄은 원고 그대로라
  꼴이 제각각이고(쉼표·세미콜론·위첨자), 이름 한글 표기(enrich/icamg2026.names.json)의 열쇠가 프로그램 표기다.
  소속 번호는 성이 맞는 저자에게만 붙인다
- 공동 세션(World Ocean Forum)의 초록 셋은 붙일 발표가 없어 넣지 않는다(시간이 따로 없는 한 행이다)
- 한눈에 보는 표(PDF 11–13쪽)에서 바뀐 행사 시각은 아래 EVENT_FIXES 에 손으로 적었다
"""
import difflib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
BOOK = HERE / "output" / "abstract_book.json"

# PDF 11–13쪽 "한눈에 보는 표" — 사이트판과 달라진 것 (key: 고칠 칸)
EVENT_FIXES = {
    "2026-11-04-0800-event": {"end": "15:00"},           # 등록 08:00–16:00 → 15:00
    "2026-11-04-1450-event": {"end": "17:00"},           # 폐회 14:50–15:00 → 17:00
}
EVENT_ADD = [  # 사이트판에 없던 것
    {"key": "2026-11-01-1730-event", "date": "2026-11-01", "start": "17:30", "end": "19:30",
     "room": None, "title": "Icebreaker (12F Rooftop Lounge, Hound Hotel)", "kind": "event"},
]


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def sim(a, b):
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def match(items, cands, key_a, key_b, floor):
    """제목 유사도가 높은 쌍부터 하나씩 짝짓는다 → {items 의 번호: cands 의 번호}."""
    pairs = sorted(((sim(key_a(a), key_b(c)), i, j) for i, a in enumerate(items) for j, c in enumerate(cands)),
                   reverse=True)
    out, used = {}, set()
    for r, i, j in pairs:
        if r < floor:
            break
        if i not in out and j not in used:
            out[i] = j
            used.add(j)
    return out


def surname(name):
    parts = re.split(r"[\s.]+", name.strip())
    return norm(parts[-1]) if parts else ""


def apply(data, log=print):
    if not BOOK.exists():
        return data
    book = json.loads(BOOK.read_text(encoding="utf-8"))
    talks, abstracts = data["talks"], data["abstracts"]
    ab_of = {a["key"]: a for a in abstracts}
    sessions = {s["code"] for s in data["sessions"]}
    removed = []

    # ── 구두 ─────────────────────────────────────────────────────────────
    oral = [t for t in talks if t.get("kind", "talk") == "talk"]
    m = match(book["oral"], oral, lambda o: o["title"], lambda t: t["title"], 0.8)
    for i, o in enumerate(book["oral"]):
        if i in m:
            t = oral[m[i]]
            moved = (t["date"], t["start"], t["room"], t.get("session")) != (o["date"], o["start"], o["room"], o["session"])
            if moved:
                log(f"  옮김 {t['key']}: {t.get('session')} {t['date']} {t['start']} → {o['session']} {o['date']} {o['start']}")
        else:
            key = f"{o['session']}-{o['start'].replace(':', '')}"
            while any(x["key"] == key for x in talks):
                key += "b"
            t = {"key": key, "abstract": key}
            talks.append(t)
            abstracts.append({"key": key})
            ab_of[key] = abstracts[-1]
            log(f"  새 구두 {key}: {o['title'][:60]}")
        t.update({"date": o["date"], "start": o["start"], "end": o["end"], "room": o["room"],
                  "session": o["session"], "title": o["title"], "speaker": o["authors"][0] if o["authors"] else ""})
        a = ab_of[t["abstract"]]
        a.update({"session": o["session"], "title": o["title"]})
        a["authors"] = [{"name": n} for n in o["authors"]]
    gone = [oral[j] for j in range(len(oral)) if j not in m.values()]
    for t in gone:
        removed.append(t)
        log(f"  취소(PDF 에 없음) {t['key']}: {t['title'][:60]}")

    # ── 포스터 ───────────────────────────────────────────────────────────
    posters = [t for t in talks if t.get("kind") == "poster"]
    m = match(book["posters"], posters, lambda p: p["title"], lambda t: t["title"], 0.8)
    proto = posters[0] if posters else {}
    for i, p in enumerate(book["posters"]):
        sess = f"P{p['session']}"
        if i in m:
            t = posters[m[i]]
            if t["code"] != f"P{p['no']}":
                log(f"  포스터 번호 {t['key']}: {t['code']} → P{p['no']}")
        else:
            key = f"p{p['no']}"
            while any(x["key"] == key for x in talks):
                key += "b"
            t = {"key": key, "abstract": key, "kind": "poster", "date": proto.get("date"), "start": proto.get("start"),
                 "end": proto.get("end"), "room": proto.get("room")}
            talks.append(t)
            abstracts.append({"key": key})
            ab_of[key] = abstracts[-1]
            log(f"  새 포스터 {key}: {p['title'][:60]}")
        t.update({"code": f"P{p['no']}", "session": sess, "title": p["title"], "speaker": p["presenter"]})
        ab_of[t["abstract"]].update({"session": sess, "title": p["title"],
                                     "authors": [{"name": p["presenter"], "affiliations": [1]}],
                                     "affiliations": [p["affil"]] if p["affil"] else []})
        if sess not in sessions:
            data["sessions"].append({"code": sess, "group": "Poster sessions", "title": ""})
            sessions.add(sess)
    for j, t in enumerate(posters):
        if j not in m.values():
            removed.append(t)
            log(f"  취소(PDF 에 없음) {t['key']} {t['code']}: {t['title'][:60]}")

    # 뺀다 — 발표와 그 초록
    gone_keys = {t["key"] for t in removed}
    gone_abs = {t.get("abstract") for t in removed}
    data["talks"] = talks = [t for t in talks if t["key"] not in gone_keys]
    data["abstracts"] = abstracts = [a for a in abstracts if a["key"] not in gone_abs]
    ab_of = {a["key"]: a for a in abstracts}

    # ── 행사 (한눈에 보는 표) ────────────────────────────────────────────
    for t in talks:
        if t["key"] in EVENT_FIXES:
            t.update(EVENT_FIXES[t["key"]])
    for e in EVENT_ADD:
        if not any(t["key"] == e["key"] for t in talks):
            talks.append(dict(e))

    # ── 초록 본문·소속 ───────────────────────────────────────────────────
    # 기조강연은 초록 행이 없었다 — 발표 key 로 만든다
    for t in talks:
        if t.get("kind") == "keynote" and not t.get("abstract"):
            t["abstract"] = t["key"]
            abstracts.append({"key": t["key"], "title": t["title"],
                              "authors": [{"name": re.split(r"\s*\(", t.get("speaker", ""))[0]
                                           .removeprefix("Prof. ").removeprefix("Dr. ")}]})
    ab_of = {a["key"]: a for a in abstracts}
    linked = [a for a in abstracts if any(t.get("abstract") == a["key"] and t.get("kind", "talk") in ("talk", "poster", "keynote")
                                         for t in talks)]
    pdf = [x for x in book["abstracts"] if x["label"]]                 # 표 없는 셋 = 공동 세션
    m = match(pdf, linked, lambda x: x["title"], lambda a: a["title"], 0.75)
    # 두 번째 길: 초록 쪽 제목에만 부제가 붙은 것("AI-assisted … architecture ‘‘to support …’’") —
    # 프로그램 제목이 초록 제목의 앞머리면 짝짓는다
    used = set(m.values())
    for i, x in enumerate(pdf):
        if i in m:
            continue
        for j, a in enumerate(linked):
            if j not in used and len(norm(a["title"])) > 30 and norm(x["title"]).startswith(norm(a["title"])):
                m[i] = j
                used.add(j)
                break
    filled = 0
    for i, x in enumerate(pdf):
        if i not in m:
            log(f"  초록 짝 없음 p{x['page']} [{x['label']}] {x['title'][:60]}")
            continue
        a = linked[m[i]]
        a["text"] = x["text"]
        nums = sorted({f["no"] for f in x["affiliations"]})
        texts = {f["no"]: f["text"] for f in x["affiliations"]}
        if nums:
            a["affiliations"] = [texts[n] for n in nums]
            pos = {n: k + 1 for k, n in enumerate(nums)}               # PDF 번호 → 목록 자리(1부터)
            by_sur = {}
            for au in x["authors"]:
                by_sur.setdefault(surname(au["name"]), au)
            for au in a.get("authors") or []:
                hit = by_sur.get(surname(au["name"]))
                if hit and hit["affiliations"]:
                    au["affiliations"] = [pos[n] for n in hit["affiliations"] if n in pos]
                elif "affiliations" in au and a.get("affiliations") and len(a["affiliations"]) == 1:
                    au["affiliations"] = [1]
                else:
                    au.pop("affiliations", None)
        filled += 1
    log(f"  초록 본문 {filled}/{len(pdf)} · 공동 세션 {len(book['abstracts']) - len(pdf)}편은 넣지 않음")

    data["conference"]["source"] = (data["conference"]["source"]
                                    + " · E-abstract Book PDF (2026-11-03 받음 — 일정·초록 본문)")
    return data
