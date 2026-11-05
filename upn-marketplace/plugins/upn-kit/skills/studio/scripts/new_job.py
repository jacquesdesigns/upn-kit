#!/usr/bin/env python3
"""Start a new studio job folder from the job template.

    <python> "<kit_root>/skills/studio/scripts/new_job.py" <client> <job> [--name "Job name"]

Copies the job template to `<home>/projects/<client>/<job>/` (home is the Studio folder in ~/.claude/upn-kit/config.json), fills the job's name, the
client and today's date into the headings, and sets `name` in `job.json`. It never overwrites: if the
job folder already exists it stops. Standard library only.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parent / "templates" / "job"


def _home():
    try:
        cfg = json.loads((Path.home() / ".claude" / "upn-kit" / "config.json").read_text("utf-8"))
        if cfg.get("home"):
            return Path(cfg["home"])
    except Exception:
        pass
    return Path.home() / "Studio"


CLIENTS = _home() / "projects"
REPO = _home()

TEXT_SUFFIXES = {".md", ".json", ".txt"}


def human_date(d: dt.date) -> str:
    return f"{d.day} {d.strftime('%b')} {d.year}"


def safe_part(value: str, what: str) -> str:
    v = value.strip()
    if not v or v in {".", ".."} or "/" in v or "\\" in v or v.startswith("."):
        raise SystemExit(f"new_job: '{value}' is not a usable {what} folder name")
    return v


def fill(text: str, values: dict[str, str]) -> str:
    for key, val in values.items():
        text = text.replace("{{" + key + "}}", val)
    return text


def main() -> int:
    ap = argparse.ArgumentParser(description="Start a new studio job folder from the job template.")
    ap.add_argument("client", help="the client's folder name")
    ap.add_argument("job", help="the job's folder name")
    ap.add_argument("--name", help="the job's name as people say it (job.json 'name'); defaults to the folder name")
    ap.add_argument("--root", type=Path, default=CLIENTS,
                    help="where client folders live (default: <home>/projects)")
    args = ap.parse_args()

    client = safe_part(args.client, "client")
    job = safe_part(args.job, "job")
    name = (args.name or job).strip()
    target = args.root.resolve() / client / job

    if not TEMPLATE.is_dir():
        print(f"new_job: the template is missing ({TEMPLATE})", file=sys.stderr)
        return 1
    if target.exists():
        print(f"new_job: {target} already exists; nothing was copied", file=sys.stderr)
        return 1

    values = {"job": name, "client": client, "date": human_date(dt.date.today())}
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(TEMPLATE, target)

    for path in sorted(target.rglob("*")):
        if path.is_file() and path.suffix in TEXT_SUFFIXES:
            path.write_text(fill(path.read_text(encoding="utf-8"), values), encoding="utf-8")

    job_json = target / "job.json"
    raw = job_json.read_text(encoding="utf-8")
    raw = raw.replace('"name": ""', '"name": ' + json.dumps(name, ensure_ascii=False), 1)
    job_json.write_text(raw, encoding="utf-8")
    data = json.loads(raw)
    if data.get("name") != name:
        print("new_job: could not set the name in job.json; set it by hand", file=sys.stderr)
        return 1

    try:
        shown = target.relative_to(REPO)
    except ValueError:
        shown = target
    print(f"new_job: made {shown}")
    for path in sorted(target.rglob("*")):
        if path.is_file():
            print(f"  {path.relative_to(target)}")
    print("Next: /studio for the intake. Fill 00 brief/INTAKE.md as the references are given; "
          "the job's stage and gates live in job.json.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
