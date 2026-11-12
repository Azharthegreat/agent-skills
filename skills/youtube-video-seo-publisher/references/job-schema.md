# Job schema

Create one JSON file per app or campaign.

```json
{
  "channelId": "UCxxxxxxxxxxxxxxxxxxxxxx",
  "profileDir": "C:\\Users\\you\\AppData\\Local\\MetaCyberGuru\\YouTubePlaywrightProfile",
  "chromePath": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "app": {
    "name": "Example App",
    "playStoreUrl": "https://play.google.com/store/apps/details?id=com.example.app",
    "website": "https://www.example.com",
    "defaultTags": ["example app", "android app"]
  },
  "videos": [
    {
      "path": "D:\\campaign\\feature-short.mp4",
      "kind": "short",
      "title": "Feature Name for Android Testing | Example App #Shorts",
      "description": "Show the verified feature and its user benefit in natural language.",
      "primaryKeyword": "android testing",
      "keywords": ["feature keyword", "mobile QA"],
      "tags": ["example app", "android testing", "mobile QA"],
      "hashtags": ["#androidtesting", "#Shorts"],
      "visibility": "public",
      "madeForKids": false
    }
  ]
}
```

## Required fields

- `channelId`: exact YouTube channel ID. The script opens this channel directly before any mutation.
- `app.name`: verified app name.
- `app.playStoreUrl`: exact Google Play listing URL. It is appended when missing from a description.
- `videos[].path`: absolute local video path.
- `videos[].title`: final human-readable title, maximum 100 characters.
- `videos[].description`: factual description based on the real video and app.
- `videos[].visibility`: `public`, `unlisted`, or `private`.
- `videos[].madeForKids`: explicit Boolean.

## Optional fields

- `profileDir`: dedicated automation profile. Omit to use the safe default. Never use a normal browser profile.
- `chromePath`: Chrome executable. Omit when Chrome is installed in a standard location.
- `app.website`: approved product website appended when missing.
- `app.defaultTags`: campaign-wide tags.
- `kind`: `short` or `video`. It controls which Studio content tab is checked first, not YouTube classification.
- `primaryKeyword`, `keywords`, and `tags`: merged case-insensitively and limited to YouTube's total tag allowance.
- `hashtags`: appended to the description when absent.

## SEO checks

- One primary search intent per video.
- Title and first sentence should agree with the visible feature.
- Use keyword variants only when they accurately describe the content.
- Tags supplement spelling and topic context. They do not justify misleading titles.
- Keep descriptions useful before the links and hashtags.
- Use the canonical Play listing and approved product site. Do not add tracking parameters unless requested.

