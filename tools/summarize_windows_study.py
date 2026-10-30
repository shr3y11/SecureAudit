"""Summarize actual capture files; never infer ground-truth accuracy."""
import argparse
import csv
import json
from pathlib import Path


def summarize(root):
    rows = []
    for case_file in sorted(root.glob('*/case.json')):
        case = json.loads(case_file.read_text(encoding='utf-8'))
        for scan_file in sorted(case_file.parent.glob('repeat-*/scan.json')):
            scan = json.loads(scan_file.read_text(encoding='utf-8'))
            reference = json.loads((scan_file.parent / 'reference-before.json').read_text(encoding='utf-8'))
            summary = scan['evidence_summary']
            rows.append({'case': case['case_id'], 'repeat': scan_file.parent.name,
                         'administrator': reference.get('is_administrator'),
                         **{key: summary[key] for key in ('passed_count', 'failed_count', 'error_count',
                            'omitted_count', 'selected_coverage', 'baseline_coverage',
                            'lower_bound', 'upper_bound', 'decision')},
                         'independent_review': case['review_status']})
    if not rows:
        raise ValueError('No actual scan files found; refusing to produce results.')
    for row in rows:
        expected = row['case'] != 'full-standard'
        if row['administrator'] is not expected:
            raise ValueError(f"Privilege mismatch or missing metadata for {row['case']}")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    rows = summarize(args.input)
    args.output.mkdir(parents=True, exist_ok=False)
    with (args.output / 'observations.csv').open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    (args.output / 'observations.json').write_text(json.dumps(rows, indent=2) + '\n', encoding='utf-8')
    report = ['# Hosted Windows pilot observations', '',
              'Actual scanner captures on a disposable Windows Server runner. Repetitions are not independent endpoints.',
              'Native references share Windows APIs with collectors. Independent review remains pending.',
              'The aggregate threshold is illustrative. No accuracy, usability, or organizational compliance claim follows.', '',
              '| Case | Repeat | Admin | P | F | E | O | Baseline coverage | Bounds |',
              '| --- | --- | --- | --- | --- | --- | --- | --- | --- |']
    for row in rows:
        report.append(f"| {row['case']} | {row['repeat']} | {row['administrator']} | {row['passed_count']} | {row['failed_count']} | {row['error_count']} | {row['omitted_count']} | {row['baseline_coverage']}% | {row['lower_bound']}-{row['upper_bound']}% |")
    (args.output / 'observations.md').write_text('\n'.join(report) + '\n', encoding='utf-8')
    print('\n'.join(report))


if __name__ == '__main__':
    main()
