import re
import base64
import requests

from datetime import datetime
from config import get_api_key

VISION_API_URL = 'https://vision.googleapis.com/v1/images:annotate'


def encode_image(image_path):
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def ocr_image(image_path):
    api_key = get_api_key()
    if not api_key:
        raise ValueError('Google Vision API key not set. Go to Scan > Settings to enter your key.')

    encoded = encode_image(image_path)

    payload = {
        'requests': [{
            'image': {'content': encoded},
            'features': [{'type': 'TEXT_DETECTION', 'maxResults': 1}]
        }]
    }

    resp = requests.post(f'{VISION_API_URL}?key={api_key}', json=payload, timeout=30)
    data = resp.json()

    if 'error' in data:
        raise ValueError(f"API Error: {data['error'].get('message', str(data['error']))}")

    text_annotations = data.get('responses', [{}])[0].get('textAnnotations', [])
    if not text_annotations:
        raise ValueError('No text found in the image.')

    full_text = text_annotations[0].get('description', '')
    return full_text


def parse_ocr_text(text):
    extracted = {}

    patterns = [
        r'(\d{2,3})\s*[/\\]\s*(\d{2,3})',
        r'(\d{2,3})\s+(\d{2,3})\s*mmHg',
        r'(\d{2,3})\s*[-\u2013]\s*(\d{2,3})',
        r'SYS[^0-9]*(\d{2,3})',
        r'sys[^0-9]*(\d{2,3})',
        r'Systolic[^0-9]*(\d{2,3})',
        r'DIA[^0-9]*(\d{2,3})',
        r'dia[^0-9]*(\d{2,3})',
        r'Diastolic[^0-9]*(\d{2,3})',
        r'HR[^0-9]*(\d{2,3})',
        r'hr[^0-9]*(\d{2,3})',
        r'Pulse[^0-9]*(\d{2,3})',
        r'pulse[^0-9]*(\d{2,3})',
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            groups = match.groups()
            pat_type = pattern.split('(')[0].rstrip('\\')

            if len(groups) == 2:
                a, b = int(groups[0]), int(groups[1])
                if 50 <= a <= 250 and 30 <= b <= 150:
                    if a > b:
                        extracted['sys'] = a
                        extracted['dia'] = b
                    else:
                        extracted['dia'] = a
                        extracted['sys'] = b
            elif len(groups) == 1:
                val = int(groups[0])
                if 'SYS' in pat_type.upper() or 'SYSTOLIC' in pat_type.upper():
                    if 50 <= val <= 250:
                        extracted['sys'] = val
                elif 'DIA' in pat_type.upper() or 'DIASTOLIC' in pat_type.upper():
                    if 30 <= val <= 150:
                        extracted['dia'] = val
                elif 'HR' in pat_type.upper() or 'PULSE' in pat_type.upper():
                    if 30 <= val <= 220:
                        extracted['hr'] = val

    bp_pair_pattern = r'(\d{2,3})\s*[/\\]\s*(\d{2,3})'
    bp_match = re.search(bp_pair_pattern, text)
    if bp_match:
        a, b = int(bp_match.group(1)), int(bp_match.group(2))
        if 50 <= a <= 250 and 30 <= b <= 150 and a > b:
            extracted['sys'] = a
            extracted['dia'] = b

    hr_pattern = r'(?:HR|hr|Hr|Pulse|pulse|Heart|heart)[^\d]*(\d{2,3})'
    hr_match = re.search(hr_pattern, text)
    if hr_match:
        val = int(hr_match.group(1))
        if 30 <= val <= 220:
            extracted['hr'] = val

    all_nums = re.findall(r'\b(\d{2,3})\b', text)
    bp_candidates = []
    hr_candidates = []
    for num_str in all_nums:
        val = int(num_str)
        if 50 <= val <= 250:
            bp_candidates.append(val)
        if 30 <= val <= 220:
            hr_candidates.append(val)

    if 'sys' not in extracted and len(bp_candidates) >= 2:
        bp_candidates.sort(reverse=True)
        extracted['sys'] = bp_candidates[0]
        extracted['dia'] = bp_candidates[1]

    if 'hr' not in extracted and hr_candidates:
        h = max(set(hr_candidates), key=hr_candidates.count)
        if h not in (extracted.get('sys'), extracted.get('dia')):
            extracted['hr'] = h

    return extracted


def capture_image_to_file():
    from kivy.utils import platform
    if platform == 'android':
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        Intent = autoclass('android.content.Intent')
        MediaStore = autoclass('android.provider.MediaStore')
        intent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)
        PythonActivity.mActivity.startActivityForResult(intent, 1001)
        return None
    else:
        return None
