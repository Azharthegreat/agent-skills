---
name: youtube-video-seo-publisher
description: Upload, publish, recover, SEO-optimize, and verify YouTube videos through a dedicated persistent Chrome profile using Playwright APIs. Use for YouTube Studio uploads that must preserve login cookies, avoid native file pickers and mouse automation, add app links and search-focused metadata, resume drafts safely, prevent duplicates, and leave every unrelated browser profile untouched.
---

# YouTube Video SEO Publisher

Publish through the provided Playwright script, not through desktop automation. Use a dedicated persistent Chrome profile owned by this skill so the user signs in once and later runs reuse the stored session.

## Non-negotiable browser isolation

- Never point `profileDir` at Chrome, Brave, Edge, Cursor, Playwright MCP, or another browser's normal user-data directory.
- Never attach to, enumerate, close, kill, unlock, copy, or modify another browser profile or process.
- Never use Computer Use, Windows UI Automation, mouse movement, clipboard automation, a native upload dialog, or a file picker.
- Assign media only with Playwright `locator('input[type="file"]').setInputFiles(...)`.
- Store authentication only in the dedicated persistent profile. Never export or print cookies, tokens, headers, passwords, or profile files.
- If the dedicated profile is locked by another run, stop and report it. Do not terminate anything to recover.

The default persistent profile is `%LOCALAPPDATA%\MetaCyberGuru\YouTubePlaywrightProfile` on Windows. A job may select another dedicated directory, but the isolation rules still apply.

## Prepare the job

Read [references/job-schema.md](references/job-schema.md), inspect the real app and videos, then create a job JSON outside the skill folder. Do not invent features, rankings, performance claims, reviews, or privacy claims.

For every video:

- choose one clear search intent and a natural primary keyword;
- write a specific title under 100 characters;
- put the primary topic naturally in the opening description sentence;
- explain only features visible in the supplied app or video;
- include the app's exact Google Play URL and the approved website URL;
- use focused, non-duplicative tags and a small number of relevant hashtags;
- set the intended visibility explicitly;
- set `madeForKids` accurately, never by assumption when the audience is unclear.

SEO copy must read naturally. Repeating keywords, stuffing tags, or adding unrelated high-volume phrases is not optimization.

## First authentication

Install the one dependency first, inside this skill folder: `npm install`. Then run once:

```powershell
node scripts/youtube-publisher.mjs auth path\to\youtube-job.json
```

The script opens its own Chrome window. If YouTube requests authentication, pause for the user to sign in. The script waits for YouTube Studio access, saves the session inside the dedicated profile, and closes only the window it launched. Future runs reuse that session.

Do not ask the user to supply Google credentials in chat or a job file.

## Validate, upload, and verify

Run in this order:

```powershell
node scripts/youtube-publisher.mjs validate path\to\youtube-job.json
node scripts/youtube-publisher.mjs upload path\to\youtube-job.json
node scripts/youtube-publisher.mjs verify path\to\youtube-job.json
```

The upload command is idempotent by exact title:

- an already published entry is not uploaded again;
- an exact-title draft is resumed and published;
- a new file is assigned directly to the hidden file input;
- title, description, audience, visibility, and tags are applied;
- confirmation text is not trusted because YouTube changes it;
- success requires an exact-title Channel Content row, no Draft state, expected visibility, a video ID, and verified saved metadata.

If a run fails, read [references/recovery.md](references/recovery.md). Retry only after checking Channel Content, because a Publish click may succeed even when a confirmation wait fails.

## Completion standard

Report a video as published only when the final verification returns `PASS` with:

- exact final title;
- expected visibility;
- YouTube video ID and public URL;
- matching saved description;
- required Google Play and website links;
- every requested tag present;
- no Draft state.

Clearly label authentication, processing, policy review, or unavailable external state as not verified. Do not claim search ranking from metadata completion alone.

