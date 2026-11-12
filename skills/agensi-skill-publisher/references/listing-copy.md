# Listing copy

Every claim comes from what the skill really does. Use the proof points collected in stage 1.

## A. Skill name (60 characters or fewer)

- Format: `<Plain name>: <outcome the buyer wants>`, for example
  "Android App Launch: From Finished Build to Google Play".
- The outcome half names a result, not a feature. No hype words (ultimate, best, powerful, magic).

## B. Summary (300 characters or fewer, count it with `len()` or an equivalent, never by eye)

- Sentence 1: what the agent does for the buyer, with concrete nouns (tools, files, platforms).
- Sentence 2: the guard rail or differentiator ("Nothing goes live without your yes.").

## C. Full description (markdown, 1,500 to 2,500 characters)

1. Opening, 2 to 3 sentences: the real pain, named through specific failure moments the skill
   prevents. The first line is never a question.
2. "What your agent does": 4 to 6 bold-led bullets, one concrete action each.
3. "Built-in guard rails": 2 to 4 bullets (approvals, no secrets in files, validation).
4. "What's inside": exact counts (SKILL.md, N references, N scripts, N tests, or words and sections
   for a single-file skill). Verify every number against the package.
5. Optional "Modes" or "Works with" line.

## D. Demo

- **Request**: a realistic prompt a buyer would type, 1 to 3 sentences, about a fictional project
  (NotesApp, a Next.js SaaS).
- **Result**: 700+ characters of structured sample output: a heading, a status line, a table, short
  sections, and a "Needs you" or "Next" step. Label it as an example run. Re-check every total and
  every computed value (for example a CVSS vector must produce the score shown).

## E. FAQ

Exactly 4 questions buyers really ask: approval, secrets or keys, requirements, "what if I don't use
X". Answers of 1 to 2 sentences.

## F. Known limitations

2 to 4 honest sentences: requirements, and what the user must do themselves.

## G. Tags and categories

6 to 8 lowercase search terms. The primary category is the one where buyers of this skill browse
(the category list is in [agensi-form.md](agensi-form.md)).

## Requires and Optional

Short plain phrases, one item each ("Python 3.10 or newer", "Claude Code or Codex or Cursor",
"WinDbg"). Avoid commas, brackets and domain-like dots inside an item; the form drops those silently.

## Writing rules (all human-facing copy)

- English. No em dashes. Contractions where natural.
- No AI filler: leverage, seamless, robust, comprehensive, game-changer, unlock, elevate, empower,
  delve, streamline.
- No "It's not X, it's Y". No "Here's what/how" openers. No "The result?" bridges.
- At most one contrast and one triple per text.
- Specific numbers beat adjectives. One concrete detail per paragraph.
- Only real facts. Label sample output "example run".
- If a humanizer skill is installed, run it (rewrite pass, then audit pass) and report its findings.
  Otherwise use this list as the audit checklist.

## LinkedIn post variant (only if the user asks)

- First line is a real number or a short real fact ("Six releases.").
- 900 to 1,300 characters, paragraphs of 1 to 2 sentences, a closing question,
  "Link in the first comment.", 0 to 2 hashtags, no links in the body.
- One post per skill. Never reuse a hook or structure across the set.
