"""Register (or remove) the two nightly tasks with Windows Task Scheduler. User level, no administrator rights.

  python register_tasks.py              create "UPN Night Save" (23:00, save) and "UPN Night Notes" (23:20, late)
  python register_tasks.py --dry-run    show what would be created, change nothing
  python register_tasks.py --remove     delete both tasks
  python register_tasks.py --suffix " TEST"   name the tasks with a suffix (for testing)

It writes a task XML for each (so "start when available" and "run if the computer was off at 23:00" are set, which
schtasks /create alone cannot do) and hands it to schtasks /create /xml. The tasks call run-nightly.cmd, which
session start writes into ~/.claude/upn-kit/. They run only while the person is logged in. Nothing is pushed anywhere.
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402

XML = """<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>{desc}</Description></RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-01-01T{time}:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <ExecutionTimeLimit>PT2H</ExecutionTimeLimit>
    <Enabled>true</Enabled>
  </Settings>
  <Actions Context="Author">
    <Exec><Command>{cmd}</Command><Arguments>{arg}</Arguments></Exec>
  </Actions>
</Task>
"""
TASKS = (("UPN Night Save", "23:00", "save", "Logs the day into each job's NOW.md and makes a git save point. Never pushes."),
         ("UPN Night Notes", "23:20", "late", "Indexes Dropbox job folders, writes the day's notes, refreshes brain search."))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--remove", action="store_true")
    ap.add_argument("--suffix", default="")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    cmd = _lib.DATA / "run-nightly.cmd"
    rc = 0
    if _lib.role() == "second" and not a.remove:
        print("Not registering: config.json says role = second. The night save and the night notes run on the main computer only, "
              "so nothing is written into the Dropbox copy of the brain.")
        return 0
    for name, time_, arg, desc in TASKS:
        tn = name + a.suffix
        if a.remove:
            r = subprocess.run(["schtasks", "/delete", "/tn", tn, "/f"], capture_output=True, text=True)
            print("%s: %s %s" % (tn, "removed" if r.returncode == 0 else "FAILED", (r.stdout + r.stderr).strip()))
            rc |= r.returncode
            continue
        if not cmd.is_file():
            print("run-nightly.cmd is missing: start one Claude session with the kit on first (session start writes it)")
            return 1
        xml = XML.format(desc=escape(desc), time=time_, cmd=escape(str(cmd)), arg=escape(arg))
        if a.dry_run:
            print("would create %s at %s: %s %s" % (tn, time_, cmd, arg))
            continue
        f = Path(tempfile.gettempdir()) / ("upn-task-%s.xml" % arg)
        f.write_bytes(b"\xff\xfe" + xml.encode("utf-16-le"))
        r = subprocess.run(["schtasks", "/create", "/tn", tn, "/xml", str(f), "/f"], capture_output=True, text=True)
        print("%s: %s %s" % (tn, "created" if r.returncode == 0 else "FAILED", (r.stdout + r.stderr).strip()))
        rc |= r.returncode
        try:
            f.unlink()
        except OSError:
            pass
    return rc


if __name__ == "__main__":
    sys.exit(main())
