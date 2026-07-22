"""
Import blood pressure readings from a markdown file into the database.
Usage: python import_data.py [path_to_markdown_file]
"""

import sys
import os
from datetime import datetime
from database import Database


def parse_markdown_table(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    readings = []
    header_found = False

    for line in lines:
        line = line.strip()
        if line.startswith('|TIME|') or line.startswith('|Time|'):
            header_found = True
            continue
        if not header_found:
            continue
        if line.startswith('|-') or line == '' or line.startswith('|After '):
            continue
        if line.startswith('|') and '<br />' in line:
            continue
        if not line.startswith('|') or not line.endswith('|'):
            continue

        parts = [p.strip() for p in line.split('|')]
        parts = [p for p in parts if p]

        if len(parts) < 4:
            continue

        time_str = parts[0].strip()
        sys_str = parts[1].strip()
        dia_str = parts[2].strip()
        hr_str = parts[3].strip()

        try:
            sys_val = int(sys_str)
            dia_val = int(dia_str)
            hr_val = int(hr_str)
        except ValueError:
            continue

        time_formats = [
            '%I:%M %p %m/%d/%Y',
            '%I:%M%p %m/%d/%Y',
            '%I:%M %p %m/%d/%y',
            '%m/%d/%Y %I:%M %p',
            '%m/%d/%Y %H:%M',
        ]

        parsed_ts = None
        for fmt in time_formats:
            try:
                parsed_ts = datetime.strptime(time_str, fmt).strftime('%Y-%m-%d %H:%M:%S')
                break
            except ValueError:
                continue

        if parsed_ts is None:
            print(f'Skipping unparseable date: {time_str}')
            continue

        readings.append((parsed_ts, sys_val, dia_val, hr_val))

    return readings


def main():
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    else:
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'readings.md')

    if not os.path.exists(filepath):
        print(f'File not found: {filepath}')
        return

    readings = parse_markdown_table(filepath)
    print(f'Found {len(readings)} readings in markdown file')

    db = Database()

    existing = db.get_all_readings()
    if existing:
        print(f'Database already has {len(existing)} readings.')
        answer = input('Clear existing data and re-import? (y/N): ')
        if answer.lower() == 'y':
            db.delete_all()
            print('Existing data cleared.')
        else:
            print('Import cancelled.')
            db.close()
            return

    count = 0
    for ts, sys_val, dia_val, hr_val in readings:
        db.add_reading(ts, sys_val, dia_val, hr_val)
        count += 1

    db.close()
    print(f'Successfully imported {count} readings!')


if __name__ == '__main__':
    main()
