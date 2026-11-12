# Listing file template

One markdown file per skill. Keep these headings exactly: the draft step finds each field by its
heading, and the demo result runs from "## Demo: The result" to "## Compatibility Note".

```markdown
## Skill Name
<60 characters or fewer>

## Summary
<300 characters or fewer>

## Full Description
<markdown, 1,500 to 2,500 characters>

## Demo: The request
<what the buyer types>

## Demo: The result
<700+ characters, labelled as an example run>

## Compatibility Note
<one or two sentences on which agents and platforms it works with>

## Requires
- <plain item>

## Optional
- <plain item>

## Tools Used
- <Read Files / Write Files / Terminal / Shell / Browser / Network Access / Environment Variables>

## Categories
<Primary>, <Second>

## Tags
<tag-one>, <tag-two>, ...

## FAQ
(exactly 4 questions)
**<question 1>**
<answer 1>

**<question 2>**
<answer 2>

**<question 3>**
<answer 3>

**<question 4>**
<answer 4>

## Known limitations
<2 to 4 sentences>

## Price
One-time $<amount>
```

## Extras file

Keep the list fields as JSON next to the listing so they can be entered and re-checked mechanically:

```json
{
  "faq": [["Question one?", "Answer one."], ["Question two?", "Answer two."],
          ["Question three?", "Answer three."], ["Question four?", "Answer four."]],
  "limitations": "Two to four honest sentences.",
  "categories": ["Security", "Research & Analysis"],
  "tags": ["tag-one", "tag-two"],
  "requires": ["Claude Code or Codex or Cursor"],
  "optional": ["WinDbg", "Windows lab VM"]
}
```
