import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
NOTEBOOK = ROOT / "notebook" / "Hamza_Tebri_PGER_TFG_End_to_End.ipynb"


def test_readme_visuals_and_services_are_complete():
    text = README.read_text(encoding="utf-8")
    for image in (
        "figures/repository_preview.png",
        "figures/figure_01_pger_evidence_flow.png",
        "figures/figure_02_data_funnel.png",
        "figures/figure_A1_dashboard_priority.png",
        "figures/figure_A2_dashboard_event_context.png",
    ):
        assert image in text
        assert (ROOT / image).exists()

    for service in (
        "Tavily Search API",
        "The Guardian Open Platform",
        "NewsAPI Everything",
        "GNews Search API",
        "NewsData.io Latest News API",
        "GDELT DOC 2.0 API",
        "LM Studio local API",
    ):
        assert service in text


def test_single_notebook_is_executed_without_error_outputs():
    notebooks = list(ROOT.rglob("*.ipynb"))
    assert notebooks == [NOTEBOOK]
    payload = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    code_cells = [cell for cell in payload["cells"] if cell["cell_type"] == "code"]
    assert code_cells
    assert all(cell.get("execution_count") is not None for cell in code_cells)
    assert not [
        output
        for cell in code_cells
        for output in cell.get("outputs", [])
        if output.get("output_type") == "error"
    ]


def test_private_and_submission_files_are_not_present():
    assert not (ROOT / ".env").exists()
    assert not list(ROOT.rglob("*.doc"))
    assert not list(ROOT.rglob("*.docx"))
    assert not (ROOT / "thesis").exists()
    assert not (
        ROOT
        / "data"
        / "raw"
        / "boe_procurement"
        / "licitaciones_contrataciones_BOE_2014_2024.csv"
    ).exists()


def test_public_entry_points_exist():
    for path in (
        ROOT / "dashboard" / "dashboard.py",
        ROOT / "src" / "download_boe_dataset.py",
        ROOT / "docs" / "SOURCE_REGISTER.md",
        ROOT / "CITATION.cff",
        ROOT / "LICENSE",
        ROOT / "THIRD_PARTY_NOTICES.md",
    ):
        assert path.exists()
