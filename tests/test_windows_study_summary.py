import json
import pytest
from tools.summarize_windows_study import summarize


def test_empty_capture_is_not_reported_as_a_successful_experiment(tmp_path):
    with pytest.raises(ValueError, match='No actual scan files'):
        summarize(tmp_path)


@pytest.mark.parametrize('administrator', [True, None])
def test_standard_user_condition_requires_observed_unelevated_token(tmp_path, administrator):
    write_case(tmp_path, administrator)
    with pytest.raises(ValueError, match='Privilege mismatch'):
        summarize(tmp_path)


def write_case(root, administrator):
    case = root / 'standard'
    repeat = case / 'repeat-1'
    repeat.mkdir(parents=True)
    (case / 'case.json').write_text(json.dumps({'case_id': 'full-standard', 'review_status': 'PENDING_INDEPENDENT_REVIEW'}))
    (repeat / 'reference-before.json').write_text(json.dumps({'is_administrator': administrator}))
    summary = dict(passed_count=2, failed_count=1, error_count=2, omitted_count=0,
                   selected_coverage=60, baseline_coverage=60, lower_bound=40,
                   upper_bound=80, decision='UNRESOLVED')
    (repeat / 'scan.json').write_text(json.dumps({'evidence_summary': summary}))


def test_real_record_counts_and_pending_review_are_preserved(tmp_path):
    write_case(tmp_path, False)
    rows = summarize(tmp_path)
    assert len(rows) == 1
    assert rows[0]['error_count'] == 2
    assert rows[0]['independent_review'] == 'PENDING_INDEPENDENT_REVIEW'
