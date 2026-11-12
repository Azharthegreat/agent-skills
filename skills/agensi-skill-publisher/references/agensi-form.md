# The Agensi submit form, as it really behaves

Observed on agensi.io in November 2026. The site can change: if a selector below finds nothing,
inspect the page again rather than guessing, and update this file.

## Browser setup

- Attach over CDP to the browser profile that is already signed in to Agensi. Never start a second
  browser or a fresh profile.
- Open a new tab for the work. On recent Chrome-based browsers the DevTools endpoint needs `PUT`:
  `PUT http://127.0.0.1:<port>/json/new?https://www.agensi.io/dashboard/submit` (a plain `GET` is
  rejected). Never navigate or close a tab the user already had open.
- Confirm the account first: the dashboard greets the signed-in creator by name and shows
  "Creator Mode Active".

## Draft URLs

- `https://www.agensi.io/dashboard/submit` with no query starts a **new** draft. The ZIP upload
  creates it and the URL gains `?draft=<uuid>`. Record that id.
- `https://www.agensi.io/dashboard/submit?draft=<uuid>` edits that draft. Before uploading a new
  skill, check the URL has no `draft=`, or you will overwrite another listing.

## Typing into fields

The page is React. Setting `.value` from script does not register. Focus the element, select all
(Ctrl+A), then send CDP `Input.insertText`. Wait about 400 ms between fields.

## Steps and selectors

| Step | Field | Selector / note |
| --- | --- | --- |
| 1 | Skill ZIP | `#skill-zip-input` (auto-fills name and description from the frontmatter; overwrite them) |
| - | Agensi tools | Optional section. Leave it empty; this is "Continue without tools" |
| 2 | Logo | the `input[type=file][accept="image/*"]` whose surrounding text contains "Skill logo" (do not pick by index: the editors and screenshots have their own image inputs) |
| 2 | Name | `#name`, 60 max |
| 2 | Summary | `#summary`, 300 max |
| 2 | Full description | the `textarea` whose placeholder starts "Describe what your skill does" |
| 3 | Demo request | `#sampleInput` |
| 3 | Demo result | `#sampleOutput` (the form asks for 700+ characters) |
| 4 | Compatibility | `#compatibilityNote` |
| 5 | Pricing | click the "One-time" option, then `#price` |

Collapsible "Recommended" sections (open each by its heading text before filling or reading):

| Section | Contents |
| --- | --- |
| Tags, Categories, Usecases | tag input `input[placeholder="Add a tag"]` (type, press Enter); category buttons |
| Permissions | Requires `#skill-requirements`, Optional `#skill-optional-requirements`, "Select services", "Permissions required" (auto-detected; check they match what the skill really uses) |
| Extra Details | "Known limitations" sub-section with `#knownLimitations` |
| FAQ | question and answer rows plus an "Add FAQ" button |

Screenshots (optional): up to 6 images, 10 MB each.

## Categories

Category buttons use `aria-pressed="true"` when selected. Up to 3. The **first one pressed becomes
Primary**. To set the order reliably: unpress every pressed button, then click them in the order you
want and read back "Primary" and "#2". Clearing and re-adding in one pass can flip the primary.

Categories seen in November 2026: Agents & Orchestration, Prompt & Skill Engineering, LLM Ops,
Frontend & Web Apps, Mobile Development, APIs & Backend, Code Quality & Review, Testing & Debugging,
DevOps & Cloud, Data & Databases, Web3 & Crypto, Security, Technical Documentation, Marketing & SEO,
Sales & Lead Gen, Social Media, E-commerce, Digital Products, Research & Analysis, Business &
Operations, Product Management, Workflow Automation, Productivity, Finance & Accounting, Legal &
Compliance, Trading & Investing, HR & Recruiting, Writing & Content, Branding & Design, UX & UI Design,
Image & Video, Education & Learning, Translation & Localization, Game Development.

## Requires and Optional chips

1. One plain phrase per chip. An item with a domain-like dot ("SKILL.md", "crt.sh") is dropped
   silently, and so can items with commas or brackets. The input clears as if it worked, but no chip
   appears.
2. To add: focus the input and wait 300 ms, `Input.insertText`, then click the input's own sibling
   button, `input.parentElement.querySelector('button')`, with a real mouse event at its centre. Wait
   600 ms. Never click a page-wide "Add"; there are several.
3. Verify only from the rendered lists: `ul[aria-label="Requires"] li span` and
   `ul[aria-label="Optional"] li span`. The Optional list exists only after its first chip.
4. Auto-fill injects chips of its own ("Windows", "Python", "Git", "Linux only"). Remove them with
   `button[aria-label="Remove <chip text>"]` (or the button inside that `li`), then re-check once at the
   end, because auto-fill can re-add.

## FAQ rows

The section always ends with an editable "New question" / "Answer" row. **"Add FAQ" saves whatever is
in that row** and opens a fresh empty one.

1. Open the FAQ section; its heading button's `parentElement` is the FAQ root.
2. Clear old rows: click every "×" inside the FAQ root until none are left.
3. For each Q&A: click "Add FAQ", wait 800 ms, type the question into the last `input` in the FAQ
   root and the answer into the last `textarea`, then press Tab.
4. **Click "Add FAQ" once more after the last answer.** Without it the last Q&A stays in the unsaved
   row and is gone after a reload.
5. The empty trailing row that remains is the form's own input row. It is not saved as an FAQ.

## Saving and verifying

- The page autosaves and shows "All changes saved". Wait for it before leaving a draft.
- Verify by reloading the draft and reading everything back. After a reload the Recommended sections
  are collapsed; open them by name first, or every field in them reads as empty and looks like data
  loss.
- Compare lengths against the listing file: name, summary, description, demo request and result,
  compatibility, limitations. Check price, logo, categories with Primary, all tags, 4 FAQ pairs with
  text, and both chip lists.

## Submit (only after the user's explicit yes)

- Click the enabled "Submit for review" button.
- A "Final review before submission" dialog asks you to confirm the auto-filled fields and the
  auto-detected permissions. Confirm with its "Submit for review" button.
- Some drafts show an "Add tools?" dialog: choose "Continue without tools".
- Success returns to `/dashboard`. Then open Creator Studio (`/dashboard#my-skills`): the totals show
  Live and Pending counts, and each skill card shows "Pending Review" / "In review" with its price.
