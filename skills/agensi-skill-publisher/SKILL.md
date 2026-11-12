---
name: agensi-skill-publisher
description: "Prepare and publish agent skills (SKILL.md folders) as paid listings on the Agensi.io marketplace: clean package copies, privacy scrub, double verification, listing copy that only states real facts, a 512x512 logo and a 1080x1350 thumbnail, then drafts with a price, then submission for review, each stage gated on the user's yes. Use when the user asks to sell, list, publish or submit a skill on Agensi, write its listing or thumbnail, or fix an Agensi draft. Do not use for free GitHub-only releases unless the user also wants an Agensi listing."
license: MIT
---

# Agensi Skill Publisher

Take one or more skill folders from source to "Pending Review" on Agensi.io without changing what the
skills do, without leaking anything private, and without publishing a single thing the user has not
approved.

## Stage gates

Work in this order. Finishing one stage never authorizes the next.

1. **Read** every source skill in full (SKILL.md, references, scripts, tests).
2. **Package** a copy of each skill, scrub it, and verify it twice.
3. **Write** the listing copy and **build** the logo and thumbnail.
4. **Show everything** to the user and propose prices. Stop and wait for a yes.
5. **Create drafts** on Agensi with the approved prices. Do not submit.
6. **Submit for review** only after a second, explicit yes. Then confirm the status.
7. **Report** what went where, with links and evidence.

If any rule below fails, stop and tell the user which rule and why. Do not work around it.

## Hard rules

- **Work on copies only.** Never edit the source skill folder. Build packages in a scratch directory.
- **Do not change what a skill does.** Its technical content stays byte-identical to the source unless
  the user approves a specific edit. Never delete a section, command or reference to make a package
  smaller or cleaner. The allowed exceptions are listed in
  [references/package-and-privacy.md](references/package-and-privacy.md), and each still needs the
  user's go-ahead.
- **Paid listings always carry a price.** One-time, $5 or more (card payments need $5+). Suggest a
  price per skill, then wait for the user's yes. If the user picks less than $5, say that card
  checkout needs $5+ and ask again rather than entering it.
- **A paid skill must not stay free elsewhere.** No link in the listing to an outside shop or a free
  GitHub copy. If the skill is public on GitHub, removing it is a separate step the user must approve.
- **Only real facts.** No invented users, sales, ratings, results or metrics, in copy or images. Every
  number in a demo or thumbnail must add up and match the package. Label sample output "example run".
- **Sign-in, 2FA, KYC and payouts belong to the user.** Never type a password or handle payout details.
- **One browser for account work.** For anything on agensi.io, attach to the browser profile that is
  already signed in (over CDP). Never start a second browser or a fresh profile for it. Open a new
  tab for the work; never navigate or close a tab the user already had open. Check the signed-in
  account before touching anything. Rendering local HTML thumbnails in a throwaway headless browser
  is fine, because it never touches an account.

## Stage details

### 1. Read and collect proof points

For each skill, write down 3 to 5 proof points taken from the files themselves: exact counts
(references, scripts, tests, sections, words), concrete behaviours, guard rails, and one example run.
These feed both the copy and the thumbnail data panel.

### 2. Package, scrub and verify

Follow [references/package-and-privacy.md](references/package-and-privacy.md): copy, privacy scrub,
portability checks, `LICENSE.txt`, ZIP, then **double verification** (a regex pass and an independent
reviewer pass). Fix every finding and verify the changed files again.

### 3. Listing copy, logo and thumbnail

- Copy rules and the exact field limits: [references/listing-copy.md](references/listing-copy.md).
- Logo and thumbnail rules: [references/thumbnails.md](references/thumbnails.md).
- Keep one listing file per skill in the format of
  [references/listing-template.md](references/listing-template.md). The draft step reads from it.

### 4. Approval

Show the user, in one message: every thumbnail and logo, each listing's name, summary and price, and
the verification results. Flag open questions (for example a `license: MIT` frontmatter on a paid
package). Wait.

### 5. Drafts

Follow [references/agensi-form.md](references/agensi-form.md). It records how the Agensi form really
behaves: which inputs to target, how chips and FAQ rows save, and what looks like data loss but is
not. For every draft: upload the ZIP and logo, set One-time and the approved price, fill every field
from the listing file, leave the "Agensi tools" section empty ("Continue without tools"), wait for
"All changes saved", then **reload the draft and re-read every field** before moving on.

### 6. Submit

Only after the user says yes to submitting. Confirm the "Final review before submission" dialog, and
choose "Continue without tools" if the tools prompt appears. Afterwards open Creator Studio and
confirm each skill shows "Pending Review" (or "Live").

### 7. Report

Short, in the language the user writes in (Roman Urdu if they write Roman Urdu). This applies to
the report only; listing copy stays in English. Include: what was
published where (links), prices, what each verification pass found and fixed, and anything not
verified. Never claim done without evidence.
