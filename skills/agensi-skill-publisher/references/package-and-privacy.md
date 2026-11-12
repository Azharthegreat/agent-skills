# Package, privacy scrub and double verification

## Copies only

Copy each source skill folder into a scratch build directory and work there. The source stays
untouched. At the end, prove the technical content did not change: compare each packaged `SKILL.md`
and script byte for byte against the source (`cmp -s`, or a hash). Line-ending differences (CRLF vs
LF) make a plain `diff` report every line as changed; normalize before diffing or use `cmp`.

## What may change in a package

Nothing that changes how the skill behaves. The only edits allowed, and each one only after the user
approves it:

- removing private data listed under "Privacy scrub" below, including (for paid listings) the
  author's own app names, package names and private anecdotes; show the user the scrub diff once and
  get one approval for it;
- replacing a dead link the user names (leave every working third-party link alone);
- fixing a factual or technical error the user agrees is wrong;
- adding `LICENSE.txt` beside `SKILL.md` (a new file, not an edit).

If a source file conflicts with the sale (for example frontmatter `license: MIT` on a paid package),
do not edit it. Report the conflict and let the user decide.

## Privacy scrub

Remove, or replace with fictional placeholders (Notes app, `com.example.*`, `example.com`,
`192.0.2.x`, `PHONE_A_SERIAL`):

- personal emails, phone numbers, postal addresses, national ID and company registry numbers;
- passwords, API keys, tokens, keystore passwords, service-account JSON;
- cloud project IDs, analytics property IDs, ad network IDs, store developer IDs, document and
  spreadsheet IDs, channel IDs, unlisted video URLs, session or ticket IDs;
- device serials, LAN IPs, OS usernames, absolute local paths (`D:/...`, `C:/Users/...`, `/home/...`);
- for paid listings: the author's own app names, package names, store links, and private anecdotes
  with exact internal numbers;
- real-looking phone numbers or personal records in screenshots and examples.

## Portability and correctness

- No references to files that exist only in the author's private repo. Ship a generic version of any
  document the skill depends on, or say "bring your own".
- Every link and file reference inside the skill must resolve. Use relative paths.
- List requirements in `SKILL.md`: language versions, package installs, connectors, accounts.
- Run any bundled tests and validators before and after edits, and confirm behaviour is unchanged.
- Nothing that misleads platforms or users: answer AI-disclosure questions truthfully, never bypass a
  CAPTCHA or anti-bot check, never scrape personal data, and put a caveat on destructive commands.

## License file (paid package)

`LICENSE.txt` beside `SKILL.md`:

```
Copyright (c) <year> <Author Name>. All rights reserved.
Licensed to buyers through Agensi.
```

## ZIP

One ZIP per skill containing the cleaned folder with `SKILL.md` (Agensi rejects a ZIP without one;
50 MB max). If `zip` is not installed, Python's `zipfile` module works on every platform.

## Double verification (mandatory, before any upload)

**Pass 1, regex scan** of every packaged file and every listing file for: secrets and key formats,
emails, phone numbers, IPs, absolute local paths, private IDs, client names, and the em dash
character. Every hit is either fixed or explained. Starter patterns (add the author's own names,
handles and client names to the last one):

```
em dash          \u2014   (the U+2014 character)
email            [\w.+-]+@[\w-]+\.[\w.]+
IPv4             \b\d{1,3}(\.\d{1,3}){3}\b          (192.0.2.x and 127.0.0.1 are fine)
Windows path     [A-Za-z]:[\\/]
home path        /home/\w|/Users/\w
UUID             [0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}
Google API key   AIza[0-9A-Za-z_-]{20,}
OpenAI key       sk-[A-Za-z0-9]{20,}
GitHub token     gh[pousr]_[A-Za-z0-9]{20,}
AdMob ID         ca-app-pub-\d+
private words    (?i)<author name>|<handle>|<client names>
```

**Pass 2, independent reviewer.** A separate agent reads every file in full, without being told your
conclusions, and checks: privacy, client content, copied third-party content, harmful instructions,
broken references, and whether every listing claim matches the package (counts, features, numbers in
the demo). If the reviewer cannot read some content (for example a safety filter on security
material), do that check yourself, and list in the report exactly which files and which checks you
did yourself and why.

Fix all findings, then re-verify the changed files. Recount every number in demos and thumbnails.

## Paid skill also on GitHub

A paid skill must not stay free. If it is public, removing it and its history (rewrite the commit, or
delete and recreate the repository) is a destructive step: describe it and get the user's yes first.
Afterwards confirm the old commit URL returns 404.
