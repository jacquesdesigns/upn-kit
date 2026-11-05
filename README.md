# The UPN kit

For James and Jeremy. Plain English, one page.

## Install in three steps

1. **Get the kit.** Open PowerShell and paste this one line (it copies the kit into your user folder; no sign-in is needed):
   `git clone https://github.com/jacquesdesigns/upn-kit.git "$env:USERPROFILE\upn-kit"`
   No Git yet? `winget install Git.Git`, then close and reopen PowerShell. If GitHub is blocked on your network, unzip `upn-kit.zip` from the Dropbox link into your user folder instead, so you have `upn-kit\upn-marketplace`.
2. **Prompt 1.** Open your second brain folder in VS Code, start a new Claude conversation and paste everything below the line in `PROMPT-1.md`. Answer its yes or no questions. It makes the save point first. Nothing is deleted.
3. **Prompt 2.** Start another new conversation and paste everything below the line in `PROMPT-2.md`. It installs the kit, tests every piece and makes a small report zip for Louis.

Then do the same on your other computer. To update later: `git -C "$env:USERPROFILE\upn-kit" pull`, then `claude plugin marketplace update upn-marketplace` and `claude plugin update upn-kit@upn-marketplace`.

## What it is

One add-on for your own Claude Code. You install it from a short prompt (Prompt 2); Prompt 1 makes the safe save point first. When we improve something we send a new version and you update with one command. Nothing is copied by hand.

## What it does for you

**It stops mistakes before they happen.**
- Claude can read Dropbox and save new files into job folders, but cannot overwrite, edit, move, rename or delete anything there; `20. RAW` stays read-only. This covers the Dropbox connector in Claude as well as files on your computer.
- After every file it writes, em dashes, double dashes and American spellings are caught and fixed straight away.
- Before it edits anything in a job folder, it has to have read that job's `NOW.md`.
- If it says "done" without having checked anything after its last change, it is sent back to check.
- When you correct it ("I told you", "from now on"), it saves that as a rule before carrying on.

**It remembers.**
- At the start of every session it brings in the job you opened (its `NOW.md`; at the brain root it lists the recent jobs and loads none), the rules you have taught it, and any handover waiting from a conversation that ran long.
- It tells you the real context fill. At 15% it saves a checkpoint. At 25% it writes the handover note and tells you to start a new conversation; the new one picks up from the note.
- Search the whole brain in a moment: memory, wiki, every `NOW.md`, the nightly notes, and an index of your Dropbox job folders (names and dates only, never contents). "Where is the Oman job?" is one search.
- A small health check runs at the start of each session and prints one red line for each fault: the memory index too big, two competing indexes, memory pointing at files that are gone, em dashes in new wiki pages, the Dropbox copy not running, the memory folder missing from the copy.

**It saves itself.**
- At 23:00 it logs the day into each job's `NOW.md` and makes a git save point ("Night save"). It never sends anything anywhere.
- At 23:20 it writes one line per conversation and a few facts worth keeping (a command that worked, an error, a fix, a decision and why), using Claude Haiku through the `claude` command. No key.
- At the end of a session where files were saved, Claude offers the close-out once. Say yes. It writes the wiki page, updates the job's `NOW.md` and lists every file with its full path. Nobody types "save to the wiki" again.

**Skills** (type the name, or just ask):
`/studio` (references, brief, build, check, judge), `/studio-check`, `/judge`, `/reverse`, `/taste-review`, `/rubric`, `/score`, `/court`, `/go-live`, plus `/close-out`, `/brain-search`, and for James `/job-start`: give a job number and Claude makes the folder, the `NOW.md` and the map row, and writes down the Dropbox paths.

## The three layers (how the brain is kept)

1. **What changes** lives in the job's `NOW.md`: status, what is sent, what is waiting. It points at the job's Dropbox folder. Check this first, and check the real file.
2. **What stays true** lives in the wiki: who someone is, how a client likes things, a decision and why.
3. **What happened lately** lives in `wiki/hot.md`: one line per day per job.

The job's `NOW.md` records where the job's files are (the Dropbox paths) and what was saved, with full paths. Where drafts live is up to you; the kit does not set it. Claude can save a new file into the Dropbox job folder for you (a new file name only); it cannot replace, edit, move, rename or delete one that is already there.

## Your Dropbox copy stays exactly as it is

The kit never changes your Dropbox copy of the brain: its schedule, where it copies to, how it copies (robocopy /MIR) and the hold file if the copy was edited elsewhere are all left alone. The only addition, with your yes, is that the memory folder is copied as well. The mirror folder is on the guard's allow list, so copying to it, pulling it back, and working inside it carry on as now. If you open the Dropbox copy on your other computer, normal edits inside that brain are not blocked; `20. RAW` still is.

## How to install

1. Get the kit into your user folder (so you have `upn-kit\upn-marketplace`): the `git clone` line at the top of this page, or, as a fallback, unzip `upn-kit.zip` there.
2. Open your second brain folder in VS Code. Start a new Claude conversation. Paste **PROMPT-1.md** (below the line). Answer its yes/no questions. It makes the save point, tidies the memory, adds the memory to your Dropbox copy and lists what you do not use. Nothing is deleted.
3. Start another new conversation. Paste **PROMPT-2.md**. It installs what the kit needs, installs the kit, runs a test for every piece and sets up the two nightly tasks. At the end it makes a small zip report. Send that to Louis.
4. **Then do the same on your other computer** (open the brain there, run Prompt 1, then Prompt 2). Prompt 1 asks which computer is your main one and how you use the other. On the second computer the kit gives you the hooks, skills and search, but it does not run the night save or the night notes (they would write into the Dropbox copy). The main computer does those.

## What you will see change

- Fewer things to remember. The things you used to ask for at the end of a session are offered.
- A red line at the start of a session when something is wrong. Tell Claude to fix it, or ignore it.
- If Claude refuses a change in Dropbox (an overwrite, an edit, a move, a rename or a delete), that is the kit working. Ask it to save a new file with a new name, or to save in the job folder in the brain.

## What is not in it

The Board, THE WEEK, the iPad and Mac tools, the logo tools, the weekly review and the studio's own machines stay with us. They need hardware you do not have.

## Questions

Louis, or ask Claude: "what does the UPN kit do?".
