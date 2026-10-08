#!/usr/bin/env python3
"""아직 번역이 없는(또는 원문이 바뀐) 글을 뽑는다 (006).

    python tools/i18n_todo.py icamg2026 ko > todo.json      # [{"k": 열쇠, "kind": title|body, "text": 원문}]
    python tools/i18n_todo.py icamg2026 ko --merge done.json # {열쇠: 번역} 을 enrich/icamg2026.ko.json 에 합친다

번역할 것: 발표 제목(휴식 빼고) · 초록 제목·본문 · 세션 제목·소개. 열쇠는
`conference.enrich.text_key` 와 같다(원문 sha1 앞 16자).
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def text_key(text):
    return hashlib.sha1((text or "").strip().encode()).hexdigest()[:16]


def sources(slug):
    d = json.loads((REPO / "conferences" / f"{slug}.json").read_text(encoding="utf-8"))
    items = {}

    def add(t, kind):
        t = (t or "").strip()
        if t:
            items.setdefault(text_key(t), {"k": text_key(t), "kind": kind, "text": t})
    for t in d.get("talks") or []:
        if t.get("kind") != "break":
            add(t.get("title"), "title")
    for a in d.get("abstracts") or []:
        add(a.get("title"), "title")
        add(a.get("text"), "body")
    for s in d.get("sessions") or []:
        add(s.get("title"), "title")
        add(s.get("description"), "body")
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("lang")
    ap.add_argument("--merge", help="{열쇠: 번역} JSON 을 합친다")
    a = ap.parse_args()
    path = REPO / "enrich" / f"{a.slug}.{a.lang}.json"
    store = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"lang": a.lang, "t": {}}
    src = sources(a.slug)
    if a.merge:
        new = json.loads(Path(a.merge).read_text(encoding="utf-8"))
        unknown = [k for k in new if k not in src]
        store["t"].update({k: v for k, v in new.items() if k in src and v.strip()})
        # 원문에서 사라진 열쇠는 걷는다 — 파일이 낡은 번역으로 불어나지 않게
        store["t"] = {k: v for k, v in sorted(store["t"].items()) if k in src}
        path.write_text(json.dumps(store, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"{path.relative_to(REPO)}: 번역 {len(store['t'])} / 원문 {len(src)}"
              + (f" · 모르는 열쇠 {len(unknown)}개는 버렸다" if unknown else ""), file=sys.stderr)
        return
    todo = [v for k, v in src.items() if k not in store["t"]]
    json.dump(todo, sys.stdout, ensure_ascii=False, indent=0)
    print(f"\n번역할 것 {len(todo)} / 원문 {len(src)}", file=sys.stderr)


if __name__ == "__main__":
    main()
