# TODOs

## 운영·바깥 (HANDOFF 0절)

- `/srv/confoinfo` · nginx 조각 · Docker Hub 시크릿 → `v0.1.0` 태그 → `deploy.sh v0.1.0`
- paleolab 첫 화면에 카드를 둘지 (ForGIA 는 `/srv/paleolab/index.html` 을 admin 이 갈았다)

## 정할 것 (P01 5절)

- **어디에 여는가** — 사내망+VPN 이면 학회장에서 폰으로 못 연다. 공개 주소·TLS 를 둘지
- 동기화를 옮기는가 · 라이선스(저장소는 public, strati2026 에 LICENSE 없음) · 다음에 넣을 학회

## 2단계 — 동기화 (정한 뒤)

- strati2026 028~039: 익명 기기 토큰 · 6자리 연결 코드 · 기기 목록·끊기 · 메모 동기화 · 사진 · `/manage/`
- 사람의 자료가 DB 에 생기므로 **백업을 같이** — `backup_db.py`(sqlite 백업 API) · 시간별 cron ·
  `/healthz` 신선도 게이트 · `deploy.sh` 의 배포 전 사본을 cp 에서 그것으로 · smoke 에 행 수

## 3단계 — 둘째 학회

- 포스터 세션(시간대 + 번호판) · 트랙 이름 · 학회 안내(장소·지도·교통)를 형식에 넣을지
- strati2026 의 남은 것: 핸드북 메타(위원회·기조연사·답사) · G18·S14 제목

## 4단계

- 화면 문구 한국어 토글 (국내 학회) · 오프라인(PWA) · 시험 겹 하나 더(브라우저 — ForGIA 처럼 CI 에서)
