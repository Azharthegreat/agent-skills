import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const COMMANDS = new Set(['auth', 'validate', 'upload', 'verify']);
const VISIBILITIES = new Set(['public', 'unlisted', 'private']);

function fail(message) {
  throw new Error(message);
}

function loadPlaywright() {
  const candidates = [
    'playwright',
    process.env.PLAYWRIGHT_MODULE,
  ].filter(Boolean);
  for (const candidate of candidates) {
    try {
      return require(candidate);
    } catch {}
  }
  fail('Playwright is unavailable. Run npm install once in this skill folder or set PLAYWRIGHT_MODULE to the Playwright package path.');
}

function normalize(value = '') {
  return String(value).replace(/\r\n/g, '\n').trim();
}

function unique(values = []) {
  const seen = new Set();
  return values.map(value => normalize(value)).filter(value => {
    const key = value.toLowerCase();
    if (!value || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function limitTags(tags) {
  const kept = [];
  let used = 0;
  for (const tag of unique(tags)) {
    const next = tag.length + (kept.length ? 1 : 0);
    if (used + next > 500) break;
    kept.push(tag);
    used += next;
  }
  return kept;
}

function defaultProfileDir() {
  const base = process.env.LOCALAPPDATA || path.join(os.homedir(), 'AppData', 'Local');
  return path.join(base, 'MetaCyberGuru', 'YouTubePlaywrightProfile');
}

function assertDedicatedProfile(profileDir) {
  const resolved = path.resolve(profileDir);
  const local = process.env.LOCALAPPDATA || '';
  const forbidden = [
    path.join(local, 'Google', 'Chrome', 'User Data'),
    path.join(local, 'BraveSoftware', 'Brave-Browser', 'User Data'),
    path.join(local, 'Microsoft', 'Edge', 'User Data'),
    path.join(local, 'ms-playwright-mcp'),
  ].filter(Boolean).map(value => path.resolve(value).toLowerCase());
  const lower = resolved.toLowerCase();
  if (forbidden.some(root => lower === root || lower.startsWith(`${root}${path.sep}`))) {
    fail(`profileDir must be a dedicated automation directory, not a normal browser profile: ${resolved}`);
  }
  return resolved;
}

function resolveChrome(configuredPath) {
  const candidates = [
    configuredPath,
    process.env.CHROME_PATH,
    process.platform === 'win32' ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe' : '',
    process.platform === 'win32' ? 'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe' : '',
    process.platform === 'darwin' ? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' : '',
    process.platform === 'linux' ? '/usr/bin/google-chrome' : '',
    process.platform === 'linux' ? '/usr/bin/google-chrome-stable' : '',
  ].filter(Boolean);
  const found = candidates.find(candidate => fs.existsSync(candidate));
  if (!found) fail('Google Chrome executable was not found. Set chromePath in the job or CHROME_PATH.');
  return found;
}

function prepareVideo(raw, app, requireFile) {
  if (!raw || typeof raw !== 'object') fail('Each videos[] item must be an object.');
  const title = normalize(raw.title);
  if (!title) fail('Each video requires a title.');
  if (title.length > 100) fail(`Title exceeds 100 characters: ${title}`);
  if (!raw.path || !path.isAbsolute(raw.path)) fail(`Video path must be absolute: ${raw.path || title}`);
  if (requireFile && !fs.existsSync(raw.path)) fail(`Video file not found: ${raw.path}`);
  const visibility = String(raw.visibility || '').toLowerCase();
  if (!VISIBILITIES.has(visibility)) fail(`Invalid visibility for '${title}': ${visibility}`);
  if (typeof raw.madeForKids !== 'boolean') fail(`madeForKids must be true or false for '${title}'.`);

  let description = normalize(raw.description);
  if (!description) fail(`Description is required for '${title}'.`);
  if (!description.includes(app.playStoreUrl)) description += `\n\nDownload ${app.name}: ${app.playStoreUrl}`;
  if (app.website && !description.includes(app.website)) description += `\nLearn more: ${app.website}`;
  const hashtags = unique(raw.hashtags || []).map(tag => tag.startsWith('#') ? tag : `#${tag}`);
  const missingHashtags = hashtags.filter(tag => !description.toLowerCase().includes(tag.toLowerCase()));
  if (missingHashtags.length) description += `\n\n${missingHashtags.join(' ')}`;
  if (description.length > 5000) fail(`Description exceeds 5000 characters: ${title}`);

  const tags = limitTags([
    ...(app.defaultTags || []),
    raw.primaryKeyword,
    ...(raw.keywords || []),
    ...(raw.tags || []),
  ]);
  if (!tags.length) fail(`At least one accurate keyword or tag is required for '${title}'.`);

  return {
    ...raw,
    title,
    description,
    visibility,
    tags,
    kind: raw.kind === 'video' ? 'video' : 'short',
  };
}

function loadJob(filePath, requireFiles) {
  if (!filePath) fail('A job JSON path is required.');
  const absolute = path.resolve(filePath);
  if (!fs.existsSync(absolute)) fail(`Job file not found: ${absolute}`);
  const raw = JSON.parse(fs.readFileSync(absolute, 'utf8'));
  if (!/^UC[A-Za-z0-9_-]+$/.test(raw.channelId || '')) fail('channelId must be an exact YouTube channel ID beginning with UC.');
  if (!raw.app?.name) fail('app.name is required.');
  if (!/^https:\/\/play\.google\.com\/store\/apps\/details\?id=/.test(raw.app?.playStoreUrl || '')) {
    fail('app.playStoreUrl must be the canonical HTTPS Google Play app URL.');
  }
  if (!Array.isArray(raw.videos) || !raw.videos.length) fail('videos[] must contain at least one item.');
  const profileDir = assertDedicatedProfile(raw.profileDir || defaultProfileDir());
  const chromePath = resolveChrome(raw.chromePath);
  const videos = raw.videos.map(video => prepareVideo(video, raw.app, requireFiles));
  const titles = videos.map(video => video.title.toLowerCase());
  if (new Set(titles).size !== titles.length) fail('Duplicate exact titles exist inside this job.');
  return { ...raw, profileDir, chromePath, videos, jobPath: absolute };
}

function processExists(pid) {
  if (!Number.isInteger(pid) || pid <= 0) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

function acquireLock(profileDir) {
  fs.mkdirSync(profileDir, { recursive: true });
  const lockPath = path.join(profileDir, '.youtube-publisher.lock');
  try {
    const fd = fs.openSync(lockPath, 'wx');
    fs.writeFileSync(fd, JSON.stringify({ pid: process.pid, startedAt: new Date().toISOString() }));
    fs.closeSync(fd);
  } catch (error) {
    if (error.code !== 'EEXIST') throw error;
    let owner = {};
    try { owner = JSON.parse(fs.readFileSync(lockPath, 'utf8')); } catch {}
    if (processExists(Number(owner.pid))) {
      fail(`The dedicated YouTube publisher profile is already in use by PID ${owner.pid}. Finish that run instead of closing any browser process.`);
    }
    fs.rmSync(lockPath);
    return acquireLock(profileDir);
  }
  return () => {
    try { fs.rmSync(lockPath); } catch {}
  };
}

async function readEditable(locator) {
  return locator.evaluate(element => ('value' in element ? element.value : element.innerText));
}

function studioUrl(job, type = 'short') {
  return `https://studio.youtube.com/channel/${job.channelId}/videos/${type === 'video' ? 'upload' : 'short'}`;
}

async function openContent(page, job, type = 'short') {
  await page.goto(studioUrl(job, type), { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.getByRole('button', { name: /^Create$/ }).waitFor({ state: 'visible', timeout: 60000 });
  await page.waitForTimeout(2000);
}

async function ensureAuthentication(page, job, interactive) {
  await page.goto(studioUrl(job, 'video'), { waitUntil: 'domcontentloaded', timeout: 120000 });
  const create = page.getByRole('button', { name: /^Create$/ });
  if (await create.waitFor({ state: 'visible', timeout: 60000 }).then(() => true).catch(() => false)) return;
  if (!interactive) fail('The dedicated profile is not authenticated. Run the auth command and sign in once.');
  console.log('AUTH_REQUIRED Sign in to the requested YouTube channel inside the dedicated Chrome window.');
  await create.waitFor({ state: 'visible', timeout: 15 * 60 * 1000 });
  if (!page.url().includes(job.channelId)) {
    await page.goto(studioUrl(job, 'video'), { waitUntil: 'domcontentloaded', timeout: 120000 });
    await create.waitFor({ state: 'visible', timeout: 60000 });
  }
  console.log('AUTH_SAVED Dedicated YouTube session is ready.');
}

function parseVisibility(text) {
  for (const value of VISIBILITIES) {
    const label = value[0].toUpperCase() + value.slice(1);
    if (new RegExp(`(^|\\n)${label}($|\\n)`, 'm').test(text)) return value;
  }
  return '';
}

async function entriesOnPage(page, title, type) {
  const rows = page.locator('ytcp-video-row');
  const entries = [];
  for (let index = 0; index < await rows.count(); index += 1) {
    const row = rows.nth(index);
    const link = row.locator('#video-title').first();
    const rowTitle = normalize((await link.getAttribute('title')) || await link.innerText().catch(() => ''));
    if (rowTitle !== title) continue;
    const text = await row.innerText();
    const href = await link.getAttribute('href');
    const id = (href || '').match(/\/video\/([^/]+)\/edit/)?.[1] || '';
    entries.push({ type, text, href: href || '', id, draft: /(^|\s)Draft(\s|$)/.test(text), visibility: parseVisibility(text) });
  }
  return entries;
}

async function findEntry(page, job, video) {
  const order = video.kind === 'video' ? ['video', 'short'] : ['short', 'video'];
  const entries = [];
  for (const type of order) {
    await openContent(page, job, type);
    entries.push(...await entriesOnPage(page, video.title, type));
  }
  return entries.find(entry => !entry.draft && entry.id) || entries.find(entry => entry.draft) || entries[0] || null;
}

async function setAudience(page, madeForKids) {
  const label = madeForKids ? "Yes, it's 'Made for Kids'" : "No, it's not 'Made for Kids'";
  const choice = page.getByText(label, { exact: false }).last();
  await choice.scrollIntoViewIfNeeded();
  await choice.click();
}

async function advanceWizard(page) {
  for (let step = 0; step < 3; step += 1) {
    const next = page.getByRole('button', { name: 'Next', exact: true }).last();
    await next.waitFor({ state: 'visible', timeout: 120000 });
    await next.click();
  }
}

async function setWizardVisibility(page, visibility) {
  await page.getByText(visibility[0].toUpperCase() + visibility.slice(1), { exact: true }).last().click();
  const actionName = visibility === 'private' ? 'Save' : 'Publish';
  const action = page.getByRole('button', { name: actionName, exact: true }).last();
  await action.waitFor({ state: 'visible', timeout: 120000 });
  await action.click();
}

async function fillWizardMetadata(page, video) {
  const title = page.getByLabel('Add a title that describes your video (type @ to mention a channel)').last();
  const description = page.getByLabel('Tell viewers about your video (type @ to mention a channel)').last();
  await title.waitFor({ state: 'visible', timeout: 60000 });
  await title.fill(video.title);
  await description.fill(video.description);
  await setAudience(page, video.madeForKids);
}

async function uploadNew(page, job, video) {
  await openContent(page, job, video.kind);
  await page.getByRole('button', { name: /^Create$/ }).click();
  await page.getByText('Upload videos', { exact: true }).click();
  const fileInput = page.locator('input[type="file"]').last();
  await fileInput.waitFor({ state: 'attached', timeout: 30000 });
  await fileInput.setInputFiles(video.path);
  await fillWizardMetadata(page, video);
  await advanceWizard(page);
  await setWizardVisibility(page, video.visibility);
}

async function resumeDraft(page, job, video, entry) {
  await openContent(page, job, entry.type);
  const row = page.locator('ytcp-video-row').filter({ hasText: video.title }).first();
  await row.getByText('Edit draft', { exact: true }).click();
  await fillWizardMetadata(page, video);
  await advanceWizard(page);
  await setWizardVisibility(page, video.visibility);
}

async function waitForPublishedEntry(page, job, video) {
  for (let attempt = 0; attempt < 18; attempt += 1) {
    await page.waitForTimeout(attempt ? 5000 : 7000);
    const entry = await findEntry(page, job, video);
    if (entry?.id && !entry.draft) return entry;
    if (entry?.draft && attempt >= 2) return entry;
  }
  return null;
}

async function setEditorVisibility(page, visibility) {
  const button = page.getByRole('button', { name: 'Edit video visibility status', exact: true });
  if (!await button.isVisible().catch(() => false)) return;
  await button.click();
  await page.getByText(visibility[0].toUpperCase() + visibility.slice(1), { exact: true }).last().click();
  await page.getByRole('button', { name: 'Save', exact: true }).last().click();
  await page.waitForTimeout(2000);
}

async function applySeo(page, job, video, id, update) {
  await page.goto(`https://studio.youtube.com/video/${id}/edit`, { waitUntil: 'domcontentloaded', timeout: 120000 });
  const title = page.getByLabel('Add a title that describes your video (type @ to mention a channel)');
  const description = page.getByLabel('Tell viewers about your video (type @ to mention a channel)');
  await title.waitFor({ state: 'visible', timeout: 60000 });
  let changed = false;
  if (normalize(await readEditable(title)) !== video.title) {
    if (!update) fail(`Title mismatch for ${id}.`);
    await title.fill(video.title);
    changed = true;
  }
  if (normalize(await readEditable(description)) !== video.description) {
    if (!update) fail(`Description mismatch for ${id}.`);
    await description.fill(video.description);
    changed = true;
  }
  const showMore = page.getByText('Show more', { exact: true }).last();
  if (await showMore.isVisible().catch(() => false)) await showMore.click();
  const tagInput = page.getByRole('textbox', { name: 'Tags', exact: true });
  await tagInput.waitFor({ state: 'visible', timeout: 30000 });
  const chipBar = tagInput.locator('xpath=ancestor::ytcp-free-text-chip-bar');
  let tagText = (await chipBar.innerText()).toLowerCase();
  const missing = video.tags.filter(tag => !tagText.includes(tag.toLowerCase()));
  if (missing.length) {
    if (!update) fail(`Missing tags for ${id}: ${missing.join(', ')}`);
    await tagInput.fill(missing.join(','));
    await tagInput.press('Enter');
    changed = true;
  }
  if (changed) {
    const save = page.getByRole('button', { name: 'Save', exact: true }).last();
    await save.waitFor({ state: 'visible', timeout: 30000 });
    await save.click();
    await page.waitForTimeout(2500);
  }
  if (normalize(await readEditable(title)) !== video.title) fail(`Saved title verification failed for ${id}.`);
  if (normalize(await readEditable(description)) !== video.description) fail(`Saved description verification failed for ${id}.`);
  tagText = (await chipBar.innerText()).toLowerCase();
  const stillMissing = video.tags.filter(tag => !tagText.includes(tag.toLowerCase()));
  if (stillMissing.length) fail(`Saved tag verification failed for ${id}: ${stillMissing.join(', ')}`);
}

async function verifyVideo(page, job, video, update) {
  let entry = await findEntry(page, job, video);
  if (!entry) fail(`No Channel Content entry found for '${video.title}'.`);
  if (entry.draft) fail(`Video is still a Draft: '${video.title}'.`);
  if (!entry.id) fail(`Video ID is unavailable for '${video.title}'.`);
  await applySeo(page, job, video, entry.id, update);
  if (update && entry.visibility !== video.visibility) await setEditorVisibility(page, video.visibility);
  entry = await findEntry(page, job, video);
  if (entry.visibility !== video.visibility) {
    fail(`Visibility mismatch for '${video.title}': expected ${video.visibility}, found ${entry.visibility || 'unknown'}.`);
  }
  const url = `https://youtu.be/${entry.id}`;
  console.log(`PASS | ${video.title} | ${entry.visibility} | ${url}`);
  return { ...entry, url };
}

async function uploadVideo(page, job, video) {
  let entry = await findEntry(page, job, video);
  if (entry?.draft) {
    console.log(`RESUME_DRAFT ${video.title}`);
    await resumeDraft(page, job, video, entry);
  } else if (!entry) {
    console.log(`UPLOAD ${video.title}`);
    await uploadNew(page, job, video);
  } else {
    console.log(`SKIP_EXISTING ${video.title}`);
  }
  entry = await waitForPublishedEntry(page, job, video);
  if (entry?.draft) {
    console.log(`RESUME_DRAFT_AFTER_UPLOAD ${video.title}`);
    await resumeDraft(page, job, video, entry);
    entry = await waitForPublishedEntry(page, job, video);
  }
  if (!entry?.id || entry.draft) fail(`Publishing could not be verified for '${video.title}'.`);
  await verifyVideo(page, job, video, true);
}

async function withBrowser(job, callback, interactiveAuth = false) {
  const releaseLock = acquireLock(job.profileDir);
  const { chromium } = loadPlaywright();
  let context;
  try {
    context = await chromium.launchPersistentContext(job.profileDir, {
      executablePath: job.chromePath,
      headless: false,
      viewport: null,
      args: ['--disable-background-mode', '--no-first-run'],
    });
    const page = context.pages()[0] || await context.newPage();
    await ensureAuthentication(page, job, interactiveAuth);
    await callback(page);
  } finally {
    if (context) await context.close().catch(() => {});
    releaseLock();
  }
}

function printHelp() {
  console.log('Usage: node scripts/youtube-publisher.mjs <auth|validate|upload|verify> <job.json>');
}

async function main() {
  const [, , command, jobPath] = process.argv;
  if (!COMMANDS.has(command) || !jobPath) {
    printHelp();
    process.exitCode = 2;
    return;
  }
  const job = loadJob(jobPath, command === 'validate' || command === 'upload');
  if (command === 'validate') {
    console.log(`PASS Job valid | ${job.videos.length} video(s) | profile=${job.profileDir}`);
    return;
  }
  if (command === 'auth') {
    await withBrowser(job, async () => console.log(`PASS Authenticated channel ${job.channelId}`), true);
    return;
  }
  if (command === 'upload') {
    await withBrowser(job, async page => {
      for (const video of job.videos) await uploadVideo(page, job, video);
    });
    return;
  }
  await withBrowser(job, async page => {
    for (const video of job.videos) await verifyVideo(page, job, video, false);
  });
}

main().catch(error => {
  console.error(`FAIL ${error.message}`);
  process.exitCode = 1;
});
