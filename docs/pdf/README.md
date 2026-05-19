# Submission PDFs (ready to upload)

Generate or refresh:

```powershell
pip install -r scripts/requirements-docs-pdf.txt
python scripts/build_submission_pdfs.py
```

| File | Use on portal |
|------|----------------|
| **`Helix-Implementation-Report.pdf`** | **Documentation or Implementation Report** (required) |
| **`Helix-Implementation-Report-PORTAL.pdf`** | **Same PDF**, different name — use if the site rejected or cached a bad upload |
| **`Helix-Executive-Summary.pdf`** | **Custom attachment** (optional) |

Source Markdown: **`../IMPLEMENTATION_REPORT.md`**

The implementation report PDF includes a **cover page** and PDF **metadata** (title, author, subject) for compatibility with upload validators.

Presentation deck: `python scripts/build_pitch_deck.py` → `../Helix-AI-Thon-Pitch.pptx`
