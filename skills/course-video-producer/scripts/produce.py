"""Manifest-driven prompt preparation, ingestion, safe draft/final assembly and QA."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess

REVIEW_KEYS = ('dialogue', 'voice', 'identity', 'lip_sync', 'logo', 'visuals')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized(text):
    return ' '.join(text.split())


def assembly_digest(data, state):
    payload = {'output': data['output'], 'scenes': [
        {k: s.get(k) for k in ('id', 'coverage', 'dialogue', 'file', 'sha256', 'in', 'out', 'measured_duration')}
        for s in state['scenes']]}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def run(command):
    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if result.returncode:
        raise ValueError(result.stderr[-5000:] or result.stdout[-5000:])
    return result


def write_json(path, value):
    temp = path.with_suffix(path.suffix + '.tmp')
    if temp.exists():
        raise ValueError(f'Unsettled checkpoint exists: {temp}')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')
    temp.replace(path)


def load(path):
    path = path.resolve()
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    for key in ('topic', 'reference_material', 'final_script', 'code_demo_assets',
                'visual_style', 'output', 'generation', 'scenes'):
        if key not in data:
            raise ValueError(f'Missing input: {key}')
    base = path.parent
    output = (base / data['output']['directory']).resolve()
    if output == Path(output.anchor) or output == base:
        raise ValueError('Output must be a dedicated artifact subdirectory')
    script = (base / data['final_script']).resolve()
    scenes = data['scenes']
    ids = [s['id'] for s in scenes]
    if not ids or len(ids) != len(set(ids)) or any(not re.fullmatch(r'[A-Za-z0-9_-]+', i) for i in ids):
        raise ValueError('Empty, duplicate or unsafe scene IDs')
    coverage = [c for s in scenes for c in s['coverage']]
    if any(not s['coverage'] or any(not isinstance(c, str) or not c.strip() for c in s['coverage']) for s in scenes):
        raise ValueError('Every scene needs nonempty coverage IDs')
    if len(coverage) != len(set(coverage)):
        raise ValueError('Duplicated script/extension coverage')
    if normalized(' '.join(s['dialogue'] for s in scenes)) != normalized(script.read_text(encoding='utf-8')):
        raise ValueError('Scene dialogue does not exactly cover the declared script')
    for item in data['reference_material'] + data['code_demo_assets']:
        if not (base / item['path']).is_file():
            raise ValueError(f'Missing asset: {item["path"]}')
    return path, data, base, output, script


def prompt(data, scene):
    style = data['visual_style']
    duration = data['generation']['clip_seconds']
    beats = '\n'.join(f'{b["time"]}: {b["action"]}\nSpeak exactly: "{b["dialogue"]}"' for b in scene['beats'])
    if normalized(' '.join(b['dialogue'] for b in scene['beats'])) != normalized(scene['dialogue']):
        raise ValueError('Beat dialogue differs from scene dialogue')
    presenter = style['presenter_reference']
    identity = style.get('presenter_description', 'Preserve the supplied authorized presenter identity and natural appearance.')
    if str(presenter).lower() == 'none':
        identity = 'Presenter-free visual shot with the approved narration. No person or face on screen.'
    references = '\n'.join(f"{r.get('browser_reference', r['path'])}: {r['role']}" for r in data['reference_material'])
    width, height = int(data['output']['width']), int(data['output']['height'])
    divisor = math.gcd(width, height)
    return f'''Create one polished {duration}-second educational source shot, {width//divisor}:{height//divisor}, at the actually selected native resolution. Topic: {data['topic']['title']}. Scene {scene['id']}, {scene['objective']}. This is part of a continuous lesson, not an advertisement. The final teaching edit will follow the declared medium: {scene.get('medium', 'presenter and authored teaching visuals')}.

REFERENCE MAPPING
{references}
Presenter reference: {presenter}. {identity}
Location reference: {style.get('location_reference', 'Use the described set')}. The location controls the set; a portrait supplies identity, not its original background. These names are reference commands, never words to speak or display. Use the actual attached references, not an imagined match.

CHARACTER, STUDIO AND PERFORMANCE
{style['studio']}. {style['framing']}. Clothing, when a presenter is visible: {style.get('clothing', 'Preserve the approved reference clothing')}. Natural eye contact, breathing and blinking, restrained gestures when applicable. No repeated pointing, distorted hands, face drift or unrequested outfit change. Keep the approved camera and light. {scene['visual']}

EXACT LOGO, MANDATORY
Use the attached {style['logo_reference']} itself once. Placement: {style.get('logo_box', 'Top-left with safe margins, preserve source aspect ratio')}. Appearance: {style.get('logo_description', 'Preserve the supplied original asset geometry, colors and aspect ratio')}. No redraw, substitution, extra symbols, duplicate, 3D effect, animation, morph, rotation or glow. The logo stays fixed to the screen. Do not display its reference name or put another logo on clothing/background. If logo_reference is explicitly none, omit branding instead of inventing a logo.

VOICE AND AUDIO
{style['voice_direction']}. {style.get('audio_direction', 'Clear teaching delivery, natural pauses and one approved voice throughout; no music, effects, filler or extra greeting')}. Do not substitute an unapproved voice. For visible speech match mouth movement to the actual words and stop speaking naturally after the last word. Do not accelerate to force text into the clip. Voice prose is direction, not proof of a technical voice lock.

TIMED TEACHING BEATS
{beats}

COMPLETE EXACT DIALOGUE
"{scene['dialogue']}"
Speak this once, not once per section. Finish by the final beat deadline, then hold a neutral editing pose. Do not read directions aloud.

VISUAL AND FACTUAL GUARDRAILS
No invented code, terminal, datasets, statistics, UI, captions or additional readable text. Accurate teaching graphics and real code will be composed separately; leave the left teaching area unobstructed except for the mandatory logo. No added people, dramatic cuts, camera orbit or repeated introduction. Prioritize correct spoken content, recognizable identity, original voice, exact branding, intelligibility and continuity over spectacle.'''


def plan(path):
    path, data, base, output, script = load(path)
    output.mkdir(parents=True, exist_ok=True)
    state_path = output / 'manifest.json'
    if state_path.exists():
        state = json.loads(state_path.read_text())
        if state['input_sha256'] != digest(path) or state['script_sha256'] != digest(script):
            raise ValueError('Input revision changed; choose a new output version')
        if len(state['scenes']) != len(data['scenes']):
            raise ValueError('Saved scene count differs from the script plan')
        for original, saved in zip(data['scenes'], state['scenes']):
            if any(saved.get(k) != v for k, v in original.items()):
                raise ValueError('Saved scene order/content differs from the script plan')
        return state
    prompts = output / 'prompts'
    prompts.mkdir(exist_ok=True)
    for scene in data['scenes']:
        prompt_path = prompts / f'{scene["id"]}.txt'
        body = prompt(data, scene)
        if prompt_path.exists() and prompt_path.read_text(encoding='utf-8') != body:
            raise ValueError('Existing prompt differs; preserve and reconcile before planning')
    for scene in data['scenes']:
        prompt_path = prompts / f'{scene["id"]}.txt'
        if not prompt_path.exists():
            prompt_path.write_text(prompt(data, scene), encoding='utf-8')
    state = {'input_sha256': digest(path), 'script_sha256': digest(script),
             'topic': data['topic'], 'scenes': [{**s, 'status': 'planned'} for s in data['scenes']],
             'delivery': {'upload_ready': False}}
    write_json(state_path, state)
    return state


def probe(binary, path):
    return json.loads(run([binary, '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)]).stdout)


def ingest(path, scene_id, file, job_url, replace_pending=False):
    _, data, _, output, _ = load(path)
    state = plan(path)
    scene = next(s for s in state['scenes'] if s['id'] == scene_id)
    if scene.get('file'):
        if scene['sha256'] == digest(file):
            return state
        if not replace_pending or scene['status'] == 'accepted':
            raise ValueError('Existing scene preserved; use --replace-pending only for an unaccepted attempt')
    raw = output / 'raw'
    raw.mkdir(exist_ok=True)
    attempt = len(scene.get('previous_attempts', [])) + (2 if scene.get('file') else 1)
    dest = raw / f'{scene_id}-attempt{attempt}{file.suffix.lower()}'
    if dest.exists():
        raise ValueError('Unregistered file exists; inspect before ingestion')
    info = probe(data['output']['ffprobe'], file)
    if not any(s['codec_type'] == 'audio' for s in info['streams']):
        raise ValueError('Generated presenter clip lacks audio')
    videos = [s for s in info['streams'] if s['codec_type'] == 'video' and not s.get('disposition', {}).get('attached_pic')]
    if not videos or float(videos[0].get('duration', 0)) <= 0:
        raise ValueError('Source lacks a timed video stream')
    before = digest(file)
    shutil.copy2(file, dest)
    if digest(dest) != before or digest(file) != before:
        raise ValueError('Download changed while ingesting; inspect retained copy')
    if scene.get('file'):
        scene.setdefault('previous_attempts', []).append({k: scene.get(k) for k in
            ('file', 'sha256', 'job_url', 'status', 'measured_duration', 'in', 'out', 'review', 'review_evidence')})
    for key in ('in', 'out', 'review_evidence'):
        scene.pop(key, None)
    scene.update(file=str(dest.relative_to(output)), sha256=digest(dest), job_url=job_url,
                 measured_duration=float(info['format']['duration']), status='downloaded',
                 review={k: 'not_verified' for k in REVIEW_KEYS})
    write_json(output / 'manifest.json', state)
    return state


def validate_media(state, output, draft):
    used = set()
    for scene in state['scenes']:
        if scene['status'] == 'rejected' or not scene.get('file'):
            raise ValueError(f'Missing or rejected scene: {scene["id"]}')
        source = (output / scene['file']).resolve()
        if not source.is_relative_to(output) or digest(source) != scene['sha256']:
            raise ValueError('Source escaped output directory or changed after ingestion')
        a = float(scene.get('in', 0))
        b = float(scene.get('out', scene['measured_duration']))
        if not 0 <= a < b <= scene['measured_duration']:
            raise ValueError('Invalid trim range')
        for sha, start, end in used:
            if sha == scene['sha256'] and max(a, start) < min(b, end):
                raise ValueError('Overlapping duplicate footage / extension prefix')
        used.add((scene['sha256'], a, b))
        if not draft and (scene['status'] != 'accepted' or
                          any(scene.get('review', {}).get(k) != 'pass' for k in REVIEW_KEYS) or
                          not scene.get('review_evidence')):
            raise ValueError(f'Required review missing: {scene["id"]}')
        if not draft:
            evidence_path = (output / scene['review_evidence']).resolve()
            if not evidence_path.is_relative_to(output) or not evidence_path.is_file():
                raise ValueError(f'Scene review evidence file missing: {scene["id"]}')
            evidence = json.loads(evidence_path.read_text(encoding='utf-8-sig'))
            if (evidence.get('sha256') != scene['sha256'] or
                evidence.get('in') != a or evidence.get('out') != b or
                not all(evidence.get(k) for k in ('reviewer', 'method', 'observations')) or
                any(evidence.get('review', {}).get(k) != 'pass' for k in REVIEW_KEYS)):
                raise ValueError(f'Scene review evidence stale or incomplete: {scene["id"]}')


def render(path, draft):
    _, data, base, output, _ = load(path)
    state = plan(path)
    validate_media(state, output, draft)
    spec = data['output']
    ffmpeg = spec['ffmpeg']
    fps = float(spec['fps'])
    if not math.isfinite(fps) or fps <= 0:
        raise ValueError('Invalid output frame rate')
    requested = Path(spec['filename'])
    if requested.name != spec['filename']:
        raise ValueError('Use an unused plain output filename')
    name = requested.name
    if draft:
        version = 1
        while (output / f'{requested.stem}.draft-{version:03d}.mp4').exists():
            version += 1
        name = f'{requested.stem}.draft-{version:03d}.mp4'
    final = output / name
    if final.exists():
        raise ValueError('Existing final master preserved')
    parts = output / (final.stem + '-parts')
    parts.mkdir(exist_ok=False)
    cursor = 0.0
    timeline = []
    for scene in state['scenes']:
        start = float(scene.get('in', 0))
        requested_duration = float(scene.get('out', scene['measured_duration'])) - start
        frames = max(1, round(requested_duration * fps))
        duration = frames / fps
        samples = round(duration * 48000)
        part = parts / f'{scene["id"]}.mkv'
        filters = [f'scale={spec["width"]}:{spec["height"]}:force_original_aspect_ratio=decrease',
                   f'pad={spec["width"]}:{spec["height"]}:(ow-iw)/2:(oh-ih)/2:color=0x09111c',
                   'setsar=1', f'fps={spec["fps"]}',
                   'tpad=stop_mode=clone:stop_duration=0.1', f'trim=end_frame={frames}', 'setpts=PTS-STARTPTS']
        run([ffmpeg, '-v', 'error', '-n', '-ss', str(start), '-i', str(output / scene['file']),
             '-t', str(duration), '-map', '0:v:0', '-map', '0:a:0', '-vf', ','.join(filters),
             '-af', f'aresample=48000,apad,atrim=end_sample={samples},asetpts=PTS-STARTPTS', '-c:v', 'libx264',
             '-preset', 'fast', '-crf', '18', '-threads', '4', '-pix_fmt', 'yuv420p',
             '-c:a', 'pcm_s16le', '-ar', '48000', '-ac', '2', str(part)])
        part_info = json.loads(run([spec['ffprobe'], '-v', 'error', '-count_frames',
            '-show_streams', '-show_format', '-of', 'json', str(part)]).stdout)
        encoded_frames = int(next(s for s in part_info['streams'] if s['codec_type'] == 'video')['nb_read_frames'])
        if encoded_frames != frames:
            raise ValueError('Encoded part frame count differs from planned frame boundary')
        duration = encoded_frames / fps
        timeline.append({'id': scene['id'], 'start': cursor, 'duration': duration,
                         'frames': encoded_frames, 'source_sha256': scene['sha256'],
                         'part_sha256': digest(part), 'in': start,
                         'requested_duration': requested_duration,
                         'dialogue': scene['dialogue'], 'objective': scene['objective']})
        cursor += duration
    listing = parts / 'concat.txt'
    listing.write_text(''.join(f"file '{s['id']}.mkv'\n" for s in state['scenes']), encoding='utf-8')
    run([ffmpeg, '-v', 'error', '-n', '-f', 'concat', '-safe', '1', '-i', str(listing),
         '-map', '0:v:0', '-map', '0:a:0', '-c:v', 'copy', '-c:a', 'aac',
         '-b:a', '192k', '-movflags', '+faststart', str(final)])
    decoded = run([ffmpeg, '-v', 'error', '-i', str(final), '-f', 'null', '-'])
    if decoded.stderr.strip():
        raise ValueError('Decoder reported errors: ' + decoded.stderr)
    info = probe(spec['ffprobe'], final)
    if abs(float(info['format']['duration']) - cursor) > 0.1:
        raise ValueError('Timeline duration mismatch')
    write_json(output / 'timeline.json', timeline)
    state['delivery'] = {'file': final.name, 'sha256': digest(final), 'draft': draft,
                         'assembly_sha256': assembly_digest(data, state),
                         'full_decode': 'pass', 'duration': float(info['format']['duration']),
                         'upload_ready': False, 'full_playback': 'not_verified'}
    write_json(output / 'manifest.json', state)
    return state['delivery']


def verify(path):
    _, data, _, output, _ = load(path)
    state = plan(path)
    problems = []
    try:
        validate_media(state, output, False)
    except ValueError as error:
        problems.append(str(error))
    delivery = state['delivery']
    final = output / delivery.get('file', 'missing.mp4')
    if not final.is_file() or digest(final) != delivery.get('sha256'):
        problems.append('Missing or modified final master')
    if delivery.get('draft') or delivery.get('full_playback') != 'pass' or not delivery.get('review_evidence'):
        problems.append('Final audiovisual review has not passed')
    if delivery.get('assembly_sha256') != assembly_digest(data, state):
        problems.append('Final master does not match the current assembly specification')
    if delivery.get('reviewed_sha256') != delivery.get('sha256'):
        problems.append('Final review does not identify the current master hash')
    for check in ('dialogue', 'voice', 'identity', 'lip_sync', 'logo', 'visuals', 'captions',
                  'chapters', 'thumbnail', 'audio_mastering', 'teaching_coverage'):
        if delivery.get('review', {}).get(check) != 'pass':
            problems.append('Final review missing: ' + check)
    evidence = delivery.get('review_evidence', '')
    if not evidence or not (output / evidence).is_file():
        problems.append('Final review evidence file missing')
    for name in ('title.txt', 'description.txt', 'thumbnail.png', 'captions.srt', 'chapters.txt', 'upload-metadata.json'):
        item = output / name
        if not item.is_file() or item.stat().st_size == 0:
            problems.append('Missing delivery asset: ' + name)
    try:
        thumbnail = probe(data['output']['ffprobe'], output / 'thumbnail.png')
        if not any(s['codec_type'] == 'video' for s in thumbnail['streams']):
            raise ValueError('Thumbnail is not an image')
        if not (output / 'thumbnail.png').read_bytes().startswith(b'\x89PNG\r\n\x1a\n'):
            raise ValueError('Thumbnail must be a genuine PNG image, not renamed video')
        captions = (output / 'captions.srt').read_text(encoding='utf-8-sig').strip()
        previous_end = 0.0
        caption_text = []
        for number, block in enumerate(re.split(r'\n\s*\n', captions), 1):
            lines = block.strip().splitlines()
            if len(lines) < 3 or lines[0] != str(number):
                raise ValueError('Malformed or nonsequential caption cue')
            match = re.fullmatch(r'(\d{2}):([0-5]\d):([0-5]\d),(\d{3}) --> (\d{2}):([0-5]\d):([0-5]\d),(\d{3})', lines[1])
            if not match:
                raise ValueError('Invalid caption timestamp')
            h, m, s, ms, eh, em, es, ems = map(int, match.groups())
            start, end = h*3600+m*60+s+ms/1000, eh*3600+em*60+es+ems/1000
            if not previous_end <= start < end <= delivery.get('duration', 0) + 0.05:
                raise ValueError('Caption cues overlap, reverse, or exceed the master')
            previous_end = end
            caption_text.extend(lines[2:])
        if normalized(' '.join(caption_text)) != normalized(' '.join(s['dialogue'] for s in state['scenes'])):
            raise ValueError('Caption text does not exactly cover the reviewed dialogue')
        chapters = (output / 'chapters.txt').read_text(encoding='utf-8').strip().splitlines()
        times = []
        for chapter in chapters:
            match = re.fullmatch(r'(\d{1,2}:\d{2}(?::\d{2})?)\s+\S.*', chapter)
            if not match:
                raise ValueError('Malformed chapter line')
            parts = [int(p) for p in match[1].split(':')]
            if any(p > 59 for p in parts[1:]):
                raise ValueError('Invalid chapter timestamp')
            seconds = sum(p * 60**i for i, p in enumerate(reversed(parts)))
            times.append(seconds)
        if not times or times[0] != 0 or any(b <= a for a, b in zip(times, times[1:])) or times[-1] >= delivery.get('duration', 0):
            raise ValueError('Chapter times do not fit the master')
        metadata = json.loads((output / 'upload-metadata.json').read_text(encoding='utf-8'))
        if metadata.get('video_sha256') != delivery.get('sha256') or not isinstance(metadata.get('tags'), list):
            raise ValueError('Upload metadata does not match current master or lacks tags')
        if metadata.get('title') != (output / 'title.txt').read_text(encoding='utf-8').strip():
            raise ValueError('Title differs from upload metadata')
        if metadata.get('description') != (output / 'description.txt').read_text(encoding='utf-8').strip():
            raise ValueError('Description differs from upload metadata')
        for key in ('channel_url', 'playlist_id', 'module_order', 'visibility'):
            if key not in metadata:
                raise ValueError('Publishing destination/order missing: ' + key)
    except (ValueError, OSError, KeyError) as error:
        problems.append('Delivery package invalid: ' + str(error))
    return {'upload_ready': not problems, 'problems': problems}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('plan', 'ingest', 'render', 'verify'))
    parser.add_argument('input', type=Path)
    parser.add_argument('scene', nargs='?')
    parser.add_argument('file', nargs='?', type=Path)
    parser.add_argument('--job-url', default='')
    parser.add_argument('--draft', action='store_true')
    parser.add_argument('--replace-pending', action='store_true')
    args = parser.parse_args()
    try:
        if args.command == 'plan':
            result = plan(args.input)
        elif args.command == 'ingest':
            result = ingest(args.input, args.scene, args.file, args.job_url, args.replace_pending)
        elif args.command == 'render':
            result = render(args.input, args.draft)
        else:
            result = verify(args.input)
        print(json.dumps(result, indent=2))
        if args.command == 'verify' and not result['upload_ready']:
            parser.exit(2)
    except (ValueError, KeyError, StopIteration, OSError) as error:
        parser.exit(2, f'Production check failed: {error}\n')


if __name__ == '__main__':
    main()
