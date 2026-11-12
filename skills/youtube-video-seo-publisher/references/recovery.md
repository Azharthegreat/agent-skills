# Recovery guide

## Dedicated profile is locked

Another publisher run or its owned Chrome window is still active. Stop and ask the user to finish or close that dedicated automation window. Never kill Chrome processes, remove Chromium singleton files, or touch normal browser profiles.

## Authentication is missing

Run the `auth` command and let the user sign in inside the dedicated Chrome window. Do not request credentials in chat. The persistent profile retains the authenticated session for later runs.

## A Publish click timed out

Do not immediately upload the file again. Run `verify` or inspect both Channel Content tabs. YouTube may have published the video even though the confirmation text changed or disappeared.

The script treats Channel Content as authoritative:

- exact title plus `Draft`: resume the draft;
- exact title plus the expected visibility and a video ID: do not re-upload;
- exact title temporarily in the regular Videos tab: verify again because Shorts classification can be delayed;
- no exact title in either tab: only then retry the upload.

## Draft exists

Use the normal `upload` command again. It opens `Edit draft`, reapplies the required metadata and audience selection, advances through the wizard, sets visibility, publishes, and verifies the final row.

## Tags selector is ambiguous

Use the exact textbox role: `getByRole('textbox', { name: 'Tags', exact: true })`. `getByLabel('Tags')` may also match YouTube's “Learn more about tags” link and fail strict mode.

## Title or description read fails

YouTube uses contenteditable elements, not normal inputs. Read them through DOM `innerText`; do not use `inputValue()` unless the element is actually an input or textarea.

## Native file picker appears

Stop the run. The supported path is the attached `input[type=file]` plus `setInputFiles()`. Do not operate the native picker, keyboard, clipboard, or mouse.

## Confirmation wording changes

Do not bind success to “Video published”. Wait briefly, then verify the exact Channel Content row, visibility, ID, description, and tags.

## Visibility is uncertain

`Draft`, missing video ID, or absent visibility is not success. Reopen the draft or edit page and verify again. Do not infer Public state from the existence of a title.

