# CHANGELOG

판 하나에 한 줄. 근거 devlog 번호와 함께. `main` 에 밀면 Pages 로 나간다.

| 판 | 날짜 | 무엇 |
|---|---|---|
| 0.4.0 | 2026-10-08 | 번역 — 사람 이름·코드·시각에 `translate="no"`(브라우저 번역이 안 건드리게) · 학회 `language` → `<html lang>` · 발표·세션 상세에 Papago·Google 번역 링크(긴 글은 나눠서, 언어는 설정에서). Google Scholar — 제1저자·교신저자의 프로필·논문 검색 링크(소속 곁들임) ([004](devlog/20261008_004_translate-scholar.md)) |
| 0.3.0 | 2026-10-08 | ICAMG 2026 을 넣었다 — `sources/icamg2026/`(icamg.org 의 HTML 표 셋 + 세션 소개) · 자료 형식에 세션 `conveners`·`description`, 발표 `code`(포스터 번호) · **발표·초록 pk 를 (slug, key) 에서 계산** — 빌드마다 읽는 순서로 밀리던 것(v0.2.0 의 북마크는 한 번 끊긴다) ([003](devlog/20261008_003_icamg2026.md)) |
| 0.2.0 | 2026-10-08 | 정적 사이트(GitHub Pages)로. `build_site`(구운 링크 검사) · 날짜는 경로(`/day/<날짜>/`) · 오늘 고르기·학회 갈래·검색·여러 발표 캘린더를 브라우저로 · `talks.json`·`search.json`·`talk.ics` · 검색이 악센트를 무시 · Docker·nginx·`/srv` 배포 틀을 걷었다 ([002](devlog/20261008_002_github-pages.md)) |
| 0.1.0 | 2026-10-08 | 1단계. strati2026 을 범용으로 — `Conference`·`Room`·`Session`·`Abstract`·`Talk` · 자료 형식 `confoinfo/1` · `import_conference` · 첫 화면·학회 가로지르는 검색·내 계획 · STRATI 2026 이식 · `csv2conf.py` · 시험 27개 (배포하지 않았다) ([P01](devlog/20261008_P01_generalize-strati2026.md) · [001](devlog/20261008_001_stage1-generic-viewer.md)) |
