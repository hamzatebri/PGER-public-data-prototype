import importlib.util
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_invalid_development_label_stops_before_any_model_request(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location('evaluation_under_test', ROOT / 'src/evaluate_local_llm.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    labels = tmp_path / 'labels.csv'
    pd.DataFrame({'label_event_family': ['unsupported']}).to_csv(labels, index=False)
    monkeypatch.setattr(module, 'LABELS', labels)
    def unexpected_request(*args, **kwargs):
        pytest.fail('Invalid labels must be rejected before calling the model')
    monkeypatch.setattr(module, 'classify', unexpected_request)
    with pytest.raises(ValueError, match='unsupported event family'):
        module.main()


def test_retained_model_result_is_development_agreement():
    import json
    result = json.loads((ROOT / 'outputs/evaluation/local_llm_evaluation.json').read_text())
    rows = pd.read_csv(ROOT / 'outputs/evaluation/local_llm_evaluation.csv')
    labels = pd.read_csv(ROOT / 'data/evaluation/researcher_event_labels.csv').fillna('')
    pd.testing.assert_frame_equal(rows[labels.columns].fillna(''), labels)
    assert result['exercise_type'] == 'development_sample'
    assert result['sample_size'] == len(rows)
    assert result['agreement_count'] == int((rows.label_event_family == rows.local_llm_prediction).sum())


def test_dashboard_snapshot_uses_recorded_dates_and_explicit_classes():
    text = (ROOT / 'dashboard/dashboard.py').read_text(encoding='utf-8')
    assert 'st_mtime' not in text
    assert "isin(valid_families)" in text
    assert 'Classification unavailable' in text
    assert 'Section 3.7' not in text


def test_execution_record_matches_notebook_and_available_inputs():
    import hashlib
    import json
    def digest(path):
        data = path.read_bytes()
        if path.suffix.lower() in {'.csv', '.txt', '.json', '.ipynb', '.md', '.html', '.svg', '.py', '.ps1', '.toml'}:
            data = data.replace(b'\r\n', b'\n')
        return hashlib.sha256(data).hexdigest()
    record = json.loads((ROOT / 'outputs/notebook_execution.json').read_text())
    assert record['code_cells_executed'] == 21
    assert digest(ROOT / 'notebook/Hamza_Tebri_PGER_TFG_End_to_End.ipynb') == record['notebook_sha256']
    for relative, expected in record['input_sha256'].items():
        path = ROOT / relative
        if relative == 'data/raw/boe_procurement/licitaciones_contrataciones_BOE_2014_2024.csv' and not path.exists():
            continue
        assert path.exists(), relative
        assert digest(path) == expected, relative
