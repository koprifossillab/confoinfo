"""학회 자료 파일을 DB 로 읽어 들인다.

    python web/manage.py import_conference conferences/strati2026.json
    python web/manage.py import_conference --all          # CONFERENCES_DIR 의 *.json 전부
    python web/manage.py import_conference --check FILE   # 검사만, DB 는 안 건드린다
    python web/manage.py import_conference --remove SLUG  # 학회 하나를 DB 에서 지운다

컨테이너가 기동할 때마다 `--all` 을 돈다(entrypoint). 자료가 이미지에 같이 들어가므로
판을 올리면 자료도 따라 올라간다. 파일 하나가 오류로 막혀도 나머지는 읽는다 —
대신 끝에 실패로 끝내 entrypoint 로그에 남는다.

**파일을 지워도 DB 의 학회는 남는다.** `--all` 이 "파일에 없는 학회" 를 지우지
않는 것은 일부러다 — 파일 이름을 잘못 옮긴 한 번에 학회가 통째로 사라지면 안 된다.
내릴 때는 `--remove` 로 사람이 한다.
"""
import json
import sys
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from conference.loader import load, validate
from conference.models import Conference


class Command(BaseCommand):
    help = "conferences/<slug>.json 을 DB 로 읽어 들인다 (pk 를 지키며 맞춘다)."

    def add_arguments(self, parser):
        parser.add_argument("files", nargs="*")
        parser.add_argument("--all", action="store_true",
                            help="CONFERENCES_DIR 의 *.json 을 전부")
        parser.add_argument("--check", action="store_true", help="검사만 한다")
        parser.add_argument("--remove", metavar="SLUG", help="이 학회를 DB 에서 지운다")

    def handle(self, *args, **opts):
        if opts["remove"]:
            n, _ = Conference.objects.filter(slug=opts["remove"]).delete()
            if not n:
                raise CommandError(f"그런 학회가 없다: {opts['remove']}")
            self.stdout.write(f"지웠다: {opts['remove']}")
            return

        files = [Path(f) for f in opts["files"]]
        if opts["all"]:
            files += sorted(Path(settings.CONFERENCES_DIR).glob("*.json"))
        if not files:
            raise CommandError("파일을 주거나 --all 을 준다")

        failed = 0
        for path in files:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as e:
                self.stderr.write(f"✗ {path}: 읽지 못했다 — {e}")
                failed += 1
                continue
            errors, warnings = validate(data)
            for w in warnings:
                self.stdout.write(f"  ! {path.name}: {w}")
            if errors:
                for e in errors[:30]:
                    self.stderr.write(f"  ✗ {path.name}: {e}")
                if len(errors) > 30:
                    self.stderr.write(f"  ✗ … 오류 {len(errors) - 30}개 더")
                failed += 1
                continue
            if opts["check"]:
                self.stdout.write(f"✓ {path.name}: 이상 없다 (경고 {len(warnings)})")
                continue
            s = load(data)
            self.stdout.write(
                f"✓ {path.name} → {s['slug']}{' (새로)' if s['created'] else ''}: "
                f"룸 {s['rooms']} · 세션 {s['sessions']} · 초록 {s['abstracts']} · "
                f"발표 {s['talks']} (초록 연결 {s['linked']}) · 지운 행 {s['removed']}")
        if failed:
            self.stderr.write(f"{failed}개 파일이 실패했다")
            sys.exit(1)
