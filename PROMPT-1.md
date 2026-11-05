# PROMPT 1: save point and clean-up

Open your second brain folder in VS Code (the folder that holds `CLAUDE.md`, `wiki` and `upn`), start a new Claude conversation, and paste everything below the line.

---

You are going to get my brain ready for a new working kit. Work through the steps in order. Rules for the whole job:

- Explain each step in one plain sentence before you do it. I am not technical.
- Nothing is deleted. Anything that moves goes to an archive folder, and you tell me where.
- Ask me "yes or no" before anything that moves, switches off or changes a file, and show me exactly what will change first. Reading and listing need no question.
- When I have to type something back (a name, an email, a path, or a command such as `/context`), ask in plain text in your reply, never with a question form: the form hides the box I type in. Say "type it, then tell me", and wait.
- In Dropbox you may only read, and save new files; never overwrite, edit, move, rename or delete anything there. `20. RAW` is read-only. The only Dropbox-related change in this job is to my own mirror script, and only after I say yes.
- British English. No em dashes, no double dashes, in anything you write.
- After each step run one test, show me what it printed, and say PASS or FAIL. If a step fails, stop and tell me; do not work around it.
- **Do not change how my Dropbox copy of the brain works.** Its schedule, its target folder, its method (robocopy /MIR) and its hold logic (for example `_MIRROR-HOLD.txt`) stay exactly as they are. The only change this job makes to the mirror is adding the memory folder copy in Step 3, with my yes.
- Keep a short report as you go, in a file at `%USERPROFILE%\upn-kit-reports\prompt-1-report.md` (create the folder). That folder is outside my brain and outside Dropbox.

## Step 0: look around

Run and show me: `python --version` (or `py --version`), `git --version`, `node --version`, `claude --version`. Say which of them are missing; do not install anything yet. Then tell me: the full path of this brain folder, whether it sits inside Dropbox or OneDrive (it must not), and how big it is (files and gigabytes). Find my Claude memory folder (it lives under `%USERPROFILE%\.claude\projects\`, in the folder named after this brain's path, then `memory`) and give me its full path.

## Step 1: which computer is which

Ask me once, in these words: "Which computer is your main one, and how do you use the other: do you open the Dropbox copy of the brain directly, or pull it back first?" Wait for my answer. This computer is `main` if it holds the master brain (the one the mirror copies FROM), otherwise `second`. Create or update `%USERPROFILE%\.claude\upn-kit\config.json` now (make the folder if needed) with `role` (`main` or `second`) and `second_use` (`open-dropbox-copy` or `pull-back` or `not used`), keeping any other keys. If this brain sits inside a Dropbox path, that is normal for a second computer that opens the Dropbox copy; do not move it. Show me the file.

## Step 1b: a save point (git, outside Dropbox)

**Main computer only.** If `role` is `second` (set in Step 1, just before this), skip this step and Step 3 completely: the git history and the Dropbox copy belong to the main computer, and no `.git` is made inside a Dropbox copy. If the mirror already copies a `.git` folder into Dropbox, leave that as it is; the kit neither adds nor removes it.

Why: every later step can then be undone.

1. If this folder is not already a git repository, run `git init`. If it is, tell me and carry on.
2. Check `git config user.name` and `user.email`. If either is empty, ask me for a name and an email and set them for this repository only.
3. Make a `.gitignore` that leaves out: `20. RAW/`, `.raw/`, `.playwright-mcp/`, `node_modules/`, `.obsidian/workspace*.json`, any `claude-obsidian/` clone (it has its own git folder), temporary files, and any single file over 50 MB. Show me the list and wait for my yes before you write it.
4. Make the first save point: `git add -A` then `git commit -m "Save point before the UPN kit, <today's date>"`. Never run `git push` and never add a remote.
5. Test: show `git log --oneline -1`, `git status --short` (it should be empty) and the number of files committed. PASS only if the commit exists and the status is clean.

## Step 2: reshape the memory

Why: both of our setups have two "main" memory files competing, one of them is not loaded automatically, and the loaded one grows until entries drop off silently.

1. Read my auto-memory `MEMORY.md` (in the memory folder from Step 0) and, if it exists, the `MEMORY.md` at the root of the brain. Tell me the size of each (bytes and lines) and how many memory files sit in the folder.
2. Make a plan and show it as a table, before touching anything:
   - ONE index only: the auto-memory `MEMORY.md`, because Claude Code loads that one by itself. The root `MEMORY.md` is archived, not deleted.
   - The index stays small: under 150 lines and 15,000 bytes. It holds one line per hub (area), not one line per fact.
   - One hub file per area (for example: bids, the website, Urban Hive, personal, Dropbox and the mirror, voice and style), each listing its facts with a short line and a link.
   - One fact per file, with a name, a one-line description, and the source and date of the fact. A fact keeps the wording it has now.
   - Show which existing line or file goes where. Anything you are not sure about stays where it is and is listed as "left alone".
3. Wait for my yes. Then do it: copy the old index(es) to `memory\_archive\MEMORY-<date>-old.md` (and the root one to `_archive\MEMORY-root-<date>.md` in the brain), write the new index and hubs.
4. Test: count the facts (lines starting with "- " or memory files) before and after; every old fact must appear somewhere in the new set. Show the two numbers, the new index size, and PASS only if nothing was lost and the index is under the limits.

## Step 3: put the memory folder in the Dropbox mirror

Why: both reports found the memory folder is outside the brain, so my daily or weekly Dropbox copy does not back it up.

1. Find my mirror: the Task Scheduler task that copies the brain into Dropbox (look at `schtasks /query /fo list` for names containing "mirror" or "Dropbox"), and the script it runs. Show me the task name and the full path of the script.
2. Do not touch the schedule, the target, the /MIR method or the hold logic. Show me the exact lines you would add so that the memory folder is copied too, into a folder called `_claude-memory` next to the brain copy. Same method the script already uses (robocopy). Wait for my yes, keep a copy of the old script next to it as `<name>.bak-<date>`, then make the change.
3. Test: run the script once the way the task does, then list the copied memory folder and compare the file count with the source. PASS only if the counts match. (If running the script is slow or would copy gigabytes, tell me and ask first.)
4. Create or update `%USERPROFILE%\.claude\upn-kit\config.json` with these keys (add `mirror_dest`, the full path of the folder in Dropbox the mirror writes into, and put that same path in a list called `allow`, so the kit's Dropbox guard never gets in the way of the mirror, of pulling it back, or of editing inside it; keep any entries already there), keeping any that exist: `brain` (the brain folder), `memory_dirs` (a list with my memory folder; if I have a second memory folder for another project, ask me and add it), `mirror_task` (the task name), `mirror_script` (the script path). Ask me for `dropbox_roots`: the full path of the folder that holds my job folders in Dropbox (for example the server's projects folder), and add it as a list. Show me the file.

## Step 4: the lean pass (switch off what is unused, delete nothing)

Why: skills and plugins I never use still cost attention and slow every conversation.

1. List everything installed: my skills (`%USERPROFILE%\.claude\skills`, and `.claude\skills` in this brain), my plugins (`claude plugin list`, or the folders under `%USERPROFILE%\.claude\plugins`), and the plugin hooks that run on every session start and every turn.
2. For each, find out whether it was used in the last 30 days: search my conversation logs in `%USERPROFILE%\.claude\projects\` for Skill calls and slash commands. Show a table: name, what it is for in one line, times used in 30 days, your suggestion (keep, switch off).
3. Two things must be in the table by name:
   - **claude-obsidian**: I use it. Its hooks run at every session start and at the end of every turn, and the kit I am about to install does its own close-out, so the two overlap. Offer me two options: (a) keep the plugin and its commands but switch its hooks off (back up its `hooks\hooks.json` as `hooks.json.off`, then leave an empty hooks file; tell me that a plugin update brings the hooks back and this step can be repeated), or (b) leave it exactly as it is. My wiki, my notes and the vault are not touched either way. My answer decides.
   - **superpowers**, if it is installed twice (two versions): offer to switch off the older copy.
4. Also tell me whether you find Graphify installed anywhere (skills, plugins, MCP servers). If you do not, say so plainly.
5. Switching off means: a plugin goes through `claude plugin disable <name>`; a skill folder moves to `%USERPROFILE%\.claude\_skills-off\` (so putting it back is one move). I choose item by item, or "all of your suggestions". Do exactly what I say yes to and nothing else.
6. Test: after switching off, list what is still on and what is off; start nothing new. PASS only if the lists match what I agreed.

## Step 5: report

Show me the report file. It should list each step, what you changed, where anything was archived, and PASS or FAIL. Tell me the full path. Then tell me the next step is Prompt 2, and not to start it in this conversation: open a new one.
