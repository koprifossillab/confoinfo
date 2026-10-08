#!/usr/bin/env python3
"""스프레드시트(CSV) 프로그램 → confoinfo 학회 자료.

    python tools/csv2conf.py program.csv --meta meta.json -o conferences/<slug>.json

PDF 를 파싱해야 하는 학회(STRATI 2026 처럼 `sources/<slug>/` 에 파서를 둔다)가
아니면 대개 이것으로 끝난다 — 학회 사이트의 표를 스프레드시트로 옮겨 CSV 로
내보내면 된다. 예시는 `docs/examples/`, 형식은 `docs/data-format.md`.

CSV 머리줄(순서 무관, 대소문자 무관):

    date,start,end,room,session,title,speaker,kind,authors,abstract,keywords

- `date` YYYY-MM-DD · `start`/`end` HH:MM — **필수는 date·start·title 셋**
- `kind` 비면 talk. break 이면 휴식(북마크 안 됨)
- `authors` 는 `;` 로 가른다. 비면 speaker 하나
- `abstract` 에 본문이 있으면 초록을 만들어 발표에 잇는다. `keywords` 는 `;`
- `key` 칸이 있으면 그것을, 없으면 줄 번호를 발표 식별자로 쓴다. **나중에 줄을
  끼워 넣을 일이 있으면 `key` 칸을 둔다** — 줄 번호가 밀리면 브라우저의 북마크가
  다른 발표를 가리킨다

meta.json 은 자료 형식의 `conference`(필수)·`rooms`·`sessions` 를 그대로 쓴다.
CSV 에만 나오는 룸·세션은 끝에 덧붙인다(세션 제목은 빈 채로).
"""
import argparse
import csv
import json
import sys
from pathlib import Path


def split(s, sep=";"):
    return [x.strip() for x in (s or "").split(sep) if x.strip()]


def convert(rows, meta):
    rooms = list(meta.get("rooms") or [])
    sessions = list(meta.get("sessions") or [])
    known_rooms = {r["name"] for r in rooms}
    known_sessions = {s["code"] for s in sessions}
    talks, abstracts = [], []
    for i, row in enumerate(rows, start=2):           # 1 은 머리줄
        r = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
        if not any(r.values()):
            continue
        key = r.get("key") or str(i)
        if r.get("room") and r["room"] not in known_rooms:
            rooms.append({"name": r["room"]})
            known_rooms.add(r["room"])
        if r.get("session") and r["session"] not in known_sessions:
            sessions.append({"code": r["session"], "title": ""})
            known_sessions.add(r["session"])
        abstract = None
        if r.get("abstract"):
            authors = split(r.get("authors")) or ([r["speaker"]] if r.get("speaker") else [])
            abstracts.append({
                "key": key, "session": r.get("session") or None, "title": r["title"],
                "text": r["abstract"], "keywords": split(r.get("keywords")),
                "authors": [{"name": a} for a in authors],
            })
            abstract = key
        talks.append({
            "key": key, "date": r.get("date"), "start": r.get("start"),
            "end": r.get("end") or None, "room": r.get("room") or None,
            "session": r.get("session") or None, "title": r.get("title"),
            "speaker": r.get("speaker", ""), "kind": r.get("kind") or "talk",
            "abstract": abstract,
        })
    return {"format": "confoinfo/1", "conference": meta["conference"],
            "rooms": rooms, "sessions": sessions, "abstracts": abstracts, "talks": talks}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("csv")
    ap.add_argument("--meta", required=True, help="conference·rooms·sessions 가 든 JSON")
    ap.add_argument("-o", "--out", help="안 주면 표준 출력")
    a = ap.parse_args(argv)
    meta = json.loads(Path(a.meta).read_text(encoding="utf-8"))
    # utf-8-sig: 엑셀이 내보낸 CSV 의 BOM 을 먹는다
    with open(a.csv, encoding="utf-8-sig", newline="") as f:
        data = convert(list(csv.DictReader(f)), meta)
    text = json.dumps(data, ensure_ascii=False, indent=1) + "\n"
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"{a.out}: 발표 {len(data['talks'])} · 초록 {len(data['abstracts'])} · "
              f"룸 {len(data['rooms'])} · 세션 {len(data['sessions'])}", file=sys.stderr)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
