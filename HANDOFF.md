# HANDOFF

**2026-10-08** · 1단계(범용 모델·자료 형식·화면·배포 틀) 코드 끝 · **아직 어디에도 안 떴다** ·
`main` 에 밀었고 CI(시험·이미지 굽기)가 통과했다. 이어서 할 사람은 여기부터.

## 0. admin 이 할 것 (2026-10-08 sclee)

`sclee` 의 두 GitHub 계정과 sudo 없이는 못 하는 것들이다. **위에서부터 차례로.**

1. ~~**저장소 쓰기 권한**~~ — 2026-10-08 초대를 받아 `wetherilli`·`jikhanjung` 둘 다 수락했고 `main` 을 밀었다.

2. **`/srv/confoinfo` 를 만든다** (`/srv` 는 root 다):

   ```bash
   sudo install -d -o paleoadmin -g paleoadmin -m 2775 /srv/confoinfo
   ~sclee/projects/confoinfo/deploy/host/sync_to_srv.sh        # compose · bin/ · www/ · db/
   cp ~sclee/projects/confoinfo/deploy/srv/env.template /srv/confoinfo/.env && chmod 660 /srv/confoinfo/.env
   # .env 의 CONFOINFO_SECRET_KEY 를 채운다
   ```

3. **nginx 조각** — phyloserver 블록에 한 줄:

   ```bash
   sudo cp ~sclee/projects/confoinfo/deploy/nginx/confoinfo-subpath.conf /etc/nginx/snippets/
   # /etc/nginx/sites-available/phyloserver 의 server 블록 안:  include snippets/confoinfo-subpath.conf;
   sudo nginx -t && sudo systemctl reload nginx
   ```

4. **Docker Hub** — 저장소 시크릿 `DOCKERHUB_USERNAME`·`DOCKERHUB_TOKEN` (ForGIA 와 같은 것).
   그 뒤 `v0.1.0` 태그를 밀면 CI 가 `koprifossillab/confoinfo:v0.1.0` 을 올린다 →
   `/srv/confoinfo/bin/deploy.sh v0.1.0`.
   시크릿 전에 먼저 띄워 보려면 이 머신에서 구운 것으로:

   ```bash
   cd ~/projects/confoinfo && docker build -f deploy/Dockerfile -t koprifossillab/confoinfo:v0.1.0 .
   /srv/confoinfo/bin/deploy.sh v0.1.0 --no-pull
   ```

## 1. 한 줄 요약

`conferences/<slug>.json` 하나를 넣으면 그 학회의 프로그램·세션·검색·내 계획이 열린다.
STRATI 2026(발표 457 · 초록 607)이 들어 있다. 북마크·메모는 브라우저에만 있다.
**동기화·사진(strati2026 의 후반부)은 2단계다** — 어디에 여는지(P01 5절)가 먼저 정해져야 한다.

| | 지금 |
|---|---|
| 뷰어 | Django 5.2 · 개발 서버로만 확인. 이미지는 이 머신에 `koprifossillab/confoinfo:v0.1.0-dev`(156 MB, 시험용) |
| 학회 | `strati2026` 하나 (지난 학회). `docs/examples/` 의 가상 학회는 시험·본보기용 — 안 넣는다 |
| 배포 | 틀만 있다 — `/srv/confoinfo` · nginx · Docker Hub 가 0절 |
| 시험 | 27개 (`python web/manage.py test conference`) · CI 가 `main` 에서 돈다(첫 판 통과) |
| 단계 | **1 끝 → 2(동기화) 는 P01 5절 ①② 를 정한 뒤** |

## 2. 화면

```
첫 화면       /                       진행 중(LIVE) · 다가올 · 지난 학회 카드
프로그램      /<slug>/?day=           날짜 칩 · 룸 탭(스와이프) · 휴식/점심 · 현재 시각 줄(개최지 시각)
세션          /<slug>/sessions/       묶음(group)별 · 세션 상세에 구두 + 그 밖의 초록
발표·초록     /<slug>/talk/<pk>/      ☆ · 캘린더 · 메모(이 기기) · 초록 본문·저자·소속
검색          /<slug>/search/ · /search/      제목·발표자·공저자·키워드·세션 + 프로그램 밖 초록
내 계획       /<slug>/plan/ · /plan/          북마크 타임테이블 — 겹치면 격자, 빈 시간은 압축
설정          /settings/              휴식 보이기 · 이 기기의 북마크 지우기
API           /api/talks/?ids= · /calendar.ics?ids= · /healthz
```

## 3. 함정

- **자료의 `key` 를 바꾸면 그 발표의 북마크가 끊긴다** (`docs/data-format.md`)
- **학회 slug 로 `search`·`plan`·`settings`·`api`·`healthz` 를 못 쓴다** — 위 경로가 가린다. loader 가 막는다
- `STATIC_URL` 은 서브경로를 직접 단다 — 상대경로로 되돌리면 이미지에서만 CSS 가 404 다 (001)
- `conferences/` 의 파일을 지워도 DB 의 학회는 남는다 — `import_conference --remove <slug>`
- 헤드리스 화면 확인은 `playwright==1.49.1`(requirements-dev) — 이 서버의 크로미움 판에 맞췄다
