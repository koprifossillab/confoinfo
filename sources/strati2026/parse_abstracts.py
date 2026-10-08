#!/usr/bin/env python3
"""STRATI 2026 초록집(abstract_volume.pdf) → output/abstracts.json 파서.

폰트/크기/위치 기반 구조 인식:
  - 러닝헤더(y<82)/푸터(size~9)는 제거하되, 헤더에서 세션코드(Session GX)만 추출
  - 제목      : size >= 13 (bold)  — 여러 줄 + 줄 안의 작은 글리프(en-dash 등) 포함
  - 헤딩      : bold size ~11, "Abstract" / "Key words"
  - 저자명    : size ~11 regular   (Abstract 이전)
  - 저자 상첨자: superscript flag   (소속번호 / '*' = 교신저자)
  - 소속      : italic  (상세 매핑 없이 원문만 보관)
  - 본문      : Abstract~Key words 사이 텍스트
  - 구분자 페이지의 "Session GX"(size 26)는 세션만 갱신하고 버림

PyMuPDF span flags: 1=superscript, 2=italic, 4=serif, 8=mono, 16=bold

strati2026 4972d35 scripts/parse_abstracts.py 에서 왔다. 경로(ROOT)만 바꿨다.
"""
import json
import re
from collections import Counter
from pathlib import Path

import pymupdf

# confoinfo: 이 디렉토리가 뿌리다 (strati2026 에서는 scripts/ 의 부모였다)
ROOT = Path(__file__).resolve().parent
PDF = ROOT / "data" / "strati2026_abstract_volume.pdf"
OUT = ROOT / "output" / "abstracts.json"

SESSION_RE = re.compile(r"Session\s+([GS]\d+)")
DIVIDER_RE = re.compile(r"^Session\s+[GS]\d+\s*$")
HEADER_Y = 82      # 이보다 위는 러닝헤더
FOOTER_Y = 770     # 이보다 아래의 size~9 는 푸터 페이지번호


def tokenize(doc):
    tokens = []
    for pno in range(doc.page_count):
        page = doc[pno]
        d = page.get_text("dict")
        session = None
        lines = []
        for b in d["blocks"]:
            for l in b.get("lines", []):
                spans = [s for s in l["spans"] if s["text"].strip()]
                if spans:
                    lines.append((round(l["bbox"][1], 1), l["bbox"][0], spans))
        lines.sort(key=lambda t: (t[0], t[1]))
        page_tokens = []
        for y, _, spans in lines:
            for s in spans:
                sz = s["size"]
                if y < HEADER_Y:                       # 러닝헤더
                    m = SESSION_RE.search(s["text"])
                    if m:
                        session = m.group(1)
                    continue
                if y > FOOTER_Y and 8.0 <= sz <= 9.7:  # 푸터 페이지번호
                    continue
                page_tokens.append({
                    "page": pno + 1,
                    "size": sz,
                    "bold": bool(s["flags"] & 16),
                    "italic": bool(s["flags"] & 2),
                    "super": bool(s["flags"] & 1),
                    "text": s["text"],
                })
        for t in page_tokens:
            t["session"] = session
        tokens.extend(page_tokens)
    return tokens


def classify(t):
    # 헤더/푸터는 tokenize 에서 y좌표로 제거됨. 여기서는 size 기반 skip 없음
    # (일부 초록은 헤딩/본문 전체가 9.5pt 등 작게 식자되어 있어 size skip 금지)
    sz = t["size"]
    if sz >= 13:
        return "title"
    if t["bold"]:
        low = t["text"].strip().lower().replace(" ", "")
        if low.startswith("abstract"):
            return "abstract_head"
        if low.startswith("keyword"):
            return "keyword_head"
        if sz >= 10:
            return "head_other"   # 제목 안 인라인 글리프 또는 기타 볼드
    if t["italic"]:
        return "affil"
    return "text"


def parse_authors(spans):
    authors = []
    cur = ""
    has_super = False
    for sp in spans:
        if sp["super"]:
            has_super = True
            name = cur.strip().lstrip(",").strip()
            refs = sp["text"].strip()
            if name:
                authors.append({
                    "name": name.replace("*", "").strip(),
                    "affil_refs": [int(n) for n in re.findall(r"\d+", refs)],
                    "corresponding": "*" in refs,
                })
            cur = ""
        else:
            cur += sp["text"]
    tail = cur.strip().lstrip(",").strip()
    if tail:
        if not has_super:
            for nm in re.split(r",\s*", tail):
                nm = nm.strip()
                if nm:
                    authors.append({"name": nm.replace("*", "").strip(),
                                    "affil_refs": [], "corresponding": "*" in nm})
        else:
            authors.append({"name": tail.replace("*", "").strip(),
                            "affil_refs": [], "corresponding": "*" in tail})
    return authors


def build_abstracts(tokens):
    abstracts = []
    cur = None
    state = None
    parts = {}

    def reset():
        return {"title": [], "authors": [], "affil": [], "body": [], "kw": []}

    def flush():
        if cur is None:
            return
        title = re.sub(r"\s+", " ", "".join(parts["title"])).strip()
        if DIVIDER_RE.match(title):          # 구분자 페이지 → 버림
            return
        cur["title"] = title
        cur["authors"] = parse_authors(parts["authors"])
        cur["affiliations_raw"] = [re.sub(r"\s+", " ", a).strip()
                                   for a in parts["affil"] if a.strip()]
        cur["abstract"] = re.sub(r"[ \t]+", " ", "".join(parts["body"])).strip()
        kw_raw = re.sub(r"\s+", " ", "".join(parts["kw"])).strip()
        cur["keywords_raw"] = kw_raw
        cur["keywords"] = [k.strip() for k in re.split(r"[,;]", kw_raw) if k.strip()]
        abstracts.append(cur)

    for t in tokens:
        kind = classify(t)
        if kind == "skip":
            continue
        if kind == "title":
            if cur is not None and state != "title":
                flush()
                cur = None
            elif cur is not None and state == "title":
                pending = re.sub(r"\s+", " ", "".join(parts["title"])).strip()
                if DIVIDER_RE.match(pending):     # 직전이 구분자였으면 폐기
                    cur = None
            if cur is None:
                cur = {"session": t["session"], "page": t["page"]}
                parts = reset()
                state = "title"
            parts["title"].append(t["text"])
            if t["session"]:
                cur["session"] = t["session"]
            continue
        if cur is None:
            continue
        if kind == "abstract_head":
            state = "abstract"
            continue
        if kind == "keyword_head":
            state = "keywords"
            continue
        if state == "title":
            # 제목 줄 안의 작은 글리프(볼드 en-dash, 아래/위첨자 CO2·δ13C 등) 흡수
            if kind == "head_other" or t["size"] < 10.5:
                parts["title"].append(t["text"])
                continue
            state = "authors"                 # 첫 11pt 본문성 토큰 → 저자 단계
        if kind == "head_other":
            continue
        if state == "authors":
            if kind == "affil":
                parts["affil"].append(t["text"])
            else:
                parts["authors"].append(t)
        elif state == "abstract":
            parts["body"].append(t["text"])
        elif state == "keywords":
            parts["kw"].append(t["text"])

    flush()
    return abstracts


def main():
    doc = pymupdf.open(PDF)
    tokens = tokenize(doc)
    abstracts = build_abstracts(tokens)
    doc.close()

    # front matter(목차 등 세션 미상) 제거
    abstracts = [a for a in abstracts if a["session"]]
    for i, a in enumerate(abstracts, 1):
        a["id"] = i

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(
        {"count": len(abstracts), "abstracts": abstracts},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"parsed {len(abstracts)} abstracts -> {OUT}")

    by_sess = Counter(a["session"] or "NONE" for a in abstracts)
    print("sessions:", dict(sorted(by_sess.items())))
    print("no_title=%d no_authors=%d no_body=%d no_keywords=%d" % (
        sum(1 for a in abstracts if not a["title"]),
        sum(1 for a in abstracts if not a["authors"]),
        sum(1 for a in abstracts if not a["abstract"]),
        sum(1 for a in abstracts if not a["keywords"]),
    ))


if __name__ == "__main__":
    main()
