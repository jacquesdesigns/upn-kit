# TESTS: UPN kit, 25 Oct 2026 (v1.0.0), retested 5 Nov 2026 (v1.1.0, then v1.1.1)

Where each test ran is stated on its line. Mac is the build machine. PC is the studio Windows PC (Windows, PowerShell over ssh, user claude-remote, non-admin, Python 3.13.15, Node 24, Git 2.55). A failure stays a failure.

## 5 Nov 2026: v1.2.0 (part A: six small hook gaps)

What changed: gaps 1, 2, 3, 6, 9 and 10 from the 5 Nov audit of our own system against the kit (`kit/system-vs-kit-2026-11-05.html`, "Portable and missing"). The version is not bumped here; part B bumps it. The self-test has 151 cases (133 before, plus 18 new "v12" cases; one existing case changed, see gap 3). Every new case except one was run against the v1.1.1 hooks first and failed there: 15 FAIL. The exception, "catch silent on a subagent report", already passed in v1.1.1 and stays as a guard.

| Gap | Where | Command | Result |
|---|---|---|---|
| 1. Night save takes new .ps1 .bat .cmd .js .css .sh .svg .jsonl files (`nightly.py` TEXT) | Mac | selftest.py: "v12 night save: new .ps1 .bat .cmd .js .css .sh .svg .jsonl committed" | PASS (v1.1.1: all eight missing) |
| 2. One machine-message pattern, `_lib.MACHINE` / `_lib.is_machine`, used by `lookfirst.py` and `catch.py`: subagent reports, task notifications, hook output, compaction summaries | Mac | selftest.py: "v12 machine: ..." (shared pattern; look-first and catch each silent on a task notification, a compaction summary, hook output and a subagent report, edits free; the person's own correction still caught) | PASS, 10 cases |
| 3. `session_start.py`: a job is in hand only from the folder the conversation was opened in; at the root it loads none and lists the recent jobs ("NO JOB LOADED ... RECENT JOBS") | Mac | selftest.py: "v12 session-start: at the root, no job in hand, recent jobs listed", "v12 session-start: opened inside a job folder, that job is in hand". The existing case "second machine: session start works in the Dropbox brain" opens at the root, so it now checks for RECENT JOBS instead of JOB IN HAND | PASS |
| 6. `CLAUDE-SNIPPET.md`: one helper agent gets about five changes; a new ask during its run goes to a fresh agent | Mac | selftest.py: "v12 snippet: about five changes per helper agent, new ask to a fresh one" | PASS |
| 9. Each LOOK FIRST block adds one line to `lookfirst-hits.log` in the kit folder (`~/.claude/upn-kit/`); Prompt 2 Step 7 puts its count in the report ("look-first blocks: n") | Mac | selftest.py: "v12 hits: a LOOK FIRST block adds one line to the hits log", "v12 hits: a silent prompt adds nothing", "v12 hits: Prompt 2 report zip carries the look-first count" | PASS |
| 10. Night save: a job word after "not", "isn't", "apart from", "nothing to do with" (also "except", "other than", "aside from", "without") does not tie a day to that job | Mac | selftest.py: "v12 night save: \"not the Oman job\" is not logged under Oman" | PASS (v1.1.1 logged all three titles under Oman) |
| Full self-test | Mac (Python 3.15) | python3 selftest.py | PASS, 151 of 151 |
| Same self-test | PC | python selftest.py | NOT RUN: part B runs the PC pass after the merge |

## 5 Nov 2026: v1.2.0, part B (gaps 4, 5, 7, 8 of the 5 Nov system audit)

What changed: four pieces carried from our own system. The job's NOW file is kept fresh during the day, a long file is not read in full twice, and the doctor gains two checks. Part B adds 21 self-test cases.

| Fix | Where | Command | Result |
|---|---|---|---|
| 4. New `hooks/latest.py` (PostToolUse on Write, Edit, MultiEdit, Bash, PowerShell): each write to this conversation's own notes file copies its title, OPEN / NOW / GATE / WAITING lines and six newest facts into the job's NOW.md as one "## LATEST (auto ...)" section, replaced in place. The job is the NOW.md of the folder opened, else of the newest file the conversation wrote; never the brain root, never from a subagent or another conversation's notes | Mac | selftest.py: "latest: notes copied into the NOW of the folder opened", "latest: replaced in place, never added twice (shell write)", "latest: other files and other conversations' notes leave NOW alone", "latest: opened at the root, the job comes from the files written", "latest: nothing written at the brain root" | PASS |
| 5. `hooks/guards.py` refuses a full Read of a file over 30 KB this conversation already read, unless it changed since (size or time) or a line range is asked; a compaction or a clear empties the list (a SessionStart hook with matcher clear\|compact); a subagent keeps its own list. Our artifact half left out | Mac | selftest.py: ten "re-read:" cases (first read, second refused, the refusal says what to do, line range, small file twice, changed file, refused again, after a compaction, subagent) | PASS |
| 7. `hooks/doctor.py` warns (AMBER) when a NOW.md has more than about 40 hand-written lines above its machine sections; the LATEST section and the NIGHT LOG are not counted | Mac | selftest.py: "doctor: a NOW file past 40 hand-written lines is warned", "doctor: LATEST and NIGHT LOG lines are not counted" | PASS |
| 8. `hooks/doctor.py` goes RED on untracked tooling files (scripts and settings) the night save will not commit, reading TEXT, BIG and NEVER_COMMIT from nightly.py's source with ast, so the two cannot drift | Mac | selftest.py: "doctor: an untracked script the night save leaves out is red", "doctor: a type the night save takes is not flagged", "doctor: the type list is read from nightly.py, not a copy", "doctor: reads the real nightly.py list as it stands" | PASS |
| Part B self-test before the merge with part A | Mac | python3 selftest.py | PASS, 154 of 154 |

## 5 Nov 2026: v1.1.1

What changed: seven things found when Prompts 1 and 2 were run end to end in VS Code on the PC. Version 1.1.0 to 1.1.1. The self-test has 133 cases (126 before, plus 7 new ones below).

| Fix | Where | Command | Result |
|---|---|---|---|
| 1. doctor no longer goes red on the hub layout Prompt 1 sets up: a fact file named in a hub that the index names counts as indexed; a file named nowhere is still flagged | Mac, PC | selftest.py: "doctor: a fact listed in a hub is not an orphan", "doctor: a file in no index and no hub is still flagged" | PASS on both |
| 2. voice check: a double dash inside a path (`client--project` folders, a Windows path with a space such as `Second Brain`) is not a fault; a double dash between words in prose still is | Mac, PC | selftest.py: three new voice cases. The 1.1.0 check, given the same two paths, returned "double dash" for both | PASS on both |
| 3. Prompt 1: "which computer is which" is now Step 1, so the role is set before the save point (now Step 1b) reads it | Mac | read the step headings in order: Step 0, Step 1 which computer, Step 1b save point | PASS |
| 4. Prompts 1 and 2: anything I have to type (`/context`, `/reload-plugins`, a name, a path) is asked in plain text, "type it, then tell me", never in a question form that hides the box | Mac | read the rules list of both prompts and Prompt 2 Steps 3 and 4 | PASS (wording only; not run in a live Claude) |
| 5. Prompt 2: frontend-design comes from the built-in marketplace `anthropic-plugin-directory` | Mac (claude 2.1.318) | claude plugin marketplace list (shows "anthropic-plugin-directory, Built in"); claude plugin details frontend-design@anthropic-plugin-directory (found, 1.1.1) | PASS |
| 6a. Prompts call schtasks through PowerShell, because Git Bash rewrites `/query` | PC, Git Bash 2.55 | plain `schtasks /query` in Git Bash: "Invalid argument/option - 'C:/Program Files/Git/query'"; `cmd.exe /c "schtasks ..."` also fails (opens a cmd prompt); `powershell -NoProfile -Command "schtasks /query /tn '...' /fo list"` works in Git Bash and in PowerShell | PASS |
| 6b. doctor reads the mirror task with `schtasks /query /tn <name> /v /fo csv`, not Get-ScheduledTaskInfo; robocopy results 1 to 7 count as fine, as its message always said | PC, non-admin over ssh | doctor.py with a real task name: 1.1.0 printed "could not read the Dropbox mirror task"; 1.1.1 read its last result (-2147160572, the same as schtasks shows). selftest.py: two new cases on the csv reader (day-first date, never-ran task) | PASS on both |
| 7. Version 1.1.1 in both manifests; full self-test | Mac (claude 2.1.318) | claude plugin validate on both manifests; python3 selftest.py | PASS, 133 of 133 |
| Same self-test | PC, kit copied to C:\Users\claude-remote\upn-kit-test\upn-kit-111 | python selftest.py | PASS, 133 of 133 |

## 5 Nov 2026: v1.1.0

What changed: the handover hooks (`context.py`, `session_start.py`) carry four fixes from our own tools since 25 Oct. The gauge line and the checkpoint and handover texts carry the local time, so Claude never invents a time in a note. The handover note keeps the person's last three messages word for word (it kept 160 characters of each). The OPEN line names the file, page or link to open first, and the next conversation carries on on it, with no new options and no restart. At the handover line the message just sent becomes the next step in the OPEN line instead of being started in a full conversation. Version 1.0.0 to 1.1.0. Delivery moves from an emailed zip (stopped by UPN's mail filter, 5 Nov) to a private git repo, with the zip kept as a fallback.

| Piece | Where | Command | Result |
|---|---|---|---|
| Full self-test, 126 cases (122 as before, plus 4 new context cases: clock, OPEN names the live thing, last three verbatim, time before the first reply) | Mac | python3 selftest.py | PASS, 126 of 126 |
| Same | PC, kit copied to C:\Users\claude-remote\upn-kit-test\upn-kit | python selftest.py | PASS, 126 of 126 |
| Marketplace manifest and plugin manifest valid | Mac (claude 2.1.318), PC (claude 2.1.310) | claude plugin validate upn-marketplace ; claude plugin validate upn-marketplace\plugins\upn-kit | PASS on both |
| New upn-kit.zip (v1.1.0, 83 files, no macOS extras, no __pycache__) unzipped with Expand-Archive, then validated | PC | claude plugin validate on both manifests | PASS |
| Install from a git clone of the repo | not run | git clone, then Prompt 2 Step 3 | NOT VERIFIED: the repo was not created in this run (see the report) |

## Summary

| Piece | Where | Command | Result |
|---|---|---|---|
| Marketplace manifest valid | Mac, PC | claude plugin validate upn-marketplace | PASS |
| Plugin manifest valid (12 skills, 3 agents, 5 hook events found) | Mac, PC | claude plugin validate .../upn-kit ; claude plugin details upn-kit | PASS |
| Add marketplace + install plugin from the unzipped kit | PC (claude 2.1.310 installed with npm into the user prefix) | claude plugin marketplace add ; claude plugin install upn-kit@upn-marketplace | PASS, status enabled |
| Hook command line works with a backslash path containing spaces | PC | hooks.json guards command, expanded, via cmd.exe and via Git Bash | PASS (deny returned, exit 0) |
| python missing falls back to py | PC | same command with a broken python name | PASS (py launcher used) |
| guards, revised rule: Dropbox allows NEW files and folders only; 20. RAW fully read-only (50 cases: new file, mkdir, copy to a new name, redirect to a new file allowed; Write/Edit/MultiEdit/NotebookEdit of existing, rm, del, mv, Move-Item, Rename-Item, copy over, robocopy plain and /MIR and /PURGE, unzip, Expand-Archive, tar into Dropbox, redirect over existing blocked; anything in 20. RAW that writes blocked, reads allowed; the config allow list honoured; Windows paths with spaces) | Mac, PC | selftest.py | PASS |
| Dropbox copy of the brain (mirror) and second computer: edit inside an allowed mirror folder, robocopy /MIR brain to mirror and mirror back to brain allowed, robocopy /MIR into any other Dropbox folder blocked; a brain opened from a Dropbox path can be edited normally while its 20. RAW and the rest of Dropbox stay protected; role second: night save, atoms and task registration refuse, no .git is made, checkpoints go to the kit folder not the brain, the search index lives in the kit folder | Mac, PC | selftest.py (19 cases) | PASS |
| guards, claude.ai Dropbox connector (mcp__claude_ai_Dropbox__*): list, search, fetch, get_shared_link_metadata, download_link, upload with mode add, create_folder allowed; upload with no mode or mode overwrite, move, delete, rename, copy, restore, update_file and an unknown tool blocked; other MCP tools untouched | Mac, PC | selftest.py | PASS. The connector's real tool names were not available to me (only five read tools appear in the reports), so the verbs are matched by name pattern, and anything unrecognised is blocked |
| voice check: em dash, US spelling, double dash, taught rule; code and non-prose ignored | Mac, PC | selftest.py | PASS |
| proof: claim without a check flagged; after a check silent; no change silent | Mac, PC | selftest.py | PASS |
| right-source: NOW file must be read first | Mac, PC | selftest.py | PASS |
| catch: correction heard, other edits blocked until the rule is saved, then freed | Mac, PC | selftest.py | PASS |
| context: gauge, 15% checkpoint written, once only, 25% handover note with OPEN line | Mac, PC | selftest.py | PASS |
| session start: NOW file, waiting handover (marked TAKEN), doctor lines, shim + kit_root | Mac, PC | selftest.py | PASS |
| close-out Stop reminder: once, after 3 saves | Mac, PC | selftest.py | PASS |
| model routing: Explore to haiku; a named model wins | Mac, PC | selftest.py | PASS |
| doctor-lite: two indexes, dead memory path, em dash in wiki page | Mac, PC | selftest.py | PASS |
| brain-search: index, ranked search, frontmatter alias, look-first hook | Mac, PC | selftest.py | PASS |
| job-start: folder, NOW, map row, path recorded; refuses to overwrite | Mac, PC | selftest.py | PASS |
| Night save: NIGHT LOG into NOW, git commit, nothing pushed | Mac, PC | selftest.py; then run-nightly.cmd save on PC | PASS |
| Storage index of Dropbox job folders (names, dates, counts; no file names or contents) | Mac, PC | selftest.py; run-nightly.cmd late | PASS |
| Atoms: line per conversation, fed into search | Mac (real Haiku call ran), PC (fallback "(no model)" only) | selftest.py | PASS on Mac with the model; PC fallback only: see Not verified |
| Task Scheduler registration (user level, no admin, start when available) | PC | register_tasks.py --dry-run, create, query /xml, --remove | PASS (StartWhenAvailable true; both tasks deleted afterwards) |
| Studio check kit runs on the sample page | Mac (venv), PC (new venv, Playwright, Chromium) | studio_check.py --job sample --quick | PASS, same result on both: 30 pass, 3 fail, 43 skip, 0 error. The 3 fails are real findings on the sample page (display-to-body ratio 2.22 against a minimum of 3), not kit faults |

Full self-test: 122 cases, 122 passed on Mac; 122 cases, 122 passed on PC (below). Validate and install were re-run on the PC after the guard change: PASS.

Revision 25 Oct, later: Louis changed the Dropbox rule from read-only to new-files-only. The self-test now has 122 cases (was 54, then 103 after the Dropbox rule, then 19 more for the mirror and second-computer cases).

## Not verified, and why

1. **Hooks firing inside a live Claude Code session** (including the new MCP matcher for the Dropbox connector, whose real tool names and inputs I could not see). The PC's Claude is not signed in (claude -p says "Not logged in"). Every hook was fed sample hook JSON on stdin and its output and exit code checked, through the real command line from hooks.json, but not driven by a running Claude. One sign-in at the PC (claude /login as claude-remote) would let a headless run check it end to end.
2. **Nightly Haiku step on the PC** (atoms and summaries): needs the same sign-in. The fallback line ("(no model)") is tested on the PC; the model call itself ran for real on the Mac (atoms). The summaries model path found no long files in the sample brain, so its model call has not been exercised on either machine.
3. **The scheduler actually launching the tasks.** schtasks /run returned "attempted" but Last Result was 267011 (never ran): claude-remote has no interactive logon session, and the tasks are set to run only when the user is logged on. The exact command the task runs (run-nightly.cmd save, then late) was run by hand on the PC and passed. Whether Task Scheduler fires it at 23:00 for James and Jeremy is untested.
4. **PROMPT-1 and PROMPT-2 as written.** They need Claude and the clients' own machines. Not run end to end. Their parts were tested one by one (git save point, install, selftest, task registration), not as a sequence.
5. **Memory reshape, mirror edit, lean pass (PROMPT-1).** Instructions only; these touch the clients' data and need their yes.
6. **Studio skills content.** Structure is validated; the skills were not run through a full /studio job. The check kit is tested as above; capture_site.py, cosmos.py and contact_sheet.py were not run on the PC (they need live sites). They were compile-checked only.
7. **Windows execution policy:** npm.ps1 is blocked on this PC ("running scripts is disabled"), so npm must be called as npm.cmd. PROMPT-2 now says so.
8. **Context window default** is 1,000,000 until PROMPT-2 asks the person for the number shown by /context.

9. **The mirror itself.** The tests use a stand-in mirror folder and robocopy command lines; Jeremy's and James's real scripts and tasks were not run or changed. The "allow" entry for the mirror folder is written by PROMPT-1 Step 3 on their machines.
10. **How they use the second computer** (open the Dropbox copy, or pull it back) is not known to us; PROMPT-1 asks and records it as role and second_use.

## Findings during testing (all fixed before the final run)

- Hook guard did not treat a Mac absolute path as a path argument (options starting with a slash were treated as switches); fixed with an explicit switch test.
- The self-test used the system Temp folder, which the hooks deliberately treat as scratch space, so two Windows cases failed; the test now builds under the user folder.
- schtasks /create /tr breaks on a Python path with a space (C:\Program Files\Python313); replaced by run-nightly.cmd and a task XML written by register_tasks.py.
- PowerShell on this PC cannot reach the scheduled-task CIM provider as claude-remote ("access denied"), so "start when available" is set through the task XML instead of Set-ScheduledTask.

## PC self-test output (final run, from the unzipped kit installed as a plugin)

```
PASS  guards: ALLOW Write a NEW file in a Dropbox job folder allowed 
PASS  guards: ALLOW Write a NEW file, Windows path with spaces allowed 
PASS  guards: ALLOW mkdir of a new Dropbox folder  allowed 
PASS  guards: ALLOW New-Item -ItemType Directory (new) allowed 
PASS  guards: ALLOW copy a file to a NEW name in Dropbox allowed 
PASS  guards: ALLOW cp into a Dropbox folder, name not there yet allowed 
PASS  guards: ALLOW redirect into a NEW Dropbox file allowed 
PASS  guards: ALLOW copy OUT of Dropbox            allowed 
PASS  guards: ALLOW ls in Dropbox                  allowed 
PASS  guards: ALLOW Get-Content (read) in 20. RAW  allowed 
PASS  guards: ALLOW Write in the brain             allowed 
PASS  guards: BLOCK Write over an existing Dropbox file denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK Write over existing file with a space in its name denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK Edit of a Dropbox file         denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK Edit, Windows path with spaces denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK MultiEdit of a Dropbox file    denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK NotebookEdit of a Dropbox file denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK Bash rm in Dropbox             denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK PowerShell Remove-Item in Dropbox denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK del in Dropbox                 denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK mv inside Dropbox              denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK Move-Item out of Dropbox       denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK Rename-Item in Dropbox         denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK copy over an existing Dropbox file denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK cp into a folder where that name already exists denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK robocopy /MIR into Dropbox     denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK robocopy /PURGE into Dropbox   denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK plain robocopy into Dropbox    denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK unzip into Dropbox             denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK Expand-Archive into Dropbox    denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK tar -C into Dropbox            denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK redirect over an existing Dropbox file denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK Set-Content on an existing Dropbox file denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK Write a NEW file in 20. RAW    denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK Write over a file in 20. RAW   denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK mkdir in 20. RAW               denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK copy a NEW file into 20. RAW   denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK Remove-Item in 20. RAW         denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK redirect into 20. RAW          denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: ALLOW-LIST: edit inside a folder the person allowed allowed 
PASS  guards: CONNECTOR ALLOW list_folder          allowed 
PASS  guards: CONNECTOR ALLOW search               allowed 
PASS  guards: CONNECTOR ALLOW fetch                allowed 
PASS  guards: CONNECTOR ALLOW get_shared_link_metadata allowed 
PASS  guards: CONNECTOR ALLOW download_link        allowed 
PASS  guards: CONNECTOR ALLOW upload as a NEW file (mode add) allowed 
PASS  guards: CONNECTOR ALLOW create_folder        allowed 
PASS  guards: CONNECTOR BLOCK upload with no mode (target unknown) denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: CONNECTOR BLOCK upload mode overwrite denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: CONNECTOR BLOCK move                 denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: CONNECTOR BLOCK delete               denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: CONNECTOR BLOCK rename               denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: CONNECTOR BLOCK copy                 denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: CONNECTOR BLOCK restore              denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: CONNECTOR BLOCK update_file          denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: CONNECTOR BLOCK move_file            denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: CONNECTOR BLOCK delete_file          denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: CONNECTOR BLOCK an unknown tool      denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: CONNECTOR: non-Dropbox MCP tool untouched allowed 
PASS  voice: em dash                               blocked {"decision": "block", "reason": "VOICE CHECK on C:\\Users\\claude-remote\\upn-kit-selftest
PASS  voice: US spelling                           blocked {"decision": "block", "reason": "VOICE CHECK on C:\\Users\\claude-remote\\upn-kit-selftest
PASS  voice: double dash                           blocked {"decision": "block", "reason": "VOICE CHECK on C:\\Users\\claude-remote\\upn-kit-selftest
PASS  voice: clean British text                    clean 
PASS  voice: code block ignored                    clean 
PASS  voice: non-prose file ignored                clean 
PASS  proof: claim without a check                 {"decision": "block", "reason": "PROOF: your reply says \"Done\", but nothing was checked 
PASS  proof: claim after a check                   (silent)
PASS  proof: no change, no flag                    (silent)
PASS  right-source: edit without reading NOW       {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason
PASS  right-source: edit after reading NOW         (silent)
PASS  right-source: wiki page is not a job folder  (silent)
PASS  catch: correction heard                      {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "CATCH: the person
PASS  catch: other edit blocked until saved        {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDeci
PASS  catch: saving the rule is allowed            (silent)
PASS  catch: edits free again after the rule       (silent)
PASS  catch: ordinary request ignored              (silent)
PASS  catch: taught rule enforced by voice check   {"decision": "block", "reason": "VOICE CHECK on C:\\Users\\claude-remote\\upn-kit-selftest-s2mambbe\
PASS  context: 5% gauge only                       {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "Context window: 5% full (fi
PASS  context: 16% checkpoint saved                {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "Context window: 16% full (c
PASS  context: checkpoint warned once              {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "Context window: 16% full (c
PASS  context: 27% handover note + new conversation {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "Context window: 27% full (past the handover lin
PASS  close-out: offered after 3 saves             {"decision": "block", "reason": "CLOSE-OUT: this session has saved 3 files and not been closed out. In one sho
PASS  close-out: offered only once                 (silent)
PASS  routing: Explore goes to haiku               {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow", "updatedInput": {"subage
PASS  routing: a model named by the person wins    (silent)
PASS  brain-search: index builds                   Indexed 7 files in 0.0s: 7 new, 0 changed, 0 touched only, 0 unchanged, 0 removed. DB C:\Users\claud
PASS  brain-search: search finds the wiki + NOW    1. wiki/oman.md  [2026-10-25]    Oman AIG bid    --- aliases: [the gulf bid] --- # [Oman] AIG bid We decided to submit t
PASS  brain-search: frontmatter alias finds it     1. wiki/oman.md  [2026-10-25]    Oman AIG bid    --- aliases: [the [gulf] [bid]] --- # Oman AIG [bid
PASS  look-first: past question gets hits          LOOK FIRST (brain-search, ranked, newest boosted): 2026-10-25 wiki/oman.md: --- aliases: [the gulf bid] --- # 
PASS  look-first: ordinary request silent          (silent)
PASS  doctor: two indexes + dead path + em dash    RED: two indexes compete: C:\Users\claude-remote\upn-kit-selftest-s2mambbe\Second Brain\MEMORY.md and C:\Users\claude-remote\upn-kit-selftes
PASS  session-start: NOW + handover + doctor       {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "STATE FILE for this session: C:\\Users\\claude-remo
PASS  session-start: handover offered once (marked TAKEN) TAKEN
PASS  session-start: shim + kit_root written       C:\Users\claude-remote\upn-kit-selftest-s2mambbe\kit-home\run-nightly.py
PASS  nightly storage: index of Dropbox job folders storage: C:\Users\claude-remote\upn-kit-selftest-s2mambbe\UrbanPlaceNetwork Dropbox\UPN_Server_01\0.
PASS  nightly storage: contents never read         file names are not listed
PASS  nightly atoms: line written for the conversation model failed for abcd1234: model error: Not logged in ┬À Please run /login atoms 2026-10-25 [fallback: (no model)]
PASS  nightly atoms: fed into brain-search         1. atoms/2026-10-25.md  [2026-10-25]    Atoms 2026-10-25    Written at night. - 12:50 Please find th
PASS  nightly summaries: runs, fallback safe       summaries: 0 written, 0 failed, 0 candidates
PASS  nightly save: commit + NIGHT LOG, no push    2026-10-25: commit ok (8 files) | 0980f4d Night save 2026-10-25: 8 files
PASS  nightly save: nothing pushed (no remote touched) no remote configured
PASS  job-start: folder, NOW, map row, path recorded job folder: C:\Users\claude-remote\upn-kit-selftest-s2mambbe\Second Brain\upn\projects\wb--albania-t
PASS  job-start: refuses to overwrite              STOP: C:\Users\claude-remote\upn-kit-selftest-s2mambbe\Second Brain\upn\projects
PASS  guards: MIRROR: edit an existing file inside the allowed mirror folder allowed 
PASS  guards: MIRROR: robocopy /MIR brain to the mirror (the scheduled copy) allowed 
PASS  guards: MIRROR: robocopy the mirror back to the brain (pull back) allowed 
PASS  guards: MIRROR: running the mirror script does not trip the guard allowed 
PASS  guards: MIRROR: robocopy /MIR into ANOTHER Dropbox folder is still blocked denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: MIRROR: server files stay protected  denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: DROPBOX BRAIN: edit an existing wiki page allowed 
PASS  guards: DROPBOX BRAIN: Write over an existing file in the brain allowed 
PASS  guards: DROPBOX BRAIN: shell redirect over a brain file allowed 
PASS  guards: DROPBOX BRAIN: 20. RAW inside it stays read-only denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: DROPBOX BRAIN: Remove-Item in 20. RAW still blocked denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: DROPBOX BRAIN: server files outside the brain still protected denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: DROPBOX BRAIN: a NEW server file is still allowed allowed 
PASS  second machine: night save skipped, no .git created night save: skipped. This is the second computer (config.json role = second); the main computer does
PASS  second machine: atoms skipped                atoms: skipped. This is the second computer (config.json role = second); the main computer does this
PASS  second machine: tasks not registered         Not registering: config.json says role = second. The night save and the night notes run on the main 
PASS  second machine: checkpoint written outside the Dropbox brain state in C:\Users\claude-remote\upn-kit-selftest-s2mambbe\kit-home\state; brain unchanged: True
PASS  second machine: search index lives in the kit folder, not Dropbox Indexed 8 files in 0.0s: 4 new, 4 changed, 0 touched only, 0 unchanged, 5 removed. DB C:\Users\claud
PASS  second machine: session start works in the Dropbox brain {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "STATE FILE for this s

122 cases, 122 passed, 0 failed
```

## Mac self-test output

```
PASS  guards: ALLOW Write a NEW file in a Dropbox job folder allowed 
PASS  guards: ALLOW Write a NEW file, Windows path with spaces allowed 
PASS  guards: ALLOW mkdir of a new Dropbox folder  allowed 
PASS  guards: ALLOW New-Item -ItemType Directory (new) allowed 
PASS  guards: ALLOW copy a file to a NEW name in Dropbox allowed 
PASS  guards: ALLOW cp into a Dropbox folder, name not there yet allowed 
PASS  guards: ALLOW redirect into a NEW Dropbox file allowed 
PASS  guards: ALLOW copy OUT of Dropbox            allowed 
PASS  guards: ALLOW ls in Dropbox                  allowed 
PASS  guards: ALLOW Get-Content (read) in 20. RAW  allowed 
PASS  guards: ALLOW Write in the brain             allowed 
PASS  guards: BLOCK Write over an existing Dropbox file denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK Write over existing file with a space in its name denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK Edit of a Dropbox file         denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK Edit, Windows path with spaces denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK MultiEdit of a Dropbox file    denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK NotebookEdit of a Dropbox file denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK Bash rm in Dropbox             denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK PowerShell Remove-Item in Dropbox denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK del in Dropbox                 denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK mv inside Dropbox              denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK Move-Item out of Dropbox       denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK Rename-Item in Dropbox         denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK copy over an existing Dropbox file denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK cp into a folder where that name already exists denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK robocopy /MIR into Dropbox     denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK robocopy /PURGE into Dropbox   denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK plain robocopy into Dropbox    denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK unzip into Dropbox             denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK Expand-Archive into Dropbox    denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK tar -C into Dropbox            denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK redirect over an existing Dropbox file denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK Set-Content on an existing Dropbox file denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK Write a NEW file in 20. RAW    denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK Write over a file in 20. RAW   denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK mkdir in 20. RAW               denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK copy a NEW file into 20. RAW   denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK Remove-Item in 20. RAW         denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: BLOCK redirect into 20. RAW          denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: ALLOW-LIST: edit inside a folder the person allowed allowed 
PASS  guards: CONNECTOR ALLOW list_folder          allowed 
PASS  guards: CONNECTOR ALLOW search               allowed 
PASS  guards: CONNECTOR ALLOW fetch                allowed 
PASS  guards: CONNECTOR ALLOW get_shared_link_metadata allowed 
PASS  guards: CONNECTOR ALLOW download_link        allowed 
PASS  guards: CONNECTOR ALLOW upload as a NEW file (mode add) allowed 
PASS  guards: CONNECTOR ALLOW create_folder        allowed 
PASS  guards: CONNECTOR BLOCK upload with no mode (target unknown) denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: CONNECTOR BLOCK upload mode overwrite denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: CONNECTOR BLOCK move                 denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: CONNECTOR BLOCK delete               denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: CONNECTOR BLOCK rename               denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: CONNECTOR BLOCK copy                 denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: CONNECTOR BLOCK restore              denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: CONNECTOR BLOCK update_file          denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: CONNECTOR BLOCK move_file            denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: CONNECTOR BLOCK delete_file          denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: CONNECTOR BLOCK an unknown tool      denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: CONNECTOR: non-Dropbox MCP tool untouched allowed 
PASS  voice: em dash                               blocked {"decision": "block", "reason": "VOICE CHECK on /Users/louiswright/upn-kit-selftest-h_ctgo
PASS  voice: US spelling                           blocked {"decision": "block", "reason": "VOICE CHECK on /Users/louiswright/upn-kit-selftest-h_ctgo
PASS  voice: double dash                           blocked {"decision": "block", "reason": "VOICE CHECK on /Users/louiswright/upn-kit-selftest-h_ctgo
PASS  voice: clean British text                    clean 
PASS  voice: code block ignored                    clean 
PASS  voice: non-prose file ignored                clean 
PASS  proof: claim without a check                 {"decision": "block", "reason": "PROOF: your reply says \"Done\", but nothing was checked 
PASS  proof: claim after a check                   (silent)
PASS  proof: no change, no flag                    (silent)
PASS  right-source: edit without reading NOW       {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason
PASS  right-source: edit after reading NOW         (silent)
PASS  right-source: wiki page is not a job folder  (silent)
PASS  catch: correction heard                      {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "CATCH: the person
PASS  catch: other edit blocked until saved        {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDeci
PASS  catch: saving the rule is allowed            (silent)
PASS  catch: edits free again after the rule       (silent)
PASS  catch: ordinary request ignored              (silent)
PASS  catch: taught rule enforced by voice check   {"decision": "block", "reason": "VOICE CHECK on /Users/louiswright/upn-kit-selftest-h_ctgosp/Second 
PASS  context: 5% gauge only                       {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "Context window: 5% full (fi
PASS  context: 16% checkpoint saved                {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "Context window: 16% full (c
PASS  context: checkpoint warned once              {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "Context window: 16% full (c
PASS  context: 27% handover note + new conversation {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "Context window: 27% full (past the handover lin
PASS  close-out: offered after 3 saves             {"decision": "block", "reason": "CLOSE-OUT: this session has saved 3 files and not been closed out. In one sho
PASS  close-out: offered only once                 (silent)
PASS  routing: Explore goes to haiku               {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow", "updatedInput": {"subage
PASS  routing: a model named by the person wins    (silent)
PASS  brain-search: index builds                   Indexed 7 files in 0.0s: 7 new, 0 changed, 0 touched only, 0 unchanged, 0 removed. DB /Users/louiswr
PASS  brain-search: search finds the wiki + NOW    1. wiki/oman.md  [2026-10-25]    Oman AIG bid    --- aliases: [the gulf bid] --- # [Oman] AIG bid We decided to submit t
PASS  brain-search: frontmatter alias finds it     1. wiki/oman.md  [2026-10-25]    Oman AIG bid    --- aliases: [the [gulf] [bid]] --- # Oman AIG [bid
PASS  look-first: past question gets hits          LOOK FIRST (brain-search, ranked, newest boosted): 2026-10-25 wiki/oman.md: --- aliases: [the gulf bid] --- # 
PASS  look-first: ordinary request silent          (silent)
PASS  doctor: two indexes + dead path + em dash    RED: two indexes compete: /Users/louiswright/upn-kit-selftest-h_ctgosp/Second Brain/MEMORY.md and /Users/louiswright/upn-kit-selftest-h_ctgo
PASS  session-start: NOW + handover + doctor       {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "STATE FILE for this session: /Users/louiswright/upn
PASS  session-start: handover offered once (marked TAKEN) TAKEN
PASS  session-start: shim + kit_root written       /Users/louiswright/upn-kit-selftest-h_ctgosp/kit-home/run-nightly.py
PASS  nightly storage: index of Dropbox job folders storage: /Users/louiswright/upn-kit-selftest-h_ctgosp/UrbanPlaceNetwork Dropbox/UPN_Server_01/0. Pro
PASS  nightly storage: contents never read         file names are not listed
PASS  nightly atoms: line written for the conversation atoms 2026-10-25: 1 conversations seen, 1 written, 0 model failures [model call ran]
PASS  nightly atoms: fed into brain-search         1. atoms/2026-10-25.md  [2026-10-25]    Atoms 2026-10-25    Written at night. - 12:49 Checked the [f
PASS  nightly summaries: runs, fallback safe       summaries: 0 written, 0 failed, 0 candidates
PASS  nightly save: commit + NIGHT LOG, no push    2026-10-25: commit ok (8 files) | 3d0d25c Night save 2026-10-25: 8 files
PASS  nightly save: nothing pushed (no remote touched) no remote configured
PASS  job-start: folder, NOW, map row, path recorded job folder: /Users/louiswright/upn-kit-selftest-h_ctgosp/Second Brain/upn/projects/wb--albania-touri
PASS  job-start: refuses to overwrite              STOP: /Users/louiswright/upn-kit-selftest-h_ctgosp/Second Brain/upn/projects/wb-
PASS  guards: MIRROR: edit an existing file inside the allowed mirror folder allowed 
PASS  guards: MIRROR: robocopy /MIR brain to the mirror (the scheduled copy) allowed 
PASS  guards: MIRROR: robocopy the mirror back to the brain (pull back) allowed 
PASS  guards: MIRROR: running the mirror script does not trip the guard allowed 
PASS  guards: MIRROR: robocopy /MIR into ANOTHER Dropbox folder is still blocked denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: MIRROR: server files stay protected  denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: DROPBOX BRAIN: edit an existing wiki page allowed 
PASS  guards: DROPBOX BRAIN: Write over an existing file in the brain allowed 
PASS  guards: DROPBOX BRAIN: shell redirect over a brain file allowed 
PASS  guards: DROPBOX BRAIN: 20. RAW inside it stays read-only denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: DROPBOX BRAIN: Remove-Item in 20. RAW still blocked denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: DROPBOX BRAIN: server files outside the brain still protected denied {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDeci
PASS  guards: DROPBOX BRAIN: a NEW server file is still allowed allowed 
PASS  second machine: night save skipped, no .git created night save: skipped. This is the second computer (config.json role = second); the main computer does
PASS  second machine: atoms skipped                atoms: skipped. This is the second computer (config.json role = second); the main computer does this
PASS  second machine: tasks not registered         Not registering: config.json says role = second. The night save and the night notes run on the main 
PASS  second machine: checkpoint written outside the Dropbox brain state in /Users/louiswright/upn-kit-selftest-h_ctgosp/kit-home/state; brain unchanged: True
PASS  second machine: search index lives in the kit folder, not Dropbox Indexed 8 files in 0.0s: 4 new, 4 changed, 0 touched only, 0 unchanged, 5 removed. DB /Users/louiswr
PASS  second machine: session start works in the Dropbox brain {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "STATE FILE for this s

122 cases, 122 passed, 0 failed
```
