#!/usr/bin/env python3
"""ICAMG-10 E-abstract Book(PDF) → `output/abstract_book.json`.

    python sources/icamg2026/abstract_book.py      # data/e-abstract-book.pdf 를 읽는다

원본: `E-abstract Book_ICAMG_2026.pdf` — 사용자가 2026-11-03 학회 사이트(icamg.org)에서 받았다.
229쪽, InDesign, 만든 날 2026-10-30·고친 날 10-31. `data/`(gitignore)에 두고, 뽑은 것만
`output/abstract_book.json` 으로 커밋한다 — to_confoinfo.py 가 그것을 합친다(PDF 없이도 다시 돈다).

쪽의 갈래 (글꼴·크기·x 로 가른다, 009 와 같은 길):

- 18–35쪽 **구두 세션** — 쪽마다 룸(34.6pt)·날짜("Oral Presentation …")·세션 머리("Session 1A  13:00–14:30").
  x=59 의 시각 줄과 x=122 의 발표 — 저자 줄은 Bold 로 시작해 Regular 로 이어지고, 제목은 Medium.
  시각과 발표는 y 순서로 짝짓는다(저자 줄이 시각 줄보다 조금 위에 놓인다)
- 36–41쪽 **포스터 목록** — 번호 · 제목 · 발표자 · 소속, "Session 1-1" 머리
- 43–228쪽 **초록** — 한 쪽에 한 편. 오른쪽 위 표("Session 1A" · "Poster 15", 공동 세션은 표 없음),
  제목(Arial Bold 12) · 저자(6.5pt, "1*Choi, Kwang Hee; 2Hwang, …") · 소속(5pt, 앞 번호) ·
  "*Presenting Author" · 본문(10.1pt, 첫 줄 들여쓰기 = 새 문단) · 그림 설명(이탤릭)·참고문헌(7.9pt)

**본문만 가져온다** — 그림 설명·참고문헌·전자우편은 뺀다(전자우편은 사람의 연락처라 사이트에 올리지 않는다).
"""
import json
import re
from pathlib import Path

import pymupdf

HERE = Path(__file__).resolve().parent
PDF = HERE / "data" / "e-abstract-book.pdf"
OUT = HERE / "output" / "abstract_book.json"
MONTHS = {"October": 10, "November": 11}
TIME_RE = re.compile(r"^(\d{1,2}:\d{2})\s*[–-]\s*(\d{1,2}:\d{2})$")
EMAIL_RE = re.compile(r"\s*[\w.+-]+@[\w-]+(\.[\w-]+)+")


def lines(page):
    """[(x, y, 글꼴, 크기, 글)] — 줄 하나에 첫 span 의 글꼴."""
    out = []
    for b in page.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            t = "".join(s["text"] for s in l["spans"])
            if t.strip():
                s = l["spans"][0]
                out.append((l["bbox"][0], l["bbox"][1], s["font"], s["size"], t))
    return out


def join(parts):
    """줄 끝 하이픈 이음("Mid-" + "Pleistocene")은 붙이고 나머지는 띄운다. "a : b" → "a: b"."""
    s = ""
    for p in parts:
        p = p.strip()
        if not p:
            continue
        s = s + p if s.endswith("-") and not s.endswith(" -") else (s + " " + p if s else p)
    return re.sub(r"\s+:", ":", re.sub(r"\s+", " ", s)).strip()


def hm(s):
    return s.zfill(5)


def iso_day(text):                          # "Oral Presentation Monday, 2 November 2026"
    m = re.search(r"(\d{1,2}) (\w+) (\d{4})", text)
    return f"{int(m.group(3)):04d}-{MONTHS[m.group(2)]:02d}-{int(m.group(1)):02d}"


# ── 구두 세션 ────────────────────────────────────────────────────────────
def oral(doc):
    out = []
    for pno in range(len(doc)):
        ls = lines(doc[pno])
        head = [l for l in ls if l[4].strip().startswith("Session ") and 14 <= l[3] <= 15.5]
        day = [l for l in ls if l[4].startswith("Oral Presentation")]
        room = [l for l in ls if l[3] > 30 and l[4].strip().startswith("Meeting Room")]
        if not (head and day and room):
            continue
        m = re.match(r"Session (\S+)\s+(\S+)", head[0][4].strip())
        session = m.group(1)
        times = sorted([l for l in ls if abs(l[0] - 59) < 3 and TIME_RE.match(l[4].strip())], key=lambda l: l[1])
        body = sorted([l for l in ls if abs(l[0] - 122) < 3 and l[1] > 270], key=lambda l: l[1])
        entries = []
        for l in body:
            if "Bold" in l[2]:
                entries.append({"authors": [l[4]], "title": []})
            elif entries and not entries[-1]["title"] and "Medium" not in l[2]:
                entries[-1]["authors"].append(l[4])      # 저자 줄 이어짐 (Regular)
            elif entries:
                entries[-1]["title"].append(l[4])
        if len(times) != len(entries):
            raise SystemExit(f"p{pno + 1}: 시각 {len(times)} · 발표 {len(entries)} 이 안 맞는다")
        for t, e in zip(times, entries):
            s, en = TIME_RE.match(t[4].strip()).groups()
            out.append({"page": pno + 1, "date": iso_day(day[0][4]), "room": room[0][4].strip(),
                        "session": session, "start": hm(s), "end": hm(en),
                        "authors": [a.strip() for a in join(e["authors"]).split(",") if a.strip()],
                        "title": join(e["title"])})
    return out


# ── 포스터 목록 ──────────────────────────────────────────────────────────
def posters(doc):
    out = []
    for pno in range(35, 41):                         # 36–41쪽
        ls = [l for l in lines(doc[pno]) if 60 < l[1] < 780 and l[4].strip() not in ("No.", "Title", "Presenter", "Affiliation")
              and "ICAMG-10" not in l[4]]
        # 번호는 칸의 세로 가운데에 놓인다 — 제목·발표자·소속 줄은 같은 세션 안에서 y 가 가장 가까운 번호에 붙인다.
        # 열은 x 로 가른다: 번호(<90) · 제목(<330) · 발표자(<430) · 소속
        heads = sorted([(l[1], l[4].strip().split()[1]) for l in ls if l[4].strip().startswith("Session ")])
        sess_at = lambda y: ([s for hy, s in heads if hy < y] or [None])[-1]
        nums = [{"no": int(l[4].strip()), "y": l[1], "session": sess_at(l[1]), "title": [], "presenter": [], "affil": []}
                for l in ls if l[0] < 90 and l[4].strip().isdigit()]
        sess_of = {}
        for x, y, f, size, t in sorted(ls, key=lambda l: l[1]):
            t = t.strip()
            if t.startswith("Session ") or (x < 90 and t.isdigit()):
                continue
            same = [n for n in nums if n["session"] == sess_at(y)] or nums
            if not same:
                continue
            n = min(same, key=lambda n: abs(n["y"] - y))
            n["title" if x < 330 else "presenter" if x < 430 else "affil"].append(t)
        out += nums
    # 이전 쪽에서 세션 머리를 이어받는다
    last = None
    for p in out:
        p["session"] = p["session"] or last
        last = p["session"]
    for p in out:
        p["title"] = join(p["title"])
        p["presenter"] = join(p["presenter"])
        p["affil"] = join(p["affil"])
        p.pop("y")
    return out


# ── 초록 ────────────────────────────────────────────────────────────────
SUP = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹˒", "0123456789,")


def sup(s):
    """위첨자 글자(¹˒²*Yang)를 보통 숫자로."""
    return s.translate(SUP)


def split_authors(raw):
    """"1*Choi, Kwang Hee; 2Hwang, Jae Hyun" → [{name, affiliations, presenting}].
    "Surname, Given" 을 "Given Surname" 으로 돌린다. 소속 번호가 여럿이면 "1,2"."""
    out = []
    for part in [p.strip() for p in raw.split(";") if p.strip()]:
        m = re.match(r"^([\d,\s]*)(\*?)\s*([\d,\s]*)(.*)$", part)
        nums = [int(n) for n in re.findall(r"\d+", (m.group(1) or "") + (m.group(3) or ""))]
        name = m.group(4).strip().strip(",").strip()
        if "," in name:
            last, first = [x.strip() for x in name.split(",", 1)]
            name = f"{first} {last}".strip()
        out.append({"name": name, "affiliations": nums, "presenting": bool(m.group(2))})
    return out


def abstracts(doc):
    out = []
    for pno in range(42, len(doc) - 1):
        ls = lines(doc[pno])
        label = " ".join(l[4].strip() for l in ls if l[1] < 60 and l[0] > 380)
        title = [l for l in ls if "Bold" in l[2] and 11 <= l[3] <= 13 and 60 <= l[1] < 200]
        if not title:
            continue
        ty = max(l[1] for l in title)
        # 글꼴 크기는 쪽마다 다르다(저자 6.5pt 또는 10pt, 위첨자가 ¹²³ 글자이기도) — 자리로 가른다:
        # 제목과 본문 첫 줄 사이가 머리 — 첫 크기의 줄들이 저자, 더 작은 줄들이 소속.
        # 본문 첫 줄은 "*Presenting Author" 바로 다음의 본문 크기 줄, 그 표가 없으면 들여 쓴(x 65–100) 본문 크기 줄
        pres = [l for l in ls if "Presenting Author" in l[4] and l[1] > ty]
        after = pres[0][1] if pres else ty
        first = min((l for l in ls if l[1] > after and 9.5 <= l[3] <= 10.6 and not l[4].strip().isdigit()
                     and (pres or 65 < l[0] < 100)), key=lambda l: l[1], default=None)
        body_y = first[1] if first else 740
        head = sorted([l for l in ls if ty < l[1] < body_y and "Presenting Author" not in l[4]
                       and l[4].strip() and not EMAIL_RE.fullmatch(" " + l[4].strip())], key=lambda l: (l[1], l[0]))
        asize = head[0][3] if head else 0
        authors = [l for l in head if abs(l[3] - asize) < .3 and l[1] < head[0][1] + 25]
        affs = [l for l in head if l not in authors]
        body = sorted([l for l in ls if 9.5 <= l[3] <= 10.6 and "Italic" not in l[2]
                       and body_y - 1 <= l[1] < 740 and not l[4].strip().isdigit()], key=lambda l: l[1])
        paras = []
        for x, y, f, size, t in body:
            if not paras or x > 65:                    # 들여 쓴 줄 = 새 문단 (본문 칸은 x 56.6, 들여쓰기는 쪽마다 76–93)
                paras.append([t])
            else:
                paras[-1].append(t)
        affiliations = []
        for l in sorted(affs, key=lambda l: l[1]):
            t = sup(EMAIL_RE.sub("", l[4])).strip().strip(",").strip()
            if not t:
                continue
            # 한 줄에 소속이 둘("3Korea Environment Institute, 4Research Institute …")이면 번호 앞에서 가른다
            for piece in re.split(r"[,;]?\s+(?=\d{1,2}[A-Z])", t):
                m = re.match(r"^(\d+)\s*(.*)$", piece)
                if m:
                    affiliations.append((int(m.group(1)), m.group(2).strip().strip(",").strip()))
                elif affiliations:                      # 소속이 두 줄로 넘어간 것
                    n, s = affiliations[-1]
                    affiliations[-1] = (n, (s + " " + piece).strip())
        out.append({
            "page": pno + 1,
            "label": label,                             # "Session 1A" · "Poster 15" · ""(공동 세션)
            "title": join(l[4] for l in sorted(title, key=lambda l: l[1])),
            "authors": split_authors(sup(join(l[4] for l in sorted(authors, key=lambda l: (l[1], l[0]))))),
            "affiliations": [{"no": n, "text": s} for n, s in affiliations],
            "text": "\n\n".join(join(p) for p in paras),
        })
    return out


def main():
    doc = pymupdf.open(PDF)
    data = {"source": "E-abstract Book_ICAMG_2026.pdf (icamg.org, 2026-11-03 받음, PDF 만든 날 2026-10-30)",
            "oral": oral(doc), "posters": posters(doc), "abstracts": abstracts(doc)}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"구두 {len(data['oral'])} · 포스터 {len(data['posters'])} · 초록 {len(data['abstracts'])} → {OUT}")


if __name__ == "__main__":
    main()
