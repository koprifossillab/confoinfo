# CHANGELOG

판 하나에 한 줄. 근거 devlog 번호와 함께. `main` 에 밀면 Pages 로 나간다.

| 판 | 날짜 | 무엇 |
|---|---|---|
| 0.8.0 | 2026-10-09 | 머리글을 새로 — 사용자가 고른 C안(학회 색 두 줄). 위 도구 줄(돌아가기 · confoinfo · 설정, 선 아이콘)은 붙어 따라오고 큰 제목 줄(학회 이름 · D-n/LIVE · 날짜·장소)은 스크롤하면 지나가며 도구 줄에 학회 이름이 뜬다. 판 번호는 설정 About 으로만 ([008](devlog/20261009_008_appbar.md)) |
| 0.7.1 | 2026-10-09 | 설정에 About — 만든이(극지연구소 정직한 · 이승찬) · 판 · 소스 저장소 링크 |
| 0.7.0 | 2026-10-08 | 검색 자동완성(저자·세션·발표, 방향키·엔터) · 한글로 저자 찾기("최경식" → Kyungsik Choi — 성은 표기 표, 이름은 표기 차이를 접은 뼈대로) · 미리 번역한 한국어 제목으로도 찾는다 ([007](devlog/20261008_007_search-autocomplete-korean-names.md)) |
| 0.6.0 | 2026-10-08 | ICAMG 2026 을 한국어로 — 제목·세션 소개 240건을 미리 번역해 넣었다(`enrich/icamg2026.ko.json`). 목록에는 제목 아래, 상세에는 원문/한국어 탭, 설정에서 끈다. 제1저자·교신저자의 대표 논문 셋을 OpenAlex 에서 미리 받아 넣었다(175명 중 117명 · 연구 주제로 동명이인을 거른다). 사용자 브라우저는 바깥을 부르지 않는다 ([006](devlog/20261008_006_prebaked-translation-works.md)) |
| 0.5.0 | 2026-10-08 | 설정 화면 — 기본으로 볼 학회(맨 위, 들어오면 바로 그 학회로) · 테마(Auto·Light·Dark, 그리기 전에 적용) · 글꼴(Sans·Serif·System) · 판 이력(이 표). 학회 화면 머리글에 `‹ All`(학회 목록으로)·설정 단추. 색을 전부 토큰으로. 굽기가 화면에 새어 나온 템플릿 문법을 잡는다 ([005](devlog/20261008_005_settings-look.md)) |
| 0.4.0 | 2026-10-08 | 번역 — 사람 이름·코드·시각에 `translate="no"`(브라우저 번역이 안 건드리게) · 학회 `language` → `<html lang>` · 발표·세션 상세에 Papago·Google 번역 링크(긴 글은 나눠서, 언어는 설정에서). Google Scholar — 제1저자·교신저자의 프로필·논문 검색 링크(소속 곁들임) ([004](devlog/20261008_004_translate-scholar.md)) |
| 0.3.0 | 2026-10-08 | ICAMG 2026 을 넣었다 — `sources/icamg2026/`(icamg.org 의 HTML 표 셋 + 세션 소개) · 자료 형식에 세션 `conveners`·`description`, 발표 `code`(포스터 번호) · **발표·초록 pk 를 (slug, key) 에서 계산** — 빌드마다 읽는 순서로 밀리던 것(v0.2.0 의 북마크는 한 번 끊긴다) ([003](devlog/20261008_003_icamg2026.md)) |
| 0.2.0 | 2026-10-08 | 정적 사이트(GitHub Pages)로. `build_site`(구운 링크 검사) · 날짜는 경로(`/day/<날짜>/`) · 오늘 고르기·학회 갈래·검색·여러 발표 캘린더를 브라우저로 · `talks.json`·`search.json`·`talk.ics` · 검색이 악센트를 무시 · Docker·nginx·`/srv` 배포 틀을 걷었다 ([002](devlog/20261008_002_github-pages.md)) |
| 0.1.0 | 2026-10-08 | 1단계. strati2026 을 범용으로 — `Conference`·`Room`·`Session`·`Abstract`·`Talk` · 자료 형식 `confoinfo/1` · `import_conference` · 첫 화면·학회 가로지르는 검색·내 계획 · STRATI 2026 이식 · `csv2conf.py` · 시험 27개 (배포하지 않았다) ([P01](devlog/20261008_P01_generalize-strati2026.md) · [001](devlog/20261008_001_stage1-generic-viewer.md)) |
