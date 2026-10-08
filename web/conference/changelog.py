"""CHANGELOG.md → 판 이력 (설정 화면, 005).

GSM 의 `patchnotes.py` 와 같은 일을 하되 CHANGELOG 의 꼴이 다르다 — 여기는 표다:

    | 판 | 날짜 | 무엇 |
    | 0.4.0 | 2026-10-08 | 번역 — … ([004](devlog/…)) |

markdown 라이브러리를 들이지 않는다. 링크는 글자만 남기고(`[004](…)` → `004`, devlog 는
사이트에 없다), `` `x` `` 는 <code>, `**x**` 는 <b>. HTML 은 먼저 이스케이프한다.
"""
import html
import re

ROW = re.compile(r"^\|\s*([^|]+?)\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*(.+?)\s*\|\s*$")


def _inline(text):
    text = html.escape(re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text))
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)


def parse(text):
    """[{version, date, html}] — 표의 순서 그대로(새 판이 위)."""
    out = []
    for line in text.splitlines():
        m = ROW.match(line.strip())
        if not m:
            continue
        version, date, body = m.groups()
        out.append({"version": version if version != "—" else "", "date": date, "html": _inline(body)})
    return out
