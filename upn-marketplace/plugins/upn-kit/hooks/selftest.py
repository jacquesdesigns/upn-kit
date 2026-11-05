"""Self-test for the UPN kit hooks. Builds a small fake brain in a temp folder, feeds every hook sample JSON on stdin,
and prints one line per case: PASS or FAIL, with the command and what came back. Exit 1 if anything failed.

  python selftest.py            run everything
  python selftest.py --keep     leave the temp folder in place

Nothing outside the temp folder is touched (UPN_KIT_HOME points into it). The model step of the nightly atoms is run
for real only when the `claude` command is signed in; otherwise the "(no model)" fallback is what is tested, and the
line says so.
"""
import json
import re
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable
RESULTS = []


def run_hook(script, payload, env, args=()):
    r = subprocess.run([PY, str(HERE / script)] + list(args), input=json.dumps(payload), capture_output=True, text=True,
                       encoding="utf-8", env=env, timeout=120)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def case(name, cmd, ok, got):
    RESULTS.append((name, cmd, bool(ok), got))
    print("%s  %-44s %s" % ("PASS" if ok else "FAIL", name, got[:150].replace("\n", " ")))


def jl(path, entries):
    with open(path, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")


def tool_use(name, inp, i=1):
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t%d" % i, "name": name, "input": inp}]}}


def text(t):
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": t}]}}


def user(t):
    return {"type": "user", "message": {"content": [{"type": "text", "text": t}]}}


def main():
    keep = "--keep" in sys.argv
    tmp = Path(tempfile.mkdtemp(prefix="upn-kit-selftest-", dir=str(Path.home())))   # not under Temp: the hooks treat Temp as scratch space
    brain = tmp / "Second Brain"
    home = tmp / "kit-home"
    dropbox = tmp / "UrbanPlaceNetwork Dropbox" / "UPN_Server_01" / "0. Projects"
    rawdir = brain / "20. RAW"
    job = brain / "upn" / "projects" / "mohup--oman-aig"
    for d in (brain / "wiki", job / "01 engine-room" / "working", rawdir, dropbox / "10350 MOHUP Oman AIG" / "Issued", home, brain / "_state"):
        d.mkdir(parents=True, exist_ok=True)
    (brain / "CLAUDE.md").write_text("# Brain\nRouter.\n", encoding="utf-8")
    (brain / "wiki" / "index.md").write_text("# Index\n", encoding="utf-8")
    (brain / "wiki" / "oman.md").write_text("---\naliases: [the gulf bid]\n---\n# Oman AIG bid\nWe decided to submit the Oman AIG tender in two parts. It uses a bad \u2014 dash.\n", encoding="utf-8")
    (job / "NOW.md").write_text("# NOW: Oman AIG (job 10350)\n\n## next\n- check the fee table before Friday\n", encoding="utf-8")
    (dropbox / "10350 MOHUP Oman AIG" / "Issued" / "tender.pdf").write_text("x")
    (dropbox / "10350 MOHUP Oman AIG" / "brief.docx").write_text("x")
    mem = tmp / "claude-projects" / "mem"
    mem.mkdir(parents=True)
    (mem / "MEMORY.md").write_text("# Memory\n- [Fees](fees.md)\n- [Bids hub](hub-bids.md)\n", encoding="utf-8")
    (mem / "hub-bids.md").write_text("---\nname: hub-bids\n---\n- [Pre-2021 attribution](bids-pre-2021-attribution.md)\n", encoding="utf-8")
    (mem / "bids-pre-2021-attribution.md").write_text("---\nname: bids-pre-2021-attribution\n---\nPre-May-2021 work carries the old practice name.\n", encoding="utf-8")
    (mem / "stray-fact.md").write_text("---\nname: stray-fact\n---\nListed nowhere.\n", encoding="utf-8")
    (mem / "fees.md").write_text("---\nname: fees\n---\nFee rule: see `upn/projects/gone--away/NOW.md`.\n", encoding="utf-8")
    (brain / "MEMORY.md").write_text("# second index\n", encoding="utf-8")
    cfg = {"brain": str(brain), "memory_dirs": [str(mem)], "dropbox_roots": [str(dropbox)], "context_window": 1000000}
    (home / "config.json").write_text(json.dumps(cfg), encoding="utf-8")
    env = dict(os.environ, UPN_KIT_HOME=str(home), CLAUDE_PLUGIN_ROOT=str(HERE.parent), PYTHONIOENCODING="utf-8")
    sid = "selftest-session-0001"
    tp = tmp / "transcript.jsonl"
    base = {"session_id": sid, "cwd": str(brain), "transcript_path": str(tp)}

    # ---- guards: Dropbox = new files only; 20. RAW = read-only; connector tools
    def guard(label, tool, inp, expect_deny):
        _, out, _ = run_hook("guards.py", dict(base, hook_event_name="PreToolUse", tool_name=tool, tool_input=inp), env)
        denied = '"permissionDecision": "deny"' in out
        case("guards: " + label, "guards.py", denied == expect_deny, ("denied" if denied else "allowed") + " " + out[:70])
    jobd = dropbox / "10350 MOHUP Oman AIG"
    existing = str(jobd / "brief.docx")
    (jobd / "Meeting Notes 2.txt").write_text("old")
    rawfile = rawdir / "source file.pdf"
    rawfile.write_text("raw")
    winnew = "C:\\Users\\james\\UrbanPlaceNetwork Dropbox\\UPN_Server_01\\0. Projects\\10360 WB Albania\\new file.md"
    # allowed in Dropbox
    guard("ALLOW Write a NEW file in a Dropbox job folder", "Write", {"file_path": str(jobd / "Issued" / "new report.md"), "content": "x"}, False)
    guard("ALLOW Write a NEW file, Windows path with spaces", "Write", {"file_path": winnew, "content": "x"}, False)
    guard("ALLOW mkdir of a new Dropbox folder", "PowerShell", {"command": 'mkdir "%s"' % (jobd / "New Sub Folder")}, False)
    guard("ALLOW New-Item -ItemType Directory (new)", "PowerShell", {"command": 'New-Item -ItemType Directory -Path "%s"' % (jobd / "Another New")}, False)
    guard("ALLOW copy a file to a NEW name in Dropbox", "PowerShell", {"command": 'Copy-Item "%s" "%s"' % (job / "NOW.md", jobd / "Issued" / "fresh copy.md")}, False)
    guard("ALLOW cp into a Dropbox folder, name not there yet", "Bash", {"command": 'cp "%s" "%s/"' % (job / "NOW.md", jobd / "Issued")}, False)
    guard("ALLOW redirect into a NEW Dropbox file", "Bash", {"command": 'echo hi > "%s"' % (jobd / "Issued" / "brand new.txt")}, False)
    guard("ALLOW copy OUT of Dropbox", "PowerShell", {"command": 'Copy-Item "%s" "%s"' % (existing, job / "01 engine-room" / "working")}, False)
    guard("ALLOW ls in Dropbox", "Bash", {"command": 'ls "%s"' % dropbox}, False)
    guard("ALLOW Get-Content (read) in 20. RAW", "PowerShell", {"command": 'Get-Content "%s"' % rawfile}, False)
    guard("ALLOW Write in the brain", "Write", {"file_path": str(job / "01 engine-room" / "working" / "draft.md"), "content": "x"}, False)
    # blocked in Dropbox
    guard("BLOCK Write over an existing Dropbox file", "Write", {"file_path": existing, "content": "x"}, True)
    guard("BLOCK Write over existing file with a space in its name", "Write", {"file_path": str(jobd / "Meeting Notes 2.txt"), "content": "x"}, True)
    guard("BLOCK Edit of a Dropbox file", "Edit", {"file_path": existing, "old_string": "a", "new_string": "b"}, True)
    guard("BLOCK Edit, Windows path with spaces", "Edit", {"file_path": "C:\\Users\\james\\UrbanPlaceNetwork Dropbox\\James Rayner\\x.md", "old_string": "a", "new_string": "b"}, True)
    guard("BLOCK MultiEdit of a Dropbox file", "MultiEdit", {"file_path": existing, "edits": [{"old_string": "a", "new_string": "b"}]}, True)
    guard("BLOCK NotebookEdit of a Dropbox file", "NotebookEdit", {"notebook_path": existing, "new_source": "x"}, True)
    guard("BLOCK Bash rm in Dropbox", "Bash", {"command": 'rm -rf "%s"' % jobd}, True)
    guard("BLOCK PowerShell Remove-Item in Dropbox", "PowerShell", {"command": 'Remove-Item "%s" -Recurse' % jobd}, True)
    guard("BLOCK del in Dropbox", "PowerShell", {"command": 'del "%s"' % existing}, True)
    guard("BLOCK mv inside Dropbox", "Bash", {"command": 'mv "%s" "%s"' % (existing, jobd / "moved.docx")}, True)
    guard("BLOCK Move-Item out of Dropbox", "PowerShell", {"command": 'Move-Item "%s" "%s"' % (existing, job)}, True)
    guard("BLOCK Rename-Item in Dropbox", "PowerShell", {"command": 'Rename-Item "%s" "renamed.docx"' % existing}, True)
    guard("BLOCK copy over an existing Dropbox file", "PowerShell", {"command": 'Copy-Item "%s" "%s" -Force' % (job / "NOW.md", existing)}, True)
    (jobd / "NOW.md").write_text("clash")
    guard("BLOCK cp into a folder where that name already exists", "Bash", {"command": 'cp "%s" "%s"' % (job / "NOW.md", jobd)}, True)
    guard("BLOCK robocopy /MIR into Dropbox", "PowerShell", {"command": 'robocopy "%s" "%s" /MIR' % (job, jobd)}, True)
    guard("BLOCK robocopy /PURGE into Dropbox", "PowerShell", {"command": 'robocopy "%s" "%s" /E /PURGE' % (job, jobd)}, True)
    guard("BLOCK plain robocopy into Dropbox", "PowerShell", {"command": 'robocopy "%s" "%s"' % (job, jobd)}, True)
    guard("BLOCK unzip into Dropbox", "Bash", {"command": 'unzip pack.zip -d "%s"' % jobd}, True)
    guard("BLOCK Expand-Archive into Dropbox", "PowerShell", {"command": 'Expand-Archive -Path pack.zip -DestinationPath "%s"' % jobd}, True)
    guard("BLOCK tar -C into Dropbox", "Bash", {"command": 'tar -xf pack.tar -C "%s"' % jobd}, True)
    guard("BLOCK redirect over an existing Dropbox file", "Bash", {"command": 'echo hi > "%s"' % existing}, True)
    guard("BLOCK Set-Content on an existing Dropbox file", "PowerShell", {"command": 'Set-Content "%s" "x"' % existing}, True)
    # 20. RAW: fully read-only
    guard("BLOCK Write a NEW file in 20. RAW", "Write", {"file_path": str(rawdir / "brand new.txt"), "content": "x"}, True)
    guard("BLOCK Write over a file in 20. RAW", "Write", {"file_path": str(rawfile), "content": "x"}, True)
    guard("BLOCK mkdir in 20. RAW", "PowerShell", {"command": 'mkdir "%s"' % (rawdir / "new folder")}, True)
    guard("BLOCK copy a NEW file into 20. RAW", "PowerShell", {"command": 'Copy-Item "%s" "%s"' % (job / "NOW.md", rawdir / "n.md")}, True)
    guard("BLOCK Remove-Item in 20. RAW", "PowerShell", {"command": 'Remove-Item "%s"' % rawfile}, True)
    guard("BLOCK redirect into 20. RAW", "Bash", {"command": 'echo hi > "%s"' % (rawdir / "x.txt")}, True)
    # the person's allow list still works
    cfg_now = json.loads((home / "config.json").read_text("utf-8"))
    cfg_allow = dict(cfg_now, allow=[str(jobd / "Issued")])
    (home / "config.json").write_text(json.dumps(cfg_allow), encoding="utf-8")
    guard("ALLOW-LIST: edit inside a folder the person allowed", "Edit", {"file_path": str(jobd / "Issued" / "tender.pdf"), "old_string": "a", "new_string": "b"}, False)
    (home / "config.json").write_text(json.dumps(cfg_now), encoding="utf-8")
    # the claude.ai Dropbox connector
    for verb in ("list_folder", "search", "fetch", "get_shared_link_metadata", "download_link"):
        guard("CONNECTOR ALLOW %s" % verb, "mcp__claude_ai_Dropbox__" + verb, {"path": "/UPN_Server_01/0. Projects"}, False)
    guard("CONNECTOR ALLOW upload as a NEW file (mode add)", "mcp__claude_ai_Dropbox__upload_file", {"path": "/UPN_Server_01/10350/new.md", "mode": "add", "content": "x"}, False)
    guard("CONNECTOR ALLOW create_folder", "mcp__claude_ai_Dropbox__create_folder", {"path": "/UPN_Server_01/10350/New"}, False)
    guard("CONNECTOR BLOCK upload with no mode (target unknown)", "mcp__claude_ai_Dropbox__upload_file", {"path": "/UPN_Server_01/10350/new.md", "content": "x"}, True)
    guard("CONNECTOR BLOCK upload mode overwrite", "mcp__claude_ai_Dropbox__upload_file", {"path": "/x.md", "mode": "overwrite", "content": "x"}, True)
    for verb in ("move", "delete", "rename", "copy", "restore", "update_file", "move_file", "delete_file"):
        guard("CONNECTOR BLOCK %s" % verb, "mcp__claude_ai_Dropbox__" + verb, {"from_path": "/a", "to_path": "/b", "path": "/a"}, True)
    guard("CONNECTOR BLOCK an unknown tool", "mcp__claude_ai_Dropbox__frobnicate", {"path": "/a"}, True)
    guard("CONNECTOR: non-Dropbox MCP tool untouched", "mcp__claude_ai_Gmail__search_threads", {"query": "x"}, False)

    # ---- voice
    def voice(label, content, path, expect_block):
        _, out, _ = run_hook("voice.py", dict(base, hook_event_name="PostToolUse", tool_name="Write", tool_input={"file_path": path, "content": content}), env)
        blocked = '"decision": "block"' in out
        case("voice: " + label, "voice.py", blocked == expect_block, ("blocked " if blocked else "clean ") + out[:90])
    md = str(brain / "wiki" / "page.md")
    voice("em dash", "This is good \u2014 really.", md, True)
    voice("US spelling", "The color of the street.", md, True)
    voice("double dash", "Wait -- what?", md, True)
    voice("clean British text", "The colour of the street, in the centre of town.", md, False)
    voice("code block ignored", "Fine.\n```\na \u2014 b\n```\n", md, False)
    voice("non-prose file ignored", "a \u2014 b", str(brain / "x.py"), False)

    # ---- proof
    jl(tp, [user("make the file"), tool_use("Write", {"file_path": str(job / "01 engine-room" / "working" / "a.md"), "content": "x"}), text("Done, the file is saved.")])
    _, out, _ = run_hook("proof.py", dict(base, hook_event_name="Stop"), env)
    case("proof: claim without a check", "proof.py", '"decision": "block"' in out, out[:90])
    jl(tp, [user("make the file"), tool_use("Write", {"file_path": str(job / "a.md"), "content": "x"}, 1), tool_use("Read", {"file_path": str(job / "a.md")}, 2), text("Done, the file is saved.")])
    _, out, _ = run_hook("proof.py", dict(base, hook_event_name="Stop"), env)
    case("proof: claim after a check", "proof.py", out == "", out[:90] or "(silent)")
    jl(tp, [user("hello"), text("Hello, I am done reading.")])
    _, out, _ = run_hook("proof.py", dict(base, hook_event_name="Stop"), env)
    case("proof: no change, no flag", "proof.py", out == "", out[:90] or "(silent)")

    # ---- right source
    edit_inp = {"file_path": str(job / "01 engine-room" / "working" / "draft.md"), "old_string": "a", "new_string": "b"}
    jl(tp, [user("edit the draft")])
    _, out, _ = run_hook("right_source.py", dict(base, hook_event_name="PreToolUse", tool_name="Edit", tool_input=edit_inp), env)
    case("right-source: edit without reading NOW", "right_source.py", "deny" in out and "NOW.md" in out, out[:110])
    jl(tp, [user("edit the draft"), tool_use("Read", {"file_path": str(job / "NOW.md")})])
    _, out, _ = run_hook("right_source.py", dict(base, hook_event_name="PreToolUse", tool_name="Edit", tool_input=edit_inp), env)
    case("right-source: edit after reading NOW", "right_source.py", out == "", out[:90] or "(silent)")
    _, out, _ = run_hook("right_source.py", dict(base, hook_event_name="PreToolUse", tool_name="Write", tool_input={"file_path": str(brain / "wiki" / "x.md"), "content": "x"}), env)
    case("right-source: wiki page is not a job folder", "right_source.py", out == "", out[:90] or "(silent)")

    # ---- catch
    _, out, _ = run_hook("catch.py", dict(base, hook_event_name="UserPromptSubmit", prompt="I told you not to use em dashes, from now on stop that"), env)
    case("catch: correction heard", "catch.py", "CATCH" in out and "rules.json" in out, out[:100])
    _, out, _ = run_hook("catch.py", dict(base, hook_event_name="PreToolUse", tool_name="Edit", tool_input=edit_inp), env)
    case("catch: other edit blocked until saved", "catch.py", "deny" in out, out[:100])
    _, out, _ = run_hook("catch.py", dict(base, hook_event_name="PreToolUse", tool_name="Write", tool_input={"file_path": str(home / "rules.json"), "content": "{}"}), env)
    case("catch: saving the rule is allowed", "catch.py", out == "", out[:90] or "(silent)")
    _, out, _ = run_hook("catch.py", dict(base, hook_event_name="PreToolUse", tool_name="Edit", tool_input=edit_inp), env)
    case("catch: edits free again after the rule", "catch.py", out == "", out[:90] or "(silent)")
    _, out, _ = run_hook("catch.py", dict(base, hook_event_name="UserPromptSubmit", prompt="Can you write the summary for the Oman bid?"), env)
    case("catch: ordinary request ignored", "catch.py", out == "", out[:90] or "(silent)")
    (home / "rules.json").write_text(json.dumps({"rules": [{"id": "r1", "pattern": "\\bsynergy\\b", "flags": "i", "reason": "never say synergy"}]}), encoding="utf-8")
    _, out, _ = run_hook("voice.py", dict(base, hook_event_name="PostToolUse", tool_name="Write", tool_input={"file_path": md, "content": "Great synergy here."}), env)
    case("catch: taught rule enforced by voice check", "voice.py", "synergy" in out, out[:100])

    # ---- context
    def fill_entry(tokens):
        return {"type": "assistant", "message": {"usage": {"input_tokens": 10, "cache_read_input_tokens": tokens, "cache_creation_input_tokens": 0}, "content": [{"type": "text", "text": "ok"}]}}
    jl(tp, [user("work"), fill_entry(50000)])
    _, out, _ = run_hook("context.py", dict(base, hook_event_name="UserPromptSubmit", prompt="next"), env)
    case("context: 5% gauge only", "context.py", "5% full" in out and "CONTEXT" not in out, out[:110])
    jl(tp, [user("work"), fill_entry(160000)])
    _, out, _ = run_hook("context.py", dict(base, hook_event_name="UserPromptSubmit", prompt="next"), env)
    states = list((brain / "_state").glob("*.md"))
    case("context: 16% checkpoint saved", "context.py", "checkpoint saved" in out and any("Checkpoint" in s.read_text("utf-8") for s in states), out[:110])
    _, out, _ = run_hook("context.py", dict(base, hook_event_name="UserPromptSubmit", prompt="next"), env)
    case("context: checkpoint warned once", "context.py", "CONTEXT" not in out, out[:110])
    jl(tp, [user("work"), fill_entry(270000)])
    _, out, _ = run_hook("context.py", dict(base, hook_event_name="UserPromptSubmit", prompt="next"), env)
    st = "".join(s.read_text("utf-8") for s in (brain / "_state").glob("*.md"))
    case("context: 27% handover note + new conversation", "context.py", "start a new conversation" in out.lower() and "OPEN: next =" in st, out[:130])
    clock_ok = bool(re.search(r"time now \d\d:\d\d \(local\)", out)) and "never write a time you did not read" in out
    case("context: the clock on the gauge and in the handover text", "context.py", clock_ok, out[:130])
    case("context: OPEN line names the live thing first; the message just sent goes in it", "context.py",
         "FIRST, then" in out and "do not start it here" in out, out[:130])
    long_msg = "keep the purple header exactly as it is, " * 8 + "and send nothing"
    jl(tp, [user("first ask"), user(long_msg), fill_entry(270000)])
    _lib_flag = home / "sessions"
    for f in (_lib_flag.glob("*-warned.json") if _lib_flag.is_dir() else []):
        f.unlink()
    for s in (brain / "_state").glob("*.md"):
        s.unlink()
    _, out, _ = run_hook("context.py", dict(base, hook_event_name="UserPromptSubmit", prompt="now the footer"), env)
    st = "".join(s.read_text("utf-8") for s in (brain / "_state").glob("*.md"))
    case("context: last three messages kept word for word", "context.py",
         "last three (verbatim)" in st and long_msg in st and "> now the footer" in st and "> first ask" in st, st[-130:].replace("\n", " "))
    jl(tp, [user("hello")])
    _, out, _ = run_hook("context.py", dict(base, hook_event_name="UserPromptSubmit", prompt="next"), env)
    case("context: time given even before the first reply", "context.py", bool(re.search(r"Time now: \d\d:\d\d", out)), out[:110])

    # ---- closeout stop
    jl(tp, [user("write")] + [tool_use("Write", {"file_path": str(job / ("a%d.md" % i)), "content": "x"}, i) for i in range(1, 4)] + [text("ok")])
    _, out, _ = run_hook("closeout_stop.py", dict(base, hook_event_name="Stop"), env)
    case("close-out: offered after 3 saves", "closeout_stop.py", "CLOSE-OUT" in out, out[:110])
    _, out, _ = run_hook("closeout_stop.py", dict(base, hook_event_name="Stop"), env)
    case("close-out: offered only once", "closeout_stop.py", out == "", out[:90] or "(silent)")

    # ---- routing
    _, out, _ = run_hook("routing.py", dict(base, hook_event_name="PreToolUse", tool_name="Agent", tool_input={"subagent_type": "Explore", "prompt": "find"}), env)
    case("routing: Explore goes to haiku", "routing.py", '"model": "haiku"' in out, out[:110])
    _, out, _ = run_hook("routing.py", dict(base, hook_event_name="PreToolUse", tool_name="Agent", tool_input={"subagent_type": "Explore", "model": "opus", "prompt": "find"}), env)
    case("routing: a model named by the person wins", "routing.py", out == "", out[:90] or "(silent)")

    # ---- index, look-first, search
    r = subprocess.run([PY, str(HERE / "brainsearch" / "index.py")], capture_output=True, text=True, encoding="utf-8", env=env)
    case("brain-search: index builds", "index.py", r.returncode == 0 and "Indexed" in r.stdout, r.stdout.strip()[:100] + r.stderr.strip()[:100])
    r = subprocess.run([PY, str(HERE / "brainsearch" / "search.py"), "Oman tender"], capture_output=True, text=True, encoding="utf-8", env=env)
    case("brain-search: search finds the wiki + NOW", "search.py", "oman.md" in r.stdout and "NOW.md" in r.stdout, r.stdout.strip()[:120].replace("\n", " "))
    r = subprocess.run([PY, str(HERE / "brainsearch" / "search.py"), "gulf bid"], capture_output=True, text=True, encoding="utf-8", env=env)
    case("brain-search: frontmatter alias finds it", "search.py", "oman.md" in r.stdout, r.stdout.strip()[:100].replace("\n", " "))
    _, out, _ = run_hook("brainsearch/lookfirst.py", dict(base, hook_event_name="UserPromptSubmit", prompt="what did we decide about the Oman tender?"), env)
    case("look-first: past question gets hits", "lookfirst.py", "LOOK FIRST" in out, out[:110])
    _, out, _ = run_hook("brainsearch/lookfirst.py", dict(base, hook_event_name="UserPromptSubmit", prompt="write me a new paragraph"), env)
    case("look-first: ordinary request silent", "lookfirst.py", out == "", out[:90] or "(silent)")

    # ---- doctor + session start
    r = subprocess.run([PY, str(HERE / "doctor.py")], capture_output=True, text=True, encoding="utf-8", env=env)
    case("doctor: two indexes + dead path + em dash", "doctor.py", r.returncode == 0 and "two indexes" in r.stdout and "gone" in r.stdout and "em dash" in r.stdout, r.stdout.strip()[:140].replace("\n", " | "))
    orphan = [l for l in r.stdout.splitlines() if "not in the index" in l]
    case("doctor: a fact listed in a hub is not an orphan", "doctor.py", orphan and "bids-pre-2021-attribution" not in orphan[0] and "hub-bids" not in orphan[0], (orphan or ["(no orphan line)"])[0][:140])
    case("doctor: a file in no index and no hub is still flagged", "doctor.py", orphan and "stray-fact.md" in orphan[0], (orphan or ["(no orphan line)"])[0][:140])
    (brain / "_state" / "2026-10-20-oldhand.md").write_text("# Old job\nOPEN: next = send the fee table\n- a fact\n", encoding="utf-8")
    _, out, _ = run_hook("session_start.py", dict(base, hook_event_name="SessionStart", source="startup", cwd=str(job)), env)
    ok = "JOB IN HAND" in out and "check the fee table" in out and "HANDOVER IS WAITING" in out and "DOCTOR" in out
    case("session-start: NOW + handover + doctor", "session_start.py", ok, out[:130])
    taken = "TAKEN:" in (brain / "_state" / "2026-10-20-oldhand.md").read_text("utf-8")
    case("session-start: handover offered once (marked TAKEN)", "session_start.py", taken, "TAKEN" if taken else "not marked")
    case("session-start: shim + kit_root written", "session_start.py", (home / "run-nightly.py").exists() and json.loads((home / "config.json").read_text("utf-8")).get("kit_root"), str(home / "run-nightly.py"))

    # ---- nightly
    r = subprocess.run([PY, str(HERE / "nightly.py"), "storage"], capture_output=True, text=True, encoding="utf-8", env=env)
    sfile = list((home / "storage").glob("*.md"))
    body = sfile[0].read_text("utf-8") if sfile else ""
    case("nightly storage: index of Dropbox job folders", "nightly.py storage", "10350 MOHUP Oman AIG" in body and "pdf 1" in body, r.stdout.strip()[:100])
    case("nightly storage: contents never read", "nightly.py storage", "x" not in body.split("tender.pdf")[-1][:0] and "tender.pdf" not in body, "file names are not listed")
    today = time.strftime("%Y-%m-%d")
    ts = time.strftime("%Y-%m-%dT%H:%M:%S%z") or ""
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    proj = tmp / "fake-home" / ".claude" / "projects" / "p1"
    proj.mkdir(parents=True)
    conv = [{"type": "user", "timestamp": stamp, "message": {"content": "Please find the fee table for the Oman tender and check the totals add up " * 3}},
            {"type": "assistant", "timestamp": stamp, "message": {"content": [{"type": "text", "text": "I opened the fee table and the totals add up to the quoted fee. " * 3}]}}]
    jl(proj / "abcd1234-0000.jsonl", conv)
    cfg2 = json.loads((home / "config.json").read_text("utf-8")); cfg2["transcript_dirs"] = [str(proj)]
    (home / "config.json").write_text(json.dumps(cfg2), encoding="utf-8")
    r = subprocess.run([PY, str(HERE / "nightly.py"), "atoms", today], capture_output=True, text=True, encoding="utf-8", env=env)
    afile = home / "atoms" / ("%s.md" % today)
    abody = afile.read_text("utf-8") if afile.exists() else ""
    model = "(no model)" not in abody
    case("nightly atoms: line written for the conversation", "nightly.py atoms", "abcd1234" in abody, r.stdout.strip()[:90] + (" [model call ran]" if model else " [fallback: (no model)]"))
    subprocess.run([PY, str(HERE / "brainsearch" / "index.py"), "--quiet"], env=env)
    r = subprocess.run([PY, str(HERE / "brainsearch" / "search.py"), "fee table totals"], capture_output=True, text=True, encoding="utf-8", env=env)
    case("nightly atoms: fed into brain-search", "search.py", "atoms" in r.stdout, r.stdout.strip()[:100].replace("\n", " "))
    r = subprocess.run([PY, str(HERE / "nightly.py"), "summaries"], capture_output=True, text=True, encoding="utf-8", env=env)
    case("nightly summaries: runs, fallback safe", "nightly.py summaries", r.returncode == 0 and "summaries" in r.stdout, r.stdout.strip()[:100])
    # night save in a real git repo
    if shutil.which("git"):
        subprocess.run(["git", "init", "-q", str(brain)], capture_output=True)
        (brain / "_state" / ("%s-abcd1234.md" % today)).write_text("# Oman AIG fee table checked\nOPEN: next = send\n", encoding="utf-8")
        r = subprocess.run([PY, str(HERE / "nightly.py"), "save", today], capture_output=True, text=True, encoding="utf-8", env=env)
        log = subprocess.run(["git", "-C", str(brain), "log", "--oneline"], capture_output=True, text=True).stdout
        nowtxt = (job / "NOW.md").read_text("utf-8")
        case("nightly save: commit + NIGHT LOG, no push", "nightly.py save", "Night save" in log and "NIGHT LOG" in nowtxt, r.stdout.strip()[:100] + " | " + log.strip()[:50])
        pushed = subprocess.run(["git", "-C", str(brain), "remote"], capture_output=True, text=True).stdout.strip()
        case("nightly save: nothing pushed (no remote touched)", "git remote", pushed == "", "no remote configured")
    else:
        case("nightly save", "git", False, "git is not installed")

    # ---- job start
    r = subprocess.run([PY, str(HERE.parent / "skills" / "job-start" / "scripts" / "jobstart.py"), "--brain", str(brain), "--number", "10360", "--client", "WB", "--project", "Albania Tourism", "--dropbox", str(dropbox / "10360 WB Albania")],
                       capture_output=True, text=True, encoding="utf-8", env=env)
    ok = (brain / "upn" / "projects" / "wb--albania-tourism" / "NOW.md").exists() and "10360" in (brain / "upn" / "PROJECT_MAP.md").read_text("utf-8") and "10360" in (brain / "upn" / "job-paths.json").read_text("utf-8")
    case("job-start: folder, NOW, map row, path recorded", "jobstart.py", ok, r.stdout.strip()[:100].replace("\n", " | "))
    r = subprocess.run([PY, str(HERE.parent / "skills" / "job-start" / "scripts" / "jobstart.py"), "--brain", str(brain), "--number", "10360", "--client", "WB", "--project", "Albania Tourism"], capture_output=True, text=True, encoding="utf-8", env=env)
    case("job-start: refuses to overwrite", "jobstart.py", "STOP" in r.stdout, r.stdout.strip()[:80])

    # ---- the Dropbox copy of the brain: the mirror keeps working, and a second computer stays out of the way
    cfg_main = json.loads((home / "config.json").read_text("utf-8"))
    mirror = tmp / "UrbanPlaceNetwork Dropbox" / "Jeremy Salmon" / "second-brain-mirror"
    (mirror / "wiki").mkdir(parents=True)
    (mirror / "wiki" / "index.md").write_text("# mirrored index\n", encoding="utf-8")
    (mirror / "_MIRROR-HOLD.txt").write_text("held", encoding="utf-8")
    (home / "config.json").write_text(json.dumps(dict(cfg_main, allow=[str(mirror)])), encoding="utf-8")
    guard("MIRROR: edit an existing file inside the allowed mirror folder", "Edit", {"file_path": str(mirror / "wiki" / "index.md"), "old_string": "a", "new_string": "b"}, False)
    guard("MIRROR: robocopy /MIR brain to the mirror (the scheduled copy)", "PowerShell", {"command": 'robocopy "%s" "%s" /MIR /R:1 /W:1' % (brain, mirror)}, False)
    guard("MIRROR: robocopy the mirror back to the brain (pull back)", "PowerShell", {"command": 'robocopy "%s" "%s" /E' % (mirror, brain)}, False)
    guard("MIRROR: running the mirror script does not trip the guard", "PowerShell", {"command": '& "%s\\_context\\dropbox-mirror\\sync-to-dropbox.ps1"' % brain}, False)
    guard("MIRROR: robocopy /MIR into ANOTHER Dropbox folder is still blocked", "PowerShell", {"command": 'robocopy "%s" "%s" /MIR' % (brain, dropbox / "10350 MOHUP Oman AIG")}, True)
    guard("MIRROR: server files stay protected", "Edit", {"file_path": existing, "old_string": "a", "new_string": "b"}, True)
    (home / "config.json").write_text(json.dumps(cfg_main), encoding="utf-8")
    # a brain opened FROM a Dropbox path (the person's other computer)
    dbrain = tmp / "UrbanPlaceNetwork Dropbox" / "James Rayner" / "Second Brain"
    for d in (dbrain / "wiki", dbrain / "upn" / "projects" / "x--y", dbrain / "20. RAW"):
        d.mkdir(parents=True)
    (dbrain / "CLAUDE.md").write_text("# Brain\n", encoding="utf-8")
    (dbrain / "wiki" / "page.md").write_text("# Page\n", encoding="utf-8")
    (dbrain / "wiki" / "index.md").write_text("# Index\n", encoding="utf-8")
    (dbrain / "upn" / "projects" / "x--y" / "NOW.md").write_text("# NOW: x\n", encoding="utf-8")
    (dbrain / "20. RAW" / "src.pdf").write_text("raw", encoding="utf-8")
    cfg_db = dict(cfg_main, brain=str(dbrain), memory_dirs=[str(mem)], role="second")
    (home / "config.json").write_text(json.dumps(cfg_db), encoding="utf-8")
    base_db = dict(base, cwd=str(dbrain), session_id="selftest-dropbox-brain")

    def guard_db(label, tool, inp, expect_deny):
        _, out, _ = run_hook("guards.py", dict(base_db, hook_event_name="PreToolUse", tool_name=tool, tool_input=inp), env)
        denied = '"permissionDecision": "deny"' in out
        case("guards: " + label, "guards.py", denied == expect_deny, ("denied" if denied else "allowed") + " " + out[:70])
    guard_db("DROPBOX BRAIN: edit an existing wiki page", "Edit", {"file_path": str(dbrain / "wiki" / "page.md"), "old_string": "a", "new_string": "b"}, False)
    guard_db("DROPBOX BRAIN: Write over an existing file in the brain", "Write", {"file_path": str(dbrain / "wiki" / "index.md"), "content": "x"}, False)
    guard_db("DROPBOX BRAIN: shell redirect over a brain file", "PowerShell", {"command": 'Set-Content "%s" "x"' % (dbrain / "wiki" / "page.md")}, False)
    guard_db("DROPBOX BRAIN: 20. RAW inside it stays read-only", "Write", {"file_path": str(dbrain / "20. RAW" / "new.txt"), "content": "x"}, True)
    guard_db("DROPBOX BRAIN: Remove-Item in 20. RAW still blocked", "PowerShell", {"command": 'Remove-Item "%s"' % (dbrain / "20. RAW" / "src.pdf")}, True)
    guard_db("DROPBOX BRAIN: server files outside the brain still protected", "Edit", {"file_path": existing, "old_string": "a", "new_string": "b"}, True)
    guard_db("DROPBOX BRAIN: a NEW server file is still allowed", "Write", {"file_path": str(jobd / "Issued" / "from the dropbox brain.md"), "content": "x"}, False)
    # role second: no git, no night notes, state and index outside Dropbox
    r = subprocess.run([PY, str(HERE / "nightly.py"), "save", today], capture_output=True, text=True, encoding="utf-8", env=env)
    case("second machine: night save skipped, no .git created", "nightly.py save", "skipped" in r.stdout and not (dbrain / ".git").exists(), r.stdout.strip()[:100])
    r = subprocess.run([PY, str(HERE / "nightly.py"), "atoms", today], capture_output=True, text=True, encoding="utf-8", env=env)
    case("second machine: atoms skipped", "nightly.py atoms", "skipped" in r.stdout, r.stdout.strip()[:100])
    r = subprocess.run([PY, str(HERE / "register_tasks.py")], capture_output=True, text=True, encoding="utf-8", env=env)
    case("second machine: tasks not registered", "register_tasks.py", "Not registering" in r.stdout, r.stdout.strip()[:100])
    jl(tp, [user("work"), fill_entry(160000)])
    before = set(p.name for p in (dbrain.glob("**/*")))
    _, out, _ = run_hook("context.py", dict(base_db, transcript_path=str(tp), hook_event_name="UserPromptSubmit", prompt="next"), env)
    after = set(p.name for p in (dbrain.glob("**/*")))
    case("second machine: checkpoint written outside the Dropbox brain", "context.py", (home / "state").is_dir() and any((home / "state").glob("*.md")) and before == after, "state in %s; brain unchanged: %s" % (home / "state", before == after))
    r = subprocess.run([PY, str(HERE / "brainsearch" / "index.py"), "--full"], capture_output=True, text=True, encoding="utf-8", env=env)
    case("second machine: search index lives in the kit folder, not Dropbox", "index.py", (home / "brain.db").exists() and not list(dbrain.glob("**/brain.db")), r.stdout.strip()[:100])
    _, out, _ = run_hook("session_start.py", dict(base_db, hook_event_name="SessionStart", source="startup"), env)
    case("second machine: session start works in the Dropbox brain", "session_start.py", "JOB IN HAND" in out and not list(dbrain.glob("**/_state")), out[:100])
    (home / "config.json").write_text(json.dumps(cfg_main), encoding="utf-8")

    fails = [x for x in RESULTS if not x[2]]
    print("\n%d cases, %d passed, %d failed" % (len(RESULTS), len(RESULTS) - len(fails), len(fails)))
    if keep:
        print("kept: " + str(tmp))
    else:
        shutil.rmtree(tmp, ignore_errors=True)
    return 1 if fails else 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main())
