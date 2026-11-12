"""Local synthetic fixtures only. Never production audiovisual acceptance evidence."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('producer', Path(__file__).with_name('produce.py'))
producer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(producer)


class ProducerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='course-skill-test-')
        self.root = Path(self.temp.name)
        self.input = self.root / 'input.json'
        self.data = json.loads((Path(__file__).parents[1] / 'assets/input.example.json').read_text())
        self.data['reference_material'] = []  # Synthetic test, no real person or brand.
        self.data['output'].update(width=160, height=90)
        shutil.copy2(Path(__file__).parents[1] / 'assets/script.example.txt', self.root / 'script.txt')
        self.save()

    def tearDown(self):
        self.temp.cleanup()

    def save(self):
        self.input.write_text(json.dumps(self.data), encoding='utf-8')

    def test_plan_idempotent_and_canonical(self):
        first = producer.plan(self.input)
        self.assertEqual(first, producer.plan(self.input))
        statefile = self.root / 'out-v1/manifest.json'
        bad = copy.deepcopy(first)
        bad['scenes'].reverse()
        producer.write_json(statefile, bad)
        with self.assertRaises(ValueError):
            producer.plan(self.input)

    def test_empty_duplicate_coverage_and_script_mismatch(self):
        for mode in ('empty', 'duplicate', 'dialogue'):
            data = copy.deepcopy(self.data)
            if mode == 'empty':
                data['scenes'][0]['coverage'] = []
            elif mode == 'duplicate':
                data['scenes'][1]['coverage'] = data['scenes'][0]['coverage']
            else:
                data['scenes'][0]['dialogue'] += ' Unexpected words.'
            self.input.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                producer.load(self.input)

    def test_parameters_not_hardcoded_to_male_or_landscape(self):
        self.data['output'].update(width=720, height=1280)
        self.data['visual_style'].update(presenter_reference='@Teacher',
            presenter_description='One woman, she/her.', clothing='Approved lab coat',
            logo_description='Blue triangle', audio_direction='One approved Spanish voice')
        text = producer.prompt(self.data, self.data['scenes'][0])
        self.assertIn('9:16', text)
        self.assertIn('One woman, she/her.', text)
        self.assertIn('Blue triangle', text)
        self.assertNotIn('sole male Character', text)
        self.assertNotIn('white geometric rings and red center', text)
        self.data['visual_style']['presenter_reference'] = 'none'
        self.assertIn('No person or face on screen', producer.prompt(self.data, self.data['scenes'][0]))

    def test_review_requires_real_hash_bound_evidence(self):
        output = self.root / 'out-v1'
        output.mkdir()
        media = output / 'selected.bin'
        media.write_bytes(b'synthetic-test-only')
        scene = {'id': 'S001', 'file': media.name, 'sha256': producer.digest(media),
                 'measured_duration': 1.0, 'status': 'accepted',
                 'review': {k: 'pass' for k in producer.REVIEW_KEYS}, 'review_evidence': 'review.json'}
        with self.assertRaises(ValueError):
            producer.validate_media({'scenes': [scene]}, output, False)
        evidence = {'sha256': scene['sha256'], 'in': 0.0, 'out': 1.0,
                    'reviewer': 'Synthetic unit fixture', 'method': 'Test, not AV approval',
                    'observations': 'Synthetic placeholder bytes, never course footage', 'review': scene['review']}
        producer.write_json(output / 'review.json', evidence)
        producer.validate_media({'scenes': [scene]}, output, False)
        scene['out'] = 0.5
        with self.assertRaises(ValueError):
            producer.validate_media({'scenes': [scene]}, output, False)

    def test_actual_ffmpeg_join_and_readiness_failure(self):
        ffmpeg = os.environ.get('COURSE_TEST_FFMPEG') or shutil.which('ffmpeg')
        ffprobe = os.environ.get('COURSE_TEST_FFPROBE') or shutil.which('ffprobe')
        if not ffmpeg or not ffprobe:
            self.skipTest('Set COURSE_TEST_FFMPEG and COURSE_TEST_FFPROBE for actual media test')
        self.data['output'].update(ffmpeg=ffmpeg, ffprobe=ffprobe)
        self.save()
        for index, color in enumerate(('red', 'blue')):
            media = self.root / f'{color}.mp4'
            producer.run([ffmpeg, '-v', 'error', '-n', '-f', 'lavfi', '-i',
                f'color=c={color}:s=160x90:r=24:d=1.25', '-f', 'lavfi', '-i',
                f'sine=frequency={400+index*200}:sample_rate=48000:duration=1.25',
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', str(media)])
            producer.ingest(self.input, f'S00{index+1}', media, 'local-synthetic-test')
        result = producer.render(self.input, True)
        self.assertTrue(result['draft'])
        self.assertEqual(result['full_decode'], 'pass')
        output = self.root / 'out-v1'
        timeline = json.loads((output / 'timeline.json').read_text())
        self.assertEqual([s['id'] for s in timeline], ['S001', 'S002'])
        self.assertEqual([s['frames'] for s in timeline], [30, 30])
        self.assertAlmostEqual(timeline[1]['start'], 1.25)
        info = producer.probe(ffprobe, output / result['file'])
        streams = {s['codec_type']: s for s in info['streams']}
        self.assertLess(abs(float(streams['video']['duration'])-float(streams['audio']['duration'])), 0.05)
        state = json.loads((output / 'manifest.json').read_text())
        for scene in state['scenes']:
            self.assertEqual(scene['sha256'], producer.digest(output / scene['file']))
        self.assertFalse(producer.verify(self.input)['upload_ready'])
        process = subprocess.run([os.sys.executable, str(Path(__file__).with_name('produce.py')),
            'verify', str(self.input)], capture_output=True, text=True)
        self.assertEqual(process.returncode, 2)
        with self.assertRaises(ValueError):
            producer.render(self.input, False)


if __name__ == '__main__':
    unittest.main(verbosity=2)
