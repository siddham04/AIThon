#!/usr/bin/env python3
"""
Build submission PDFs from docs/IMPLEMENTATION_REPORT.md plus a short executive summary.

Usage (repo root):
  pip install -r scripts/requirements-docs-pdf.txt
  python scripts/build_submission_pdfs.py

Outputs:
  docs/pdf/Helix-Implementation-Report.pdf   -- portal field "Documentation or Implementation Report"
  docs/pdf/Helix-Executive-Summary.pdf       -- optional "Custom Attachment" (1--2 pages)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_JUSTIFY
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        HRFlowable,
        ListFlowable,
        ListItem,
        PageBreak,
        Paragraph,
        Preformatted,
        SimpleDocTemplate,
        Spacer,
    )
except ImportError as e:
    print("Install: pip install -r scripts/requirements-docs-pdf.txt", file=sys.stderr)
    raise SystemExit(1) from e


def strip_inline_md(s: str) -> str:
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"`([^`]+)`", r"\1", s)
    return s


def safe_para(s: str, style) -> Paragraph:
    t = escape(strip_inline_md(s)).replace("\n", "<br/>")
    return Paragraph(t, style)


def parse_markdown_to_story(md: str, body_style, h2_style, h3_style, mono_style, bullet_style):
    story = []
    # Drop YAML-ish first line if only title - split by ## at line start
    parts = re.split(r"(?m)^## ", md)
    for i, part in enumerate(parts):
        part = part.strip()
        if not part:
            continue
        lines = part.split("\n")
        title_line = lines[0].strip()
        body_lines = lines[1:]

        if i == 0 and title_line.startswith("# "):
            # Preamble before first ## - title doc
            story.append(Paragraph(escape(strip_inline_md(title_line[2:])), h2_style))
            story.append(Spacer(1, 0.15 * inch))
            # rest of preamble until next ## already in body_lines... actually first part is "# Helix" block
            preamble = "\n".join(body_lines).strip()
            if preamble:
                for chunk in re.split(r"\n{2,}", preamble):
                    chunk = chunk.strip()
                    if chunk.startswith("---"):
                        continue
                    if chunk.startswith("|"):
                        continue  # skip tables if any
                    story.append(safe_para(chunk, body_style))
                    story.append(Spacer(1, 0.08 * inch))
            story.append(PageBreak())
            continue

        story.append(Paragraph(escape(strip_inline_md(title_line)), h2_style))
        story.append(Spacer(1, 0.12 * inch))

        in_code = False
        code_buf: list[str] = []
        bullet_group: list[str] = []

        def flush_bullets():
            nonlocal bullet_group
            if not bullet_group:
                return
            items = [
                ListItem(Paragraph(escape(strip_inline_md(b)), bullet_style), leftIndent=12)
                for b in bullet_group
            ]
            story.append(ListFlowable(items, bulletType="bullet", start="bulletchar"))
            story.append(Spacer(1, 0.1 * inch))
            bullet_group = []

        for raw in body_lines:
            line = raw.rstrip()
            if line.strip() == "---":
                flush_bullets()
                story.append(Spacer(1, 0.05 * inch))
                story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
                story.append(Spacer(1, 0.1 * inch))
                continue
            if line.strip().startswith("```"):
                if in_code:
                    flush_bullets()
                    txt = "\n".join(code_buf)
                    story.append(Preformatted(txt, mono_style))
                    story.append(Spacer(1, 0.1 * inch))
                    code_buf = []
                    in_code = False
                else:
                    flush_bullets()
                    in_code = True
                continue
            if in_code:
                code_buf.append(raw)
                continue
            if line.startswith("### "):
                flush_bullets()
                story.append(Paragraph(escape(strip_inline_md(line[4:])), h3_style))
                story.append(Spacer(1, 0.06 * inch))
                continue
            if line.strip().startswith("- ") or line.strip().startswith("* "):
                bullet_group.append(line.strip()[2:].strip())
                continue
            if not line.strip():
                flush_bullets()
                continue
            flush_bullets()
            if line.strip().startswith("|"):
                continue
            story.append(safe_para(line.strip(), body_style))
            story.append(Spacer(1, 0.06 * inch))

        flush_bullets()
        story.append(PageBreak())

    # Remove trailing empty page break
    while story and isinstance(story[-1], PageBreak):
        story.pop()
    return story


def build_implementation_report(md_path: Path, out_path: Path) -> None:
    md = md_path.read_text(encoding="utf-8")
    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "BodyJustify",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        alignment=TA_JUSTIFY,
        spaceAfter=6,
    )
    h2 = ParagraphStyle(
        "H2",
        parent=styles["Heading2"],
        fontSize=14,
        leading=18,
        spaceBefore=6,
        textColor=colors.HexColor("#0f172a"),
    )
    h3 = ParagraphStyle(
        "H3",
        parent=styles["Heading3"],
        fontSize=11,
        leading=14,
        spaceBefore=4,
        textColor=colors.HexColor("#334155"),
    )
    mono = ParagraphStyle(
        "Mono",
        parent=styles["Code"],
        fontSize=8,
        leading=10,
        fontName="Courier",
    )
    bullet = ParagraphStyle(
        "Bullet",
        parent=body,
        leftIndent=18,
        bulletIndent=8,
    )

    story = parse_markdown_to_story(md, body, h2, h3, mono, bullet)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=LETTER,
        rightMargin=inch * 0.75,
        leftMargin=inch * 0.75,
        topMargin=inch * 0.75,
        bottomMargin=inch * 0.75,
        title="Helix Implementation Report",
        author="Helix / AI-Thon",
    )

    def _footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        text = f"Page {doc_.page} | Helix -- AI-Thon Implementation Report"
        canvas.drawString(inch * 0.75, 0.5 * inch, text)
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)


def build_executive_summary(out_path: Path) -> None:
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "T",
        parent=styles["Title"],
        fontSize=18,
        spaceAfter=14,
        textColor=colors.HexColor("#0f172a"),
    )
    body = ParagraphStyle(
        "B",
        parent=styles["Normal"],
        fontSize=11,
        leading=15,
        alignment=TA_JUSTIFY,
        spaceAfter=10,
    )
    h = ParagraphStyle("H", parent=styles["Heading2"], fontSize=12, spaceBefore=8, spaceAfter=6)
    mono = ParagraphStyle("Mono", parent=styles["Code"], fontName="Courier", fontSize=9, leading=11)

    blocks = [
        (title, "Helix -- Executive summary"),
        (
            body,
            "Helix is an Intelligent SDLC Copilot that converts unstructured requirements into "
            "traceable stories, tasks, acceptance criteria, tests, ambiguity findings, risks, and "
            "effort estimates. Teams review and refine work in a React workspace, query a copilot "
            "over project context, and export to CSV/Markdown and optionally Jira or GitHub.",
        ),
        (
            h,
            "What was built (hackathon scope)",
        ),
        (
            body,
            "Requirement ingestion (text, file, URL, optional browser voice-to-text), preprocessing "
            "and clause-level traceability, multi-agent AI generation with live SSE progress, "
            "interactive dashboard (Kanban, summary, readiness, tests, ambiguity, export), "
            "test-case generation, ambiguity detection, conversational assistant, effort metrics, "
            "and governed export with human approval flags.",
        ),
        (
            h,
            "Technology",
        ),
        (
            body,
            "Frontend: React + Vite (helix-frontend). Backend: Python 3.11 + FastAPI + SQLAlchemy; "
            "PostgreSQL in Docker Compose; optional Redis, MongoDB, FAISS RAG; Azure OpenAI and/or "
            "Anthropic when keys are configured, with a mock path for offline demos.",
        ),
        (
            h,
            "How to verify quickly",
        ),
        (
            body,
            "Sign in with the seeded demo account (see README / docs/RUNBOOK.md). New Project: "
            "Load sample requirement, Ingest, then Generate artifacts -- no microphone required. "
            "Full stack: docker compose up --build from repo root, or deploy single-container demo "
            "per docs/DEMO_HOSTING.md.",
        ),
        (
            h,
            "Repository",
        ),
        (
            body,
            "https://github.com/siddham04/AIThon -- see docs/IMPLEMENTATION_REPORT.md for the full "
            "written report and docs/RUNBOOK.md for reviewer steps.",
        ),
    ]

    story = []
    for style, text in blocks:
        story.append(Paragraph(escape(text), style))

    story.append(Spacer(1, 0.2 * inch))
    story.append(
        Preformatted(
            "Logical flow (high level)\n"
            "  Browser (React) --> FastAPI (/api/*)\n"
            "       |-> PostgreSQL / SQLite\n"
            "       |-> optional Redis, MongoDB\n"
            "       |-> RAG (FAISS) + Azure / Anthropic / mock agents\n",
            mono,
        )
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=LETTER,
        rightMargin=inch * 0.85,
        leftMargin=inch * 0.85,
        topMargin=inch * 0.85,
        bottomMargin=inch * 0.85,
        title="Helix Executive Summary",
    )

    def _f(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(inch * 0.85, 0.55 * inch, "Helix | AI-Thon | Custom attachment")
        canvas.restoreState()

    doc.build(story, onFirstPage=_f, onLaterPages=_f)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", type=Path, default=root / "docs" / "IMPLEMENTATION_REPORT.md")
    ap.add_argument(
        "--out-report",
        type=Path,
        default=root / "docs" / "pdf" / "Helix-Implementation-Report.pdf",
    )
    ap.add_argument(
        "--out-summary",
        type=Path,
        default=root / "docs" / "pdf" / "Helix-Executive-Summary.pdf",
    )
    args = ap.parse_args()

    build_implementation_report(args.md, args.out_report)
    print(f"Wrote {args.out_report} ({args.out_report.stat().st_size // 1024} KB)")
    build_executive_summary(args.out_summary)
    print(f"Wrote {args.out_summary} ({args.out_summary.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
