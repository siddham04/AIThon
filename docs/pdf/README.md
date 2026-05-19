# Submission PDFs (ready to upload)

Generate or refresh these files from the repo root:

```powershell
pip install -r scripts/requirements-docs-pdf.txt
python scripts/build_submission_pdfs.py
```

| File | Use on portal |
|------|----------------|
| **`Helix-Implementation-Report.pdf`** | **Documentation or Implementation Report** (required) |
| **`Helix-Executive-Summary.pdf`** | **Custom attachment** (optional one-pager) |

Source Markdown (editable): **`../IMPLEMENTATION_REPORT.md`**

Presentation deck (separate script): `python scripts/build_pitch_deck.py` → `../Helix-AI-Thon-Pitch.pptx` in `docs/` (from `PRESENTATION.md`).
