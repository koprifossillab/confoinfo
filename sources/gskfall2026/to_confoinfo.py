#!/usr/bin/env python3
"""2026 추계지질과학연합학술대회 프로그램북 PDF → confoinfo 학회 자료(`conferences/gskfall2026.json`).

    python sources/gskfall2026/to_confoinfo.py

원본은 `data/programbook.pdf`(gitignore) — `2026 추계_프로그램북_(공지용).pdf`, 2026-10-08
InDesign 출력, 83쪽. NAS 의 `N:\\GSM\\temp\\` 에서 받았다(2026-10-12).

**쪽의 글자를 글꼴로 가른다.** 프로그램북은 InDesign 틀 하나로 짜여 줄마다 역할이 글꼴·크기·
x 로 정해져 있다:

| 역할 | 글꼴 | x |
|---|---|---|
| 날짜 머리 `10. 27.화` | AppleSDGothicNeo-Heavy 20pt | 57 |
| 세션 머리 `G10: 지구물리학 …` (둘째 줄은 YDIYGO360) | AppleSDGothicNeo-ExtraBold 13.3pt | 62 |
| 발표장 `제1발표장` | YDIYGO360 11.6pt | 421 |
| 좌장·사회·위원 | AppleSDGothicNeo-Regular 8.4pt | 437 |
| 시각 `13:00-13:15` · 포스터 번호 `P001` | NotoSansCJKkr | 58 |
| 제목 | YDIYGO350(한글) · AppleSDGothicNeo-Bold(영문) | 123 (포스터 95) |
| 저자·꼬리표(`휴식`·`패널토론`) | HakgyoansimBareondotum(한글) · AppleSDGothicNeo-Light(영문) | 123 (포스터 95) |

x 500 넘는 쪽 옆 띠(`구두발표 / 10. 30.수` — 지난해 틀의 날짜가 남아 있다)와 y 680 아래 쪽번호는 버린다.

**`*` 는 발표자가 아니다** — `Seonghyun Kim, Yongjae Yu*` 처럼 지도교수 한 사람이 포스터 셋에
붙는다. 교신저자로 읽는다. 발표자는 프로그램북에 없어 `speaker` 는 제1저자로 둔다(형식의 관례).
초록 본문이 없다 — ICAMG 처럼 저자만 채운 초록 행을 만들어 공저자로 검색이 걸리게 한다.

**세션 머리에 둘이 묶인 것**(`G08: … / G12: …`, `W02: … / F02: …`)은 그 아래 좌장 줄이
새로 나올 때마다 다음 세션으로 넘긴다 — 쪽 28 은 G08 두 편 뒤 좌장 줄이 다시 나오고 G12 다.

**`key` 는 발표장·날짜·시작 시각**(`1027-r1-1300`), 포스터는 번호(`P001`·`Y001`)다. 행 순서로
매기지 않는다 — 다음 판 프로그램북에서 발표 하나가 빠져도 다른 발표의 북마크가 안 밀린다.
"""
import json
import re
from pathlib import Path

import pymupdf

HERE = Path(__file__).resolve().parent
PDF = HERE / "data" / "programbook.pdf"
OUT = HERE.parent.parent / "conferences" / "gskfall2026.json"

YEAR = 2026
ROOMS = [  # 쪽 3 의 한눈에 보는 표 — 1F 컨퍼런스홀, B1 세미나실
    {"name": "제1발표장", "short": "제1 · 컨퍼런스홀", "floor": "1F"},
    *({"name": f"제{i}발표장", "short": f"제{i} · 세미나실 {i - 1}", "floor": "B1"} for i in range(2, 9)),
    {"name": "포스터 발표장", "short": "포스터 · 로비", "floor": "1~2F 로비"},
]
POSTER_ROOM = "포스터 발표장"
POSTER_PAGE = 66                     # 포스터 목록이 시작하는 쪽
# 세션 머리에 줄여 적힌 것 — 쪽 5 의 이름으로
TITLES = {"W02": "단기강좌: 암석의 미시세계에서 이해하는 지구의 역사",
          "F02": "여성분과 멘토링 프로그램"}
GROUPS = {"G": "일반세션", "S": "특별세션", "F": "심포지엄 · 분과 · 협약식",
          "W": "워크숍 · 단기강좌", "Y": "차세대 지질과학자"}

TIME_RE = re.compile(r"^(\d{1,2}:\d{2})\s*[-~]\s*(\d{1,2}:\d{2})")
DATE_RE = re.compile(r"^(\d{1,2})\.\s*(\d{1,2})\.")
SESS_RE = re.compile(r"([GSFWY]\d{2}):\s*")
CODE_RE = re.compile(r"^([PY]\d{3})$")
CHAIR_RE = re.compile(r"^(좌장|사회|위원)\s*:\s*(.+)")
TITLE_FONTS = ("YDIYGO350", "AppleSDGothicNeo-Bold")
SKIP = {"휴식", "중식", "중식 및 휴식"}
# 발표장마다 같은 줄이 되풀이되는 전체 행사 — 룸 없이 한 번만 낸다
# 제목 글꼴로 찍혔지만 발표가 아닌 것 — 저자 대신 맡은 사람·기관이 적혀 있다
EVENT_TITLE = re.compile(r"분과총회$|^인사말|워크숍$|단기강좌$|토의$")
ALL_HANDS = ("개회식 및 특별강연", "기조강연", "특별강연", "정기총회", "간친회",
             "네트워킹 리셉션", "포스터발표 평가")


def lines_of(page):
    out = []
    for b in page.get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            t = "".join(s["text"] for s in ln["spans"]).replace("\u3000", " ").strip()
            x, y = ln["bbox"][0], ln["bbox"][1]
            if not t or x > 500 or y > 680:
                continue
            s = ln["spans"][0]
            out.append({"x": x, "y": y, "size": s["size"], "font": s["font"], "t": t})
    # 같은 줄이 겹쳐 찍힌 것(쪽 52 의 날짜 머리)을 지운다
    seen, uniq = set(), []
    for ln in out:
        k = (round(ln["x"]), round(ln["y"]), ln["t"])
        if k not in seen:
            seen.add(k)
            uniq.append(ln)
    # y 가 3pt 안인 것을 한 행으로 보고 x 로 정렬한다. 자간을 벌려 쪼개진 글자(쪽 39 의 `축` `사 (…)`)는
    # 같은 행에서 붙인다
    rows = []
    for ln in sorted(uniq, key=lambda l: l["y"]):
        if rows and ln["y"] - rows[-1][0]["y"] <= 3:
            rows[-1].append(ln)
        else:
            rows.append([ln])
    lines = []
    for row in rows:
        row.sort(key=lambda l: l["x"])
        for ln in row:
            prev = lines[-1] if lines else None
            if prev and prev is not None and prev.get("_row") is row and len(prev["t"]) == 1 \
                    and prev["font"] == ln["font"]:
                prev["t"] += ln["t"]
                continue
            ln["_row"] = row
            lines.append(ln)
    return lines


def role(ln):
    f, s, x = ln["font"], ln["size"], ln["x"]
    if "Heavy" in f and s > 19:
        return "date"
    if "ExtraBo" in f and s > 13:
        return "session"
    if f.startswith("YDIYGO360") and x > 400:
        return "room"
    if f.startswith("YDIYGO360") and x < 100:
        return "session2"            # 세션 머리의 둘째 줄
    if x > 400 and CHAIR_RE.match(ln["t"]):
        return "chair"
    if f.startswith("NotoSansCJK") and x < 90:
        return "code" if CODE_RE.match(ln["t"]) else ("time" if TIME_RE.match(ln["t"]) else "label")
    if any(f.startswith(p) for p in TITLE_FONTS) and s >= 9:
        return "title"
    return "small"                   # 저자·꼬리표


def join_lines(parts):
    """줄바꿈된 제목을 잇는다 — 영문은 띄어 잇고, 하이픈으로 끊긴 낱말은 붙인다."""
    out = ""
    for p in parts:
        p = p.strip()
        if not out:
            out = p
        elif out.endswith("-") and re.match(r"[a-z]", p):
            out += p
        else:
            out += " " + p
    return re.sub(r"\s+", " ", out).strip()


def split_authors(s):
    names = [a.strip() for a in re.split(r",\s*", s) if a.strip()]
    return [{"name": a.rstrip("*").strip(), **({"corresponding": True} if a.endswith("*") else {})}
            for a in names]


def parse():
    doc = pymupdf.open(PDF)
    sessions = {}        # code → {code, group, title, conveners}
    items = []           # 시간 칸 또는 포스터 하나
    date = None
    head = []            # 지금 세션 머리의 코드들
    head_i = 0
    room = None
    chairs_seen = 0
    cur = None

    def flush():
        nonlocal cur
        if cur:
            items.append(cur)
        cur = None

    for pno in range(10, doc.page_count + 1):
        lines = lines_of(doc[pno - 1])
        if not any(role(ln) in ("time", "code") for ln in lines):
            continue                 # 장 표지·빈 쪽
        for ln in lines:
            r, t = role(ln), ln["t"]
            if r == "date":
                m = DATE_RE.match(t)
                if not m:            # 장 표지(`구두발표` 큰 글씨)
                    continue
                date = f"{YEAR}-{int(m[1]):02d}-{int(m[2]):02d}"
                continue
            if r == "session":
                flush()
                head = []
                for part in re.split(r"\s+/\s+(?=[GSFWY]\d{2}:)", t):
                    m = SESS_RE.match(part)
                    code, title = m[1], part[m.end():].strip()
                    head.append(code)
                    sessions.setdefault(code, {"code": code, "group": GROUPS[code[0]], "title": title,
                                               "conveners": [], "page": pno})
                head_i, chairs_seen = 0, 0
                continue
            if r == "session2" and t.startswith("차세대 지질과학자"):
                flush()
                head, head_i = ["Y01"], 0
                continue
            if r == "session2":
                sessions[head[-1]]["title"] += " " + t
                continue
            if r == "room":
                room = t
                continue
            if r == "chair" and pno >= POSTER_PAGE:
                continue             # 포스터 쪽의 좌장은 평가 위원이다 — 세션 좌장에 섞지 않는다
            if r == "chair":
                flush()
                chairs_seen += 1
                if len(head) > 1 and chairs_seen > 1 and head_i < len(head) - 1:
                    head_i += 1
                who = CHAIR_RE.match(t)[2].strip()
                conv = sessions[head[head_i]]["conveners"]
                if who not in conv:
                    conv.append(who)
                continue
            if r == "label" and t in ("고등부", "대학부"):
                continue
            if r in ("time", "code"):
                flush()
                cur = {"page": pno, "date": date, "room": room,
                       "session": head[head_i] if head else None, "label": [], "title": [], "who": []}
                if r == "time":
                    m = TIME_RE.match(t)
                    cur["start"], cur["end"] = f"{int(m[1][:-3]):02d}{m[1][-3:]}", f"{int(m[2][:-3]):02d}{m[2][-3:]}"
                else:
                    cur["code"] = t
                    if t.startswith("Y"):
                        cur["session"] = "Y01"
                continue
            if cur is None:
                continue
            if r == "title":
                if cur["who"]:           # 한 칸에 제목이 둘(쪽 38 협약식) — 저자 뒤 새 제목
                    cur.setdefault("more", []).append((cur["title"], cur["who"]))
                    cur["title"], cur["who"] = [], []
                cur["title"].append(t)
            elif not cur["title"]:
                cur["label"].append(t)
            else:
                cur["who"].append(t)
    flush()
    return sessions, items


def main():
    sessions, items = parse()
    sessions.setdefault("Y01", {"code": "Y01", "group": GROUPS["Y"], "title": "차세대 지질과학자 프로그램",
                                "conveners": [], "page": 82})
    talks, abstracts, seen_events = [], [], set()
    poster_count = {}

    for it in items:
        label = " ".join(it["label"])
        if it.get("code"):                               # 포스터
            title = join_lines(it["title"])
            authors = split_authors(join_lines(it["who"]))
            key = it["code"]
            poster_count[it["session"]] = poster_count.get(it["session"], 0) + 1
            abstracts.append({"key": key, "session": it["session"], "title": title, "authors": authors})
            talks.append({"key": key, "code": key, "date": "2026-10-29", "start": "13:30", "end": "14:00",
                          "room": POSTER_ROOM, "session": it["session"], "title": title,
                          "speaker": authors[0]["name"] if authors else "", "kind": "poster",
                          "abstract": key, "page": it["page"]})
            continue
        if not it["title"]:
            if label in SKIP or not label:
                continue
            title, who = label, ""
        else:
            parts = it.get("more", []) + [(it["title"], it["who"])]
            title = " · ".join(join_lines(t) for t, _ in parts)
            who = join_lines(sum((w for _, w in parts), []))

        event = not it["title"] or bool(label) or it.get("more") or EVENT_TITLE.search(title)
        all_hands = any(a in label or a in title for a in ALL_HANDS)
        if all_hands:
            k = (it["date"], it["start"], title[:12])
            if k in seen_events:
                continue
            seen_events.add(k)
        if event:
            kind = "plenary" if "특별강연" in label else "keynote" if "기조강연" in label else "event"
            t = {"key": f"{it['date'][5:].replace('-', '')}-{it['start'].replace(':', '')}-"
                        f"{'all' if all_hands else 'r' + it['room'][1]}-{kind}",
                 "date": it["date"], "start": it["start"], "end": it["end"],
                 "room": "제1발표장" if kind != "event" else (None if all_hands else it["room"]),
                 "session": None if all_hands else it["session"],
                 "title": f"{label}: {title}" if it["title"] and label and kind == "event" else title,
                 "kind": kind, "page": it["page"]}
            if who:
                t["speaker"] = who.replace("*", "")
            if t["title"] == "포스터발표 평가(1~2F 로비)":
                t["title"], t["room"] = "포스터발표 평가", POSTER_ROOM
            talks.append(t)
            continue

        authors = split_authors(join_lines(it["who"]))
        key = f"{it['date'][5:].replace('-', '')}-r{it['room'][1]}-{it['start'].replace(':', '')}"
        abstracts.append({"key": key, "session": it["session"], "title": title, "authors": authors})
        talks.append({"key": key, "date": it["date"], "start": it["start"], "end": it["end"],
                      "room": it["room"], "session": it["session"], "title": title,
                      "speaker": authors[0]["name"] if authors else "", "kind": "talk",
                      "abstract": key, "page": it["page"]})

    # 프로그램 쪽에 시각이 없는 것 — 쪽 2 의 주요일정
    talks += [
        {"key": "1027-1000-all-event", "date": "2026-10-27", "start": "10:00", "end": "18:00",
         "room": None, "title": "등록 · 포스터 부착 시작", "kind": "event", "page": 2},
        {"key": "1030-0700-all-event", "date": "2026-10-30", "start": "07:00", "end": "16:00",
         "room": None, "title": "야외지질답사: 여수 사도·낭도의 지질과 공룡발자국화석",
         "speaker": "가이드: 박정웅, 신승원, 전용문, 김민국", "kind": "event", "page": 2},
    ]

    order = {c: i for i, c in enumerate("GSFWY")}
    sess = []
    for s in sorted(sessions.values(), key=lambda s: (order[s["code"][0]], s["code"])):
        row = {"code": s["code"], "group": s["group"], "title": TITLES.get(s["code"], s["title"]).strip()}
        if s["conveners"]:
            row["conveners"] = ", ".join(s["conveners"])
        if poster_count.get(s["code"]):
            row["poster_count"] = poster_count[s["code"]]
        sess.append(row)

    keys = [t["key"] for t in talks]
    dup = {k for k in keys if keys.count(k) > 1}
    assert not dup, dup

    data = {
        "format": "confoinfo/1",
        "conference": {
            "slug": "gskfall2026",
            "short_name": "2026 추계지질과학연합",
            "name": "2026 추계지질과학연합학술대회 및 대한지질학회 제81차 정기총회",
            "start_date": "2026-10-27",
            "end_date": "2026-10-30",
            "timezone": "Asia/Seoul",
            "language": "ko",
            "venue": "여수엑스포컨벤션센터",
            "url": "https://www.gskorea.or.kr/",
            "color": "#1f4e5f",
            "lunch_at": "12:00",
            "source": "프로그램북(공지용) PDF, 2026-10-08 판 — sources/gskfall2026/to_confoinfo.py",
        },
        "rooms": ROOMS,
        "sessions": sess,
        "abstracts": abstracts,
        "talks": sorted(talks, key=lambda t: (t["date"], t["start"], t["room"] or "", t["key"])),
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    kinds = {}
    for t in talks:
        kinds[t["kind"]] = kinds.get(t["kind"], 0) + 1
    print(f"{OUT.name}: 세션 {len(sess)} · 발표 {len(talks)} {kinds} · 초록(저자만) {len(abstracts)}")


if __name__ == "__main__":
    main()
