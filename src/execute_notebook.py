"""Execute the retained notebook and record exactly which inputs it checked.

This reruns local analysis. Optional network refresh and model inference remain
off in the notebook, preserving the documented external-evidence snapshots.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / 'notebook/Hamza_Tebri_PGER_TFG_End_to_End.ipynb'


def sha256(path):
    data = path.read_bytes()
    if path.suffix.lower() in {'.csv', '.txt', '.json', '.ipynb', '.md', '.html', '.svg', '.py', '.ps1', '.toml'}:
        data = data.replace(b'\r\n', b'\n')
    return hashlib.sha256(data).hexdigest()


def main():
    os.environ['PGER_SKIP_BROWSER_OPEN'] = '1'
    started = datetime.now(timezone.utc).isoformat()
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    client = NotebookClient(notebook, timeout=600, kernel_name='python3',
                            resources={'metadata': {'path': str(ROOT)}})
    client.execute()
    nbformat.write(notebook, NOTEBOOK)
    inputs = sorted(p for folder in ('data', 'outputs/evaluation', 'figures', 'src', 'dashboard', '.streamlit')
                    for p in (ROOT / folder).rglob('*') if p.is_file()
                    and '__pycache__' not in p.parts and p.name != 'secrets.toml')
    report = {
        'started_utc': started,
        'completed_utc': datetime.now(timezone.utc).isoformat(),
        'runner_python': platform.python_version(),
        'kernel_python': notebook.metadata.language_info.version,
        'code_cells_executed': sum(c.cell_type == 'code' for c in notebook.cells),
        'notebook_sha256': sha256(NOTEBOOK),
        'digest_convention': 'SHA-256 with CRLF normalised to LF for text files, unchanged binary bytes',
        'external_evidence_mode': 'Retained snapshots, no new API or local-model requests',
        'local_model_inference_time': 'Not recorded in the original retained model result',
        'input_sha256': {p.relative_to(ROOT).as_posix(): sha256(p) for p in inputs},
    }
    path = ROOT / 'outputs/notebook_execution.json'
    path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(f"Executed {report['code_cells_executed']} code cells without errors.")
    print('Execution record: outputs/notebook_execution.json')


if __name__ == '__main__':
    main()
