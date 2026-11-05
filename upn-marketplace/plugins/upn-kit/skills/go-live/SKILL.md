---
name: go-live
description: Put a studio project's site live on the person's own domain, step by step, doing as much of the work as possible for them. Use when the user says "put it live", "go live", "publish my site", "deploy", "replace my current website", "connect my domain", "my site is on GoDaddy", or asks how to get their new design onto their real web address. Covers Cloudflare Pages hosting with the domain kept at GoDaddy (the default), and GoDaddy cPanel hosting as the fallback. Uses Claude in Chrome to guide them through the GoDaddy and Cloudflare dashboards.
---

# Go live

You are walking someone who is not technical through putting their new site live on their own domain. Do
every step you can yourself. When they have to act (logging in, approving), tell them exactly what to click,
one step at a time, and wait. Explain each step in one plain sentence before you do it. Never use a term
like DNS, CNAME or nameserver without saying what it means in brackets the first time ("DNS (the address
book that tells the internet where your site lives)").

## Ground rules (keep all of them)

- **The old site stays up until the new one is approved.** Nothing changes on their domain until they have
  opened the new site on a preview link, on their phone and their computer, and said yes in this chat.
- **Write down what is there before you change it.** Before any domain change, save the current records to
  `<project>/go-live/BEFORE.md` (and take a screenshot with Chrome if you can). That is how you undo it.
- **They log in, you never do.** Never type, ask for, read out or store a password, a 2FA code or card
  details. When a login or payment screen appears, stop and say: "Please log in here yourself, then tell me
  when you're in."
- **Confirm before every save.** In Chrome, fill the form, then show them what you are about to save and
  wait for "yes" before pressing Save. After saving, read the page back to check it took.
- **Never delete their email records** (MX records, and TXT records mentioning spf, dkim or dmarc). If a
  change would remove them, stop.
- **Never cancel or downgrade anything they pay for** (GoDaddy hosting, the website builder, email). Tell
  them what they could cancel once the new site has been live for two weeks, and let them do it.
- **The studio check must be green first.** Run `/studio-check` (full run, with `--safari`) on the project.
  Do not go live with a failing check.
- If something does not match these instructions (a screen looks different, a step fails), say what you
  see, take a screenshot, and work it out with them. Never guess at a domain setting.

## Step 1 · Find out what they have (5 minutes)

Ask, one at a time, and write the answers in `<project>/go-live/PLAN.md`:

1. **Their web address** (for example `theirsite.com`).
2. **Where the domain is registered.** Usually GoDaddy. If unsure, look it up yourself: run
   `nslookup -type=ns theirsite.com` and check the nameservers. `domaincontrol.com` means GoDaddy is
   handling the domain; `cloudflare.com` means Cloudflare already is.
3. **What their current site runs on.** With Chrome, open `https://account.godaddy.com/products` and ask
   them to log in. Read the list with them:
   - **Websites + Marketing** (GoDaddy's drag-and-drop builder): it cannot host their new site. Use Route A.
   - **Web Hosting** with cPanel: it can, but Route A is still better (previews, undo). Use Route B only if
     they want everything to stay at GoDaddy.
   - **Managed WordPress**: use Route A.
   - **Nothing but the domain**: Route A.
4. **Does their email use this domain** (`name@theirsite.com`)? If yes, note who provides it (GoDaddy /
   Microsoft 365, Google Workspace). Their email must keep working, so this decides how careful Step 4 is.

Then capture the current site so nothing is lost:
`<python> ~/.claude/skills/studio/scripts/capture_site.py https://theirsite.com "<project>/go-live/old-site"`
and list every page address the old site has (from its menu, footer and `https://theirsite.com/sitemap.xml`
if it exists). Old addresses that the new site does not have get a redirect in Step 3, so Google results
and old links still work.

Tell them the plan in three or four lines before starting.

## Route A · Cloudflare Pages, domain stays at GoDaddy (the default)

Free, fast, with a preview link for every change and one-click undo. Their domain, email and GoDaddy
account stay exactly where they are.

### Step 2 · Put the site on Cloudflare (preview only, their domain untouched)

1. **Node.js** is needed for the deploy tool. Check `node --version`. If missing, on Windows run
   `winget install OpenJS.NodeJS.LTS` (Mac: `brew install node`), then ask them to close and reopen VS Code.
2. **A Cloudflare account.** With Chrome, open `https://dash.cloudflare.com/sign-up`. They sign up
   themselves (free plan; no card needed). Wait until they say they are in.
3. **Connect this computer to their Cloudflare.** Run `npx -y wrangler@4 login`. A browser tab opens; tell
   them to click **Allow**. Then `npx -y wrangler@4 whoami` to confirm.
4. **First deploy.** Pick a short project name from their domain (`theirsite`; lowercase, dashes only):
   ```
   npx -y wrangler@4 pages project create <name> --production-branch main
   npx -y wrangler@4 pages deploy "<project>/site" --project-name <name> --branch main
   ```
   It prints a link like `https://<name>.pages.dev`. That is the new site, live on the internet but not on
   their domain yet.
5. **Check it.** Run `/studio-check --url https://<name>.pages.dev --safari`. Open the link in Chrome for
   them, and ask them to open it on their phone too. Wait for their yes. Change anything they want and
   deploy again with the same command; the link stays the same.

### Step 3 · Redirects for old pages

For every old page address that the new site does not have, add a line to `<project>/site/_redirects`
(Cloudflare reads this file):
```
/about-us    /about    301
/services    /         301
```
Deploy again and test two of the old addresses on the `pages.dev` link.

### Step 4 · Point their domain at the new site

Do this at a quiet time for their business; the switch takes a few minutes to an hour to reach everyone.

**4a. Write down the current settings.** In Chrome, open
`https://dcc.godaddy.com/control/portfolio/<domain>/settings?tab=dns` (or My Products, then the domain,
then **DNS**). Copy every record into `<project>/go-live/BEFORE.md` and take a screenshot.

**4b. Tell Cloudflare to expect the domain.** In Chrome, open the Cloudflare dashboard, then
**Workers & Pages**, then the `<name>` project, then **Custom domains**, then **Set up a custom domain**.
Enter `www.theirsite.com`. Cloudflare shows the record GoDaddy needs (a CNAME (an alias that points one
name at another) from `www` to `<name>.pages.dev`). Keep that tab open.

**4c. Point `www` at the new site, in GoDaddy.** On the GoDaddy DNS page:
- If a record named `www` already exists (usually a CNAME to `@`, or to the website builder), **edit**
  it; there can only be one. Otherwise **Add** a new record.
- Type **CNAME**, Name **www**, Value **`<name>.pages.dev`**, TTL **1 hour** (or the shortest offered).
- Show them the filled form, wait for yes, then **Save**. Read the list back to confirm.

**4d. Send the bare address to `www`.** GoDaddy cannot point `theirsite.com` (with no `www`) straight at
Cloudflare, so forward it. On the domain's page in GoDaddy find **Forwarding** (sometimes under DNS, then
Forwarding, then Add Forwarding):
- Forward to `https://www.theirsite.com`, type **Permanent (301)**, setting **Forward only**.
- If the bare domain has an **A record** (a direct address) pointing at the old site, GoDaddy may change or
  replace it when forwarding is saved; that is expected, and it is in `BEFORE.md` if you need it back. Do NOT touch MX or TXT records.
- Show them, wait for yes, Save.

**4e. Wait and check.** Back in Cloudflare's Custom domains tab, the status turns **Active** (a few minutes,
up to an hour; it sets up the padlock (HTTPS) by itself). Then check, from this computer:
`nslookup www.theirsite.com` (should mention `pages.dev`), open `https://theirsite.com` and
`https://www.theirsite.com` in Chrome, and run `/studio-check --url https://www.theirsite.com`. If they have
email on the domain, ask them to send themselves one email and reply to it.

**Done when** both addresses show the new site with a padlock, the check is green, and their email still
works. Write the outcome and the date in `<project>/go-live/PLAN.md`.

### Undo

If anything is wrong after the switch: in GoDaddy, set the `www` record and the forwarding back to what
`BEFORE.md` says. The old site returns within the hour. For a bad change to the new site itself, Cloudflare
keeps every deploy: Workers & Pages, then the project, then **Deployments**, then the one before, then
**Rollback**.

### Every update after that

The person changes the design in this folder, then says "put it live". You run the full studio check, then
the same deploy command:
```
npx -y wrangler@4 pages deploy "<project>/site" --project-name <name> --branch main
```
To show a change before it goes live, deploy with `--branch preview` instead: it gets its own link and the
live site does not change.

### The better long-term option (offer it, never push it)

Moving the domain's nameservers (the setting that says which company answers for the domain) to Cloudflare
lets the bare address work without forwarding and makes later changes simpler. It moves ALL the domain's
records, email included, so it needs every record from `BEFORE.md` checked in Cloudflare before switching.
Only do it if they ask, after Route A has been working for a while, and walk through it as carefully as
Step 4.

## Route B · Upload to GoDaddy cPanel hosting (only if they want to stay on GoDaddy)

No preview links and no one-click undo, so the backup step is not optional.

1. **Switch on SSH** (a secure way for this computer to upload files). In Chrome: My Products, then Web
   Hosting, then **Manage**, then **Settings**, then **SSH Access**, then **Manage**, then switch it on. Some
   cheap plans do not offer it; if the switch is missing, say so and use Route A.
2. **Get the login details** from the same page: host, username and port. They type the password
   themselves when asked; better, set up a key so no password is needed: run
   `ssh-keygen -t ed25519 -f ~/.ssh/godaddy_site -N ""`, then in cPanel (Security, then SSH Access, then
   Manage SSH Keys, then Import Key) paste the contents of `~/.ssh/godaddy_site.pub` for them, and
   **Authorize** it.
3. **Back up the old site first:**
   `scp -i ~/.ssh/godaddy_site -P <port> -r <user>@<host>:public_html "<project>/go-live/old-site-files"`
   Check the folder has files in it before going on.
4. **Show the new site before it replaces the old one:** upload to a test folder first:
   `scp -i ~/.ssh/godaddy_site -P <port> -r "<project>/site" <user>@<host>:public_html/preview-new`
   and open `https://theirsite.com/preview-new/` with them. Wait for their yes.
5. **Go live:** upload the contents of `site/` into `public_html` (Windows and Mac both have `scp`). Keep
   anything in `public_html` that is not part of the old site (a `.well-known` folder, an email or SSL
   file); only replace the website's own files. Then delete `public_html/preview-new`.
6. **Old addresses:** cPanel uses an `.htaccess` file for redirects instead of `_redirects`:
   `Redirect 301 /about-us /about`, one per line.
7. **Check:** `/studio-check --url https://theirsite.com --safari`, and their email.
8. **Undo:** upload `old-site-files` back into `public_html`.

## Using Chrome well

- Load the Chrome tools in one go (ToolSearch, `select:` the Claude in Chrome tools) and open a NEW tab;
  never take over one of their tabs.
- GoDaddy and Cloudflare change their screens often. Find buttons by what they say, not by position, and
  take a screenshot when unsure. If a page asks for a login, a code or a card, hand it to them.
- Point things out as you go: "I've filled in the www record; it's highlighted on the screen. Shall I save
  it?"
- Do not click anything that opens a pop-up confirm box without warning them; it can freeze the
  connection. If one appears, ask them to click it.

## Finish

Tell them in four short lines: the live address, how to make a change from now on ("change it here, then
say put it live"), how to undo, and what they could cancel at GoDaddy in two weeks if they no longer need it
(the old website builder or hosting, never the domain or email).
