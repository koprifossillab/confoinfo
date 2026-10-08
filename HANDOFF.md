# HANDOFF

**2026-10-08** · v0.2.0 · 정적 사이트(GitHub Pages)로 옮겼다([002](devlog/20261008_002_github-pages.md)) ·
**Pages 가 아직 안 켜져 있다** — 그것만 되면 `https://koprifossillab.github.io/confoinfo/` 가 뜬다.
이어서 할 사람은 여기부터.

## 0. admin 이 할 것

1. **GitHub Pages 켜기** — `koprifossillab/confoinfo` → Settings → Pages → Build and deployment →
   Source: **GitHub Actions**. 저장소 admin 만 된다(`wetherilli`·`jikhanjung` 은 Write 라 API 도 404).
   켠 뒤 Actions 에서 "사이트" workflow 를 한 번 다시 돌리거나(Run workflow) `main` 에 아무거나 민다.

## 1. 한 줄 요약

`conferences/<slug>.json` 하나를 넣고 `main` 에 밀면 그 학회의 프로그램·세션·검색·내 계획이
공개 주소에 열린다. 폰에서 VPN·Tailscale 없이 연다. STRATI 2026(발표 457 · 초록 607, 본문 포함)이
들어 있다. 북마크·메모는 그 브라우저에만 있다 — 서버가 없어 기기 간 동기화는 없다.

| | 지금 |
|---|---|
| 사이트 | `tools/build_site.sh` → `site/` (1,568개 파일 · 17 MB) · 링크 검사 · CI 가 `main` 에서 굽는다 |
| 학회 | `strati2026` 하나 (지난 학회). `docs/examples/` 의 가상 학회는 본보기 — 안 넣는다 |
| 시험 | 28개 (`python web/manage.py test conference`) |
| 남은 것 | Pages 켜기(0절) · `TODOs.md` |

## 2. 화면 (구운 경로)

```
첫 화면       /confoinfo/                         학회 카드 — 진행 중(LIVE)·다가올·지난 갈래는 JS 가 오늘로
프로그램      /<slug>/  ·  /<slug>/day/<날짜>/     뿌리는 첫째 날 — 학회 기간이면 JS 가 오늘로 넘긴다
세션          /<slug>/sessions/ · /<slug>/session/<code>/
발표·초록     /<slug>/talk/<pk>/ · /<slug>/abstract/<pk>/   ☆ · 메모 · talk.ics(발표 하나)
검색          /<slug>/search/ · /search/          search.json 을 받아 브라우저에서 (악센트 무시, 낱말 모두)
내 계획       /<slug>/plan/ · /plan/              talks.json 에서 북마크만 골라 · 여러 발표 .ics 는 JS 가 만든다
설정          /settings/
```

## 3. 함정

- **뷰가 요청을 보면 안 된다** — `request.GET`·`timezone.now()` 는 굽는 순간의 값으로 굳는다 (CLAUDE.md)
- **자료의 `key` 를 바꾸면 그 발표의 북마크가 끊긴다** (`docs/data-format.md`)
- `localStorage` 는 출처(`koprifossillab.github.io`) 단위다 — 같은 조직의 다른 Pages 와 키 공간을 나눠 쓴다. 키는 늘 `confoinfo_` 로 시작할 것
- `STATIC_URL` 은 서브경로를 직접 단다 — 상대경로로 되돌리면 구운 사이트의 CSS 가 404 다 (001)
- 미리 보기는 `/confoinfo/` 아래로 띄워야 한다 — `build_site.sh` 가 끝에 명령을 찍어 준다
- 헤드리스 화면 확인은 `playwright==1.49.1`(requirements-dev) — 이 서버의 크로미움 판에 맞췄다.
  `page.clock.install(time=…)` 으로 학회 기간을 흉내 낸다
