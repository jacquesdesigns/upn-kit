## HOW THINGS ARE KEPT (added by the UPN kit; paste under your existing rules, do not replace them)

Three layers. Look in the right one first.

1. **What changes** (status, what is sent, what is live, what is waiting on whom): the job's `NOW.md`, in the job's folder in the brain (`upn/projects/<client>--<project>/NOW.md`). It also says where the job's Dropbox folder is. Check it, and check the real file, before saying anything is done or sent.
2. **What stays true** (who someone is, how a client likes things, a decision and why, how a method works): the wiki. Start at `wiki/index.md`.
3. **What happened lately**: `wiki/hot.md`, one line per day per job, newest first. Older detail is in the wiki or in the atoms (search finds it).

Dropbox holds the originals and the job files. Claude reads from it and may save NEW files into job folders there; it never overwrites, edits, moves, renames or deletes anything in Dropbox (the Dropbox connector included), and `20. RAW` stays fully read-only. The job's NOW file records where the job's files are (the Dropbox paths) and what was saved, with full paths. Where drafts live is the person's call, per job.

Searching: ask the brain before answering about the past (`brain-search`). It covers memory, wiki, every NOW file, the nightly atoms and an index of the Dropbox job folders.

Closing a session: the `close-out` skill writes the wiki page, updates the job's NOW file and lists every file saved with its full path. Nobody needs to type "save to the wiki".

Voice: British English; no em dashes and no double dashes; plain words, no hype. The kit checks this after every write.

Helper agents: one agent gets a short list, about five changes; more work goes to more agents in parallel. A new ask during an agent's run goes to a fresh agent, never onto the running one.

Memory: one index only, the auto-memory `MEMORY.md`, kept small, with one hub file per area and one fact per file. A correction from the person becomes a saved rule before work carries on.
