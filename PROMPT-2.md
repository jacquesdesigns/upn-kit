# PROMPT 2: install the UPN kit

Do Prompt 1 first. Install on your main computer first, then do the same on the other computer (Prompt 1 and Prompt 2 again; Prompt 1 skips the parts that belong to the main computer). Get the kit into `%USERPROFILE%\upn-kit` (so that the folder `%USERPROFILE%\upn-kit\upn-marketplace` exists; not inside the brain, not inside Dropbox): in PowerShell, `git clone https://github.com/jacquesdesigns/upn-kit.git "$env:USERPROFILE\upn-kit"` (no sign-in is needed). Fallback, if the clone cannot reach GitHub: unzip `upn-kit.zip` from the Dropbox link into the same place. Open the brain folder in VS Code, start a new Claude conversation, and paste everything below the line.

---

You are going to install the UPN kit for me and prove each piece works. The kit is at `%USERPROFILE%\upn-kit\upn-marketplace`. Rules for the whole job:

- Explain each step in one plain sentence first. I am not technical.
- Ask me "yes or no" before installing software, moving files, switching anything off or registering a scheduled task. Reading and listing need no question.
- When I have to type something (a command such as `/reload-plugins` or `/context`, a number, a path), ask in plain text in your reply, never with a question form: the form hides the box I type in. Say "type it, then tell me", and wait.
- In Dropbox you may only read and save new files; never overwrite, edit, move, rename or delete anything there (the kit enforces this). `20. RAW` is read-only, no new files either. Never sign in to anything for me; if a sign-in is needed, tell me exactly what to click and wait.
- Nothing is deleted: anything replaced is moved to a folder you name to me.
- British English. No em dashes, no double dashes.
- Every piece gets one test. Show what it printed and say PASS or FAIL. A failure stays a failure in the report; do not work around it, stop and tell me.
- Keep the report at `%USERPROFILE%\upn-kit-reports\prompt-2-report.md`.

## Step 0: check Prompt 1 was done

Read `role` in `%USERPROFILE%\.claude\upn-kit\config.json`. If there is no `role`, stop and tell me to do Prompt 1 first. If `role` is `main`: run `git log --oneline -3` in the brain; there must be a commit called "Save point before the UPN kit", and if there is not, stop. If `role` is `second`: skip the git check (the save point lives on the main computer) and do not run `git init` anywhere.

## Step 1: what the kit needs, checked and installed

Check each, tell me what is there, and for anything missing give the exact command and ask yes before running it. After any install, tell me to close and reopen VS Code if the command is not found.

- Python 3.10 or newer (`winget install Python.Python.3.12` if missing; tick "Add to PATH" if the python.org installer is used). Hooks call `python` and fall back to `py`; show me which one works.
- Git (`winget install Git.Git`).
- Node.js LTS (`winget install OpenJS.NodeJS.LTS`), needed for anything started with `npx`.
- The `claude` command line (`claude --version`). If it is missing: `npm.cmd install -g @anthropic-ai/claude-code` (use `npm.cmd`, not `npm`: Windows often blocks `npm.ps1`). The nightly notes use it, with no key, to write one-line summaries.
- ffmpeg (`winget install Gyan.FFmpeg`), only for recording scroll films in the studio skills.
- A private Python for the studio check kit: `python -m venv "%USERPROFILE%\.claude\upn-kit\venv"`, then in it `pip install playwright pillow`, then `python -m playwright install chromium` (slow; say so). The Safari-like engine (`python -m playwright install webkit`) is optional; ask me.
- Plugins from their own marketplaces: check `claude plugin list`. superpowers is usually there already; do not add a second copy. Add `frontend-design` from the built-in marketplace `anthropic-plugin-directory` (`claude plugin install frontend-design@anthropic-plugin-directory`; check the name with `claude plugin marketplace list` and use the one it shows) and `gsap-skills` (marketplace `greensock/gsap-skills`) if missing. Hyperframes is not needed by any skill in this kit, so do not install it. Fonts: the kit ships none and needs none.
- Connectors (Dropbox, Microsoft 365, Gmail and so on) are mine to sign in to on claude.ai. Do not touch them; just tell me if one the skills mention is not connected.

Test: print a table of every item with its version and PASS/FAIL.

## Step 2: retire the 2 October studio skills

The kit replaces the nine studio skills I was given on 2 October. If any of `studio`, `studio-check`, `judge`, `court`, `rubric`, `score`, `go-live`, `reverse`, `taste-review` exist in `%USERPROFILE%\.claude\skills`, show me the list and, after my yes, move each folder to `%USERPROFILE%\.claude\skills-retired-2-oct\`. My `Studio\taste` folder (reversal log, lessons, stance) stays exactly where it is; the new skills use it.

## Step 3: install the kit

0. If `%USERPROFILE%\upn-kit\.git` exists (the kit came from `git clone`), run `git -C "%USERPROFILE%\upn-kit" pull` so it is the newest, and show me `git -C "%USERPROFILE%\upn-kit" log --oneline -1` for the report. If it came from the zip, skip this.
1. `claude plugin marketplace add "%USERPROFILE%\upn-kit\upn-marketplace"`
2. `claude plugin install upn-kit@upn-marketplace`
3. `claude plugin list` must show `upn-kit` enabled. Then, in plain text (not a question form), tell me: "type `/reload-plugins` (or close and reopen the Claude panel), then tell me", and wait.

## Step 4: settings the kit reads

Open `%USERPROFILE%\.claude\upn-kit\config.json` (Prompt 1 made it; the kit fills in `kit_root` and `python_exe` by itself the first time a session starts). Make sure it has: `brain`, `memory_dirs`, `mirror_task`, `mirror_script`, `dropbox_roots`, plus `home` (my Studio folder, normally `%USERPROFILE%\Studio`), `python` (the full path of `%USERPROFILE%\.claude\upn-kit\venv\Scripts\python.exe`), and `context_window`. For `context_window`: in plain text (not a question form), ask me to type `/context`, then tell you the total number it shows (for example 200k or 1M); write 200000 or 1000000. Show me the file.

Then, if my brain's `CLAUDE.md` does not already have a section called "HOW THINGS ARE KEPT", show me `%USERPROFILE%\upn-kit\CLAUDE-SNIPPET.md` and, after my yes, add it at the end of `CLAUDE.md`. Do not rewrite anything else in that file.

## Step 5: one test per piece

First, the automatic test of every hook. Run:
`python "<kit_root>\hooks\selftest.py"` (`kit_root` is in `%USERPROFILE%\.claude\upn-kit\config.json` once a session has started with the kit on; if it is not there yet, start a new conversation first). It builds a small fake brain in a temporary folder, feeds each hook sample input, and prints PASS or FAIL for about 130 cases. Show me the whole table. Any FAIL stops the install: tell me which.

Then four live tests in this conversation, so I can see them work:
1. **Voice check**: write a short test note to `<brain>\_state\kit-test.md` that contains the word "color" and one em dash. The kit must tell you to fix it straight away. Fix it, and show me the file after.
2. **Guard**: in the first path in `dropbox_roots`, (a) save a NEW file called `kit-test-new.txt` containing one line: it must be allowed; (b) then try to overwrite it with the Write tool, and to edit it: both must be refused; (c) try to rename it and to delete it: both must be refused; (d) try to create any file inside `20. RAW`: it must be refused. If any of (b) to (d) is NOT refused, stop at once and tell me. Afterwards tell me the full path of `kit-test-new.txt`; I will delete it myself, because you cannot.
3. **Search**: search the brain for a job name I give you, with the brain-search skill. It must return a ranked list with paths.
4. **Close-out**: run the close-out skill on this install conversation. It must write a wiki page, update or create a NOW file for the install, and list every file saved with its full path.

## Step 6: the nightly jobs

**If `role` is `second`, skip this whole step.** The night save and the night notes run on the main computer only: on the second computer they would write `.git` and notes into the Dropbox copy and fight the mirror. Say so, run `python "<kit_root>\hooks\register_tasks.py"` once to show me it refuses ("Not registering"), and go to Step 7. On a second computer the kit keeps its session state and its search index in `%USERPROFILE%\.claude\upn-kit`, never inside Dropbox.

Why: the 23:00 save and the 23:20 notes run by themselves, so nobody has to remember. They run only while I am logged in, and if the computer was off they run at the next opportunity.

1. Run `python "<kit_root>\hooks\register_tasks.py" --dry-run` and show me what it would create: "UPN Night Save" at 23:00 and "UPN Night Notes" at 23:20. Wait for my yes. (No administrator rights are needed; they are user-level tasks.) Then run it without `--dry-run`. It writes a task file for each so that "start when available" is set, and hands it to `schtasks /create /xml`. Do not hand-write `schtasks /create /tr` lines: a path with a space in it breaks the quoting.
2. Call schtasks through PowerShell, exactly as written here, because Git Bash turns `/run` and `/query` into folder paths. Run each task once now with `powershell -NoProfile -Command "schtasks /run /tn 'UPN Night Save'"` and `powershell -NoProfile -Command "schtasks /run /tn 'UPN Night Notes'"`, wait a minute, then read the result with `powershell -NoProfile -Command "schtasks /query /tn '<name>' /v /fo list"` (Last Result 0 is a pass). Show me the commit that "UPN Night Save" made (`git log --oneline -2`: "Night save <date>") and the files `%USERPROFILE%\.claude\upn-kit\atoms\<today>.md` and `%USERPROFILE%\.claude\upn-kit\storage\*.md`. If the notes show "(no model)", the `claude` command was not signed in or not found; tell me, and I will fix it.
3. To remove the tasks later: `python "<kit_root>\hooks\register_tasks.py" --remove`.
4. The save never pushes anywhere. Say so back to me.

## Step 7: the report

Show me the whole report. Then make a zip of: the report, `config.json` with the folder paths only (remove anything that looks like a key or token), the output of `claude plugin list`, and the self-test table. Save it at `%USERPROFILE%\upn-kit-reports\upn-kit-report-<my first name>.zip` and tell me the full path, so I can send it to Louis. Tell me the one habit that changes: nobody types "save to the wiki" any more; when Claude offers the close-out at the end of a session, say yes.
