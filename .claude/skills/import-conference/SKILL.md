---
name: import-conference
description: 새 학회의 프로그램(PDF 프로그램북·초록집, 학회 사이트 HTML, 스프레드시트/CSV, API)을 confoinfo 학회 자료 `conferences/<slug>.json` 으로 반입하고, 점검·배포까지 한다. 이미 들어간 학회의 새 판 프로그램을 다시 반입할 때도 쓴다. "학회 자료 반입", "이 프로그램북 넣어줘", "이 학회 페이지 데이터 이식", "N:\... pdf 반입", "프로그램 새 판 나왔어" 같은 요청에 쓴다.
---

# 학회 자료 반입

원본 하나 → `sources/<slug>/` 의 변환기 → `conferences/<slug>.json` → 점검 → 문서 → 커밋·푸시(=배포).
본보기: PDF 는 `sources/gskfall2026/`(devlog 009), HTML 은 `sources/icamg2026/`(003),
PDF 둘(프로그램+초록집)은 `sources/strati2026/`. 형식은 `docs/data-format.md` — **먼저 읽는다.**

## 0. 원본을 가져온다

- 사용자가 `N:\…` 로 말하면 NAS 다 — 이 서버에서는 **`/nfs/temp-share/…`** (`N:\GSM\temp\x.pdf` → `/nfs/temp-share/GSM/temp/x.pdf`).
  한글 파일 이름은 `ls` 에서 깨져 보인다 — 글롭(`2026*.pdf`)으로 집는다
- PDF·내려받은 파일은 남의 것이다: `sources/<slug>/data/` 에 둔다(gitignore). HTML 은 `sources/<slug>/raw/` 에
  **커밋한다** — 학회 사이트는 바뀌고 사라지므로 어느 판에서 뽑았는지를 git 이 가져야 한다
- 원본이 무엇을 갖고 있고 무엇이 없는지 먼저 본다: 초록 본문? 저자 소속? 포스터 번호? 룸의 층? 세션 소개?

## 1. 이름을 정한다 — 바꿀 수 없는 것과 바꿔도 되는 것

| | |
|---|---|
| `slug` | URL 이자 북마크의 열쇠. **한 번 내보내면 안 바꾼다.** 영소문자·숫자·하이픈. 예 `icamg2026` · `gskfall2026` |
| 발표 `key` | 북마크가 붙는 자리. **행 순서로 매기지 않는다.** 학회가 준 번호(`P001`, `1A-1300`)나 `날짜-룸-시각`(`1028-r3-0915`) |
| `short_name` | 머리글 큰 글씨. **한글 13자·영문 18자 안팎**을 넘으면 두 줄로 넘어간다. 언제든 고쳐도 된다 |
| `language` | 제목의 언어(`ko`·`en`). 화면 문구는 언제나 영어다 |
| `timezone` · `lunch_at` · `color` | 개최지 시각대 · 점심 시각(휴식 이름 고르기) · 머리글 색 |

slug 를 사용자에게 물을 필요는 없다 — 정하고 보고에 적는다. 이미 있는 slug 와 겹치거나
`search`·`plan`·`settings`·`static`·`i18n`·`manifest.webmanifest`·`sw.js` 면 안 된다.

## 2. 변환기를 쓴다 — `sources/<slug>/to_confoinfo.py`

머리말(docstring)에 **원본(파일 이름·판·받은 날·어디서) · 읽는 방법 · 내린 판단**을 적는다. 다음에 새 판이
오면 이것만 다시 돌린다. 산출은 `conferences/<slug>.json` 에 바로 쓴다.

**PDF** — `pymupdf` 로 `page.get_text("dict")` 의 줄마다 (x, y, 글꼴, 크기, 글)을 덤프해 **역할을 글꼴·x 로
가른다**(009). 정규식으로 줄을 읽는 것보다 덜 깨진다. 먼저 덤프 파일을 만들어 쪽 몇 장을 보고 표를 짠다.
- 쪽 옆 띠·머리글·쪽번호는 x·y 로 버린다 — 지난해 틀의 날짜가 남아 있기도 하다(009)
- 장 표지(큰 글씨, 시각 줄이 없는 쪽)는 쪽째 건너뛴다
- 같은 y(±3pt)를 한 행으로 모아 x 로 정렬한다 — 자간을 벌린 글자가 쪼개져 나온다
- 덤프를 `cut -c` 로 자르면 한글이 깨져 `�` 가 보인다 — 원본 문제가 아니다

**HTML** — 받은 파일에서 표를 읽는다. 세션 소개처럼 다른 페이지에 있는 것은 제목·좌장으로 짝짓는다(003).

**CSV/스프레드시트** — `tools/csv2conf.py` 로 대개 끝난다. `key` 칸을 둔다.

**어디서나 부딪힌 것**
- 저자 표시(`*` 등)의 뜻을 짐작하지 말고 확인한다. 같은 사람이 여러 편에 `*` 면 교신저자다(009).
  발표자가 따로 없으면 `speaker` 는 제1저자
- 초록 본문이 없어도 저자만 채운 초록 행을 만든다 — 공저자로 검색이 걸리고 상세에 저자가 나온다
- 세션 머리에 둘이 묶인 것(`G08 / G12`), 한 시각 칸에 제목이 둘(협약식)
- 룸마다 되풀이된 전체 행사(개회식·총회·만찬)는 한 번만, 룸 없이(Plenary 탭) — 기조강연은 열리는 룸에
- 휴식·점심은 넣지 않아도 된다(자동으로 생긴다). 넣으면 `kind: "break"`
- 포스터는 형식에 "기간"이 없다 — 발표(평가·코어 타임) 시각에 둔다
- 발표가 아닌 칸(분과총회·인사말·패널토론·워크숍)은 `kind: "event"`

## 3. 점검한다 — 원본과 맞춰 볼 때까지 끝이 아니다

```bash
workon ci
python sources/<slug>/to_confoinfo.py
python web/manage.py import_conference --check conferences/<slug>.json   # 형식
python tools/check_conf.py conferences/<slug>.json --sample 10           # 내용 — 겹침·빠진 번호·의심 행·표본
```

1. **수를 원본과 맞춘다** — 원본의 시각 줄 수·포스터 번호 끝·세션 수. 날짜·룸별 개수(check_conf 요약)가 원본의 한눈에 보는 표와 맞는지
2. **의심 행을 하나씩 원본과 대조한다** — 고치거나, 맞으면 넘긴다
3. **표본 10편을 원본 쪽에서 직접 찾아** 제목·저자·시각·룸이 맞는지 본다
4. **구워서 화면으로 본다** — `PYTHON=~/venv/confoinfo/bin/python tools/build_site.sh` 뒤 playwright(390×844)로
   첫 화면 · 프로그램(룸 탭) · 세션 목록 · 발표 상세. 머리글이 두 줄로 넘어가는지, 룸 탭 이름이 너무 긴지
   (미리 보기 서버는 `site` 를 `<dir>/confoinfo` 로 링크하고 `<dir>` 에서 `python3 -m http.server 8797`.
   끌 때 `pkill -f "http.server 8797"` 은 자기 셸까지 죽인다 — `fuser -k 8797/tcp`)
5. `python web/manage.py test conference`

## 4. 다시 반입할 때 (새 판 프로그램)

```bash
python tools/check_conf.py conferences/<slug>.json --old HEAD     # 사라진 key = 끊기는 북마크
```

사라진 key 가 있으면 왜 사라졌는지(발표 취소 vs 시각 이동 vs 변환기가 key 를 다르게 지음) 보고한다.
시각만 옮겨진 발표가 많으면 key 짓는 법을 바꾸지 말고 그대로 보고한다 — 이미 내보낸 key 를 바꾸면 전부 끊긴다.

## 5. 덧붙임 자료 — 묻기 전에 하지 않는다

- 번역(`enrich/<slug>.<lang>.json`)은 **제목·세션 소개만**. **초록 본문은 미리 번역하지 않는다**(비용)
- **지난 학회에는 덧붙임 자료를 만들지 않는다**
- 수백 건 번역·OpenAlex 조회처럼 큰 일은 범위와 비용을 먼저 말하고 사용자가 고르게 한다

## 6. 문서·배포

- `devlog/YYYYMMDD_NNN_<slug>.md` — 원본 · 결과(수) · **판단과 버린 것** · 하지 않은 것. 번호는 `ls devlog` 의 다음
- `CHANGELOG.md` 한 줄 + `web/confoinfoweb/version.py` 부판 올림(학회 추가는 0.x.0)
- `HANDOFF.md` 의 "학회" 줄과 맨 위 날짜·판
- 커밋: **파일을 지정해 add**(원본 PDF·DB 가 섞이지 않게), 한국어 메시지, 끝에 attribution
- **묻지 말고 푸시한다** — `main` 푸시가 곧 Pages 배포다. `gh run watch` 로 끝난 것을 보고,
  `https://koprifossillab.github.io/confoinfo/<slug>/` 가 200 인지 확인한다

## 보고

사용자에게: 들어간 수(세션·구두·포스터·행사) · 주소 · **내가 정한 것**(slug, short_name, `*` 해석, 포스터 시각 등 —
바꿀 수 있는 것과 없는 것을 갈라) · 원본에 없어서 빠진 것.
