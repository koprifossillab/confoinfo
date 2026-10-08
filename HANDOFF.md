# HANDOFF

**2026-10-08** · v0.2.0 · 정적 사이트(GitHub Pages)로 옮겼다([002](devlog/20261008_002_github-pages.md)) ·
**`https://koprifossillab.github.io/confoinfo/` 에 떠 있다** (2026-10-08 Pages 켬).
이어서 할 사람은 여기부터.

## 0. admin 이 할 것

없다. ~~GitHub Pages 켜기~~ — 2026-10-08 admin 이 Source 를 GitHub Actions 로 켰고, 첫 배포가 돌았다.

## 1. 한 줄 요약

`conferences/<slug>.json` 하나를 넣고 `main` 에 밀면 그 학회의 프로그램·세션·검색·내 계획이
공개 주소에 열린다. 폰에서 VPN·Tailscale 없이 연다. STRATI 2026(발표 457 · 초록 607, 본문 포함)이
들어 있다. ICAMG 2026(부산, 11-02~04 · 구두 108 · 포스터 75, 초록 본문은 아직 미공개)도.
북마크·메모는 그 브라우저에만 있다 — 서버가 없어 기기 간 동기화는 없다.

| | 지금 |
|---|---|
| 사이트 | `tools/build_site.sh` → `site/` (1,568개 파일 · 17 MB) · 링크 검사 · CI 가 `main` 에서 굽는다 |
| 학회 | `icamg2026`(icamg.org HTML · `sources/icamg2026/fetch.sh` 로 다시 받는다) · `strati2026`(지난 학회). `docs/examples/` 의 가상 학회는 본보기 — 안 넣는다 |
| 시험 | 28개 (`python web/manage.py test conference`) |
| 남은 것 | `TODOs.md` |

## 2. 화면 (구운 경로)

```
첫 화면       /confoinfo/                         학회 카드 — 진행 중(LIVE)·다가올·지난 갈래는 JS 가 오늘로
프로그램      /<slug>/  ·  /<slug>/day/<날짜>/     뿌리는 첫째 날 — 학회 기간이면 JS 가 오늘로 넘긴다
세션          /<slug>/sessions/ · /<slug>/session/<code>/
발표·초록     /<slug>/talk/<pk>/ · /<slug>/abstract/<pk>/   ☆ · 메모 · talk.ics(발표 하나)
검색          /<slug>/search/ · /search/          search.json 을 받아 브라우저에서 (악센트 무시, 낱말 모두) ·
                                                  자동완성 · 한글 이름("최경식") · 한국어 번역 제목 (007, kname.js)
내 계획       /<slug>/plan/ · /plan/              talks.json 에서 북마크만 골라 · 여러 발표 .ics 는 JS 가 만든다
설정          /settings/                          기본 학회 · 테마 · 글꼴 · 휴식 · 번역 언어 · 이 기기 지우기 · 판 이력(CHANGELOG.md)
```

## 3. 함정

- **뷰가 요청을 보면 안 된다** — `request.GET`·`timezone.now()` 는 굽는 순간의 값으로 굳는다 (CLAUDE.md)
- **발표 pk = (slug, key) 의 해시다** (`loader.stable_id`, 003). `key`·`slug` 를 바꾸면 그 북마크가 끊긴다.
  DB 의 일련번호로 되돌리면 학회 하나를 더할 때마다 다른 학회의 북마크가 밀린다
- `localStorage` 는 출처(`koprifossillab.github.io`) 단위다 — 같은 조직의 다른 Pages 와 키 공간을 나눠 쓴다. 키는 늘 `confoinfo_` 로 시작할 것
- **템플릿의 여러 줄 주석은 `{% comment %}`** — `{# #}` 는 한 줄짜리라 여러 줄이면 화면에 글로 나온다. 굽기가 잡는다 (005)
- 색은 `style.css` 머리의 토큰으로만 — 글자색에 `--navy` 를 쓰면 다크에서 안 읽힌다. 글자는 `--link`
- `STATIC_URL` 은 서브경로를 직접 단다 — 상대경로로 되돌리면 구운 사이트의 CSS 가 404 다 (001)
- 미리 보기는 `/confoinfo/` 아래로 띄워야 한다 — `build_site.sh` 가 끝에 명령을 찍어 준다
- **덧붙임 자료(`enrich/`)는 이 서버에서 미리 만든다** — 번역은 원문 해시가 열쇠라 원문이 바뀌면 안 나온다
  (`tools/i18n_todo.py <slug> ko` 가 다시 할 것을 뽑는다). 대표 논문은 `tools/fetch_openalex.py <slug>` (006)
- **STRATI 2026 은 덧붙임 자료를 만들지 않는다** — 지난 학회다(사용자, 2026-10-08)
- **초록 본문은 미리 번역하지 않는다** — 비용이 과하다(사용자, 2026-10-08). 미리 번역은 제목·세션 소개만,
  초록은 Papago·Google 링크로. `tools/i18n_todo.py` 가 초록 본문을 아예 안 뽑는다
- 헤드리스 화면 확인은 `playwright==1.49.1`(requirements-dev) — 이 서버의 크로미움 판에 맞췄다.
  `page.clock.install(time=…)` 으로 학회 기간을 흉내 낸다
