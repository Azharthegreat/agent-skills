# Logo and thumbnail

## Design floor

- No purple-to-blue gradients, no emoji as icons, no fake browser or OS windows, no invented metrics,
  testimonials or logos.
- At most 2 font families (for example Archivo 500/700/800 for text, JetBrains Mono for data panels).
  Body text 24px or larger.
- One accent colour per skill, the same in the logo, the thumbnail and the price badge.

## Logo (512x512 PNG)

Dark solid background (#14161A), one simple geometric mark that shows the skill's idea (arrow up for
a launch, bar chart for an estimate, hub and nodes for orchestration, shield for mitigations), in the
accent colour. No text. Agensi accepts up to 5 MB.

## Feed thumbnail (1080x1350 PNG; 1200x1200 if asked)

Top to bottom:

- The logo plus the skill name, and a small accent label such as "NOW LIVE ON AGENSI" only if it is
  actually live.
- A big headline, 90 to 100px, two lines, 4 to 7 words, naming the outcome
  ("Hours you can defend to a client.").
- A sub-line, 28 to 32px, 1 to 2 sentences on what the agent does.
- A data panel from a real example run of the skill: 5 to 6 rows, label left, value right in the
  accent colour. Neutral colour for "needs you" or "waiting" states. Values match the listing demo and
  add up.
- Footer: the price badge in the accent colour, "Works in Claude Code, Codex, Cursor", and
  "by <Author Name> · agensi.io".
- One large soft accent circle in the top-right corner for depth.

## Build

Write each card as an HTML file with a fixed-size `#card` element and screenshot that element with a
throwaway headless browser (local files only, no account involved, so the one-browser rule for
account work does not apply): Playwright's `locator('#card').screenshot()`, or a capture script you already have.
If the capture tool names output files by page, give each render its own name or they overwrite each
other.

## Check every PNG

Open each image and confirm:

- no text is cut off;
- every number adds up and matches the listing demo;
- the price is right;
- nothing private shows (balances, notifications, emails, real phone numbers or IDs). If you used a
  screenshot of a real page, crop out all logged-in UI first.

Send all images to the user in one message.
