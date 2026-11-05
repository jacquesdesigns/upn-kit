"""Start a UPN job: folder, NOW.md, project map row, recorded Dropbox path. Standard library only.

  python jobstart.py --brain <brain> --number 10360 --client <client> --project <project> [--dropbox <path>] [--stage "<stage>"] [--due <date>]

Never overwrites. Never touches Dropbox: it only writes the path down.
"""
import argparse
import datetime
import json
import re
import shutil
import sys
from pathlib import Path


def slug(s):
    return re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")


NOW = """# NOW: {name} (job {number})
started {today} by job-start. Notes, not instructions.

## CARD
- heard: (the person's words, quoted)
- done when: (what must be true)
- touch only: this folder
- by: {due}

## where things are
- brain folder: {folder}
- Dropbox job folder: {dropbox}
- drafts: (decided per job, write it here) ; in Dropbox Claude only saves new files, never overwrites, moves, renames or deletes; list what was saved below

## done
- {today}: job folder, NOW file and map row created.

## open
- (nothing yet)

## next
- (the one next step)

## files
- (made / changed, full paths)
"""


def add_map_row(map_path, values):
    if not map_path.exists():
        map_path.write_text("# Project map\n\n| Folder | Job | Stage | Due | Dropbox |\n|---|---|---|---|---|\n", encoding="utf-8")
    lines = map_path.read_text(encoding="utf-8").splitlines()
    for i, l in enumerate(lines):
        if l.strip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            head = [c.strip() for c in l.strip().strip("|").split("|")]
            end = i + 2
            while end < len(lines) and lines[end].strip().startswith("|"):
                end += 1
            row = []
            for h in head:
                hl = h.lower()
                key = ("folder" if re.search(r"folder|project|name", hl) else "job" if re.search(r"job|number|ref|code", hl)
                       else "stage" if re.search(r"stage|status|pipeline", hl) else "due" if re.search(r"due|deadline|date", hl)
                       else "dropbox" if re.search(r"dropbox|path|server", hl) else "")
                row.append(values.get(key, ""))
            lines.insert(end, "| " + " | ".join(row) + " |")
            map_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return "added a row under the existing table: " + " | ".join(head)
    with open(map_path, "a", encoding="utf-8") as f:
        f.write("\n| Folder | Job | Stage | Due | Dropbox |\n|---|---|---|---|---|\n| %s | %s | %s | %s | %s |\n" % (
            values["folder"], values["job"], values["stage"], values["due"], values["dropbox"]))
    return "no table found; added a new one at the end"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brain", required=True)
    ap.add_argument("--number", required=True)
    ap.add_argument("--client", required=True)
    ap.add_argument("--project", required=True)
    ap.add_argument("--dropbox", default="")
    ap.add_argument("--stage", default="")
    ap.add_argument("--due", default="")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    brain = Path(a.brain)
    upn = brain / "upn"
    name = "%s--%s" % (slug(a.client), slug(a.project))
    folder = upn / "projects" / name
    if folder.exists():
        print("STOP: %s already exists; nothing was changed" % folder)
        return 1
    template = upn / "projects" / "_template"
    if template.is_dir():
        shutil.copytree(template, folder)
    else:
        folder.mkdir(parents=True)
    now = folder / "NOW.md"
    if now.exists():
        print("note: the template already has a NOW.md; left as it is")
    else:
        now.write_text(NOW.format(name=name, number=a.number, today=datetime.date.today().isoformat(),
                                  due=a.due or "(no date given)", folder=folder, dropbox=a.dropbox or "(not given yet)"), encoding="utf-8")
    row = add_map_row(upn / "PROJECT_MAP.md", {"folder": name, "job": a.number, "stage": a.stage, "due": a.due, "dropbox": a.dropbox})
    jp = upn / "job-paths.json"
    try:
        data = json.loads(jp.read_text("utf-8"))
    except Exception:
        data = {}
    data[str(a.number)] = {"folder": name, "dropbox": a.dropbox, "started": datetime.date.today().isoformat()}
    jp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print("job folder: %s" % folder)
    print("NOW file:   %s" % now)
    print("map row:    %s (%s)" % (upn / "PROJECT_MAP.md", row))
    print("recorded:   job %s -> %s ; Dropbox %s (in %s)" % (a.number, name, a.dropbox or "not given", jp))
    return 0


if __name__ == "__main__":
    sys.exit(main())
