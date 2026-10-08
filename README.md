# confoinfo

학회 프로그램을 한 눈에 보는 모바일 우선 웹 앱. 발표를 둘러보고 ☆ 북마크하면
**My Plan** 에 시간·장소 타임테이블이 그려진다. 학회 자료 파일 하나
(`conferences/<slug>.json`)를 넣으면 어느 학회든 같은 화면으로 열린다.

[STRATI 2026 Companion](https://github.com/jikhanjung/strati2026) 을 여러 학회에 쓰도록 옮긴 것이다.

- **화면**: 학회 목록 → Program(날짜·룸 탭) / Sessions / Search / My Plan · 캘린더(.ics) · 메모
- **북마크·메모**: 로그인 없이 브라우저 localStorage(기기마다 따로). 모든 학회의 북마크가 한 My Plan 에 모인다
- **자료**: `confoinfo/1` 형식 — [docs/data-format.md](docs/data-format.md). CSV 에서 만드는 도구가 있다
- **사이트**: `https://koprifossillab.github.io/confoinfo/` — 서버 없는 정적 사이트(GitHub Pages).
  Django 5.2 로 화면을 그리고 `tools/build_site.sh` 가 파일로 굽는다. `main` 에 밀면 CI 가 올린다

## 학회

| slug | 학회 | 발표 | 초록 | 자료 |
|---|---|---|---|---|
| `strati2026` | STRATI 2026 — 5th International Congress on Stratigraphy (쑤저우, 2026-06-28~07-03) | 457 | 607 | `sources/strati2026/` (핸드북·초록집 PDF 파서) |

## 새 학회를 넣는다

```bash
# 스프레드시트에서
python tools/csv2conf.py program.csv --meta meta.json -o conferences/<slug>.json
python web/manage.py import_conference --check conferences/<slug>.json
```

예시는 `docs/examples/`. PDF 에서 뽑아야 하면 `sources/strati2026/` 처럼 `sources/<slug>/` 에
파서와 변환기를 둔다.

## 실행

```bash
python3.12 -m venv ~/venv/confoinfo && . ~/venv/confoinfo/bin/activate
pip install -r requirements.txt
python web/manage.py migrate
python web/manage.py import_conference --all
python web/manage.py runserver
python web/manage.py test conference
tools/build_site.sh          # 정적 사이트 → site/
```

지금 상태는 [HANDOFF.md](HANDOFF.md).
