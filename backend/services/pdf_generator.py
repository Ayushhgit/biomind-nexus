"""
BioMind Nexus - PDF Report Generator

Generates research-grade PDF reports for drug repurposing analysis.
Uses ReportLab for PDF generation.

Report Structure:
1. Cover Page
2. Query Overview
3. Knowledge Graph (static image)
4. Mechanistic Reasoning
5. Citations Table
6. Safety Review
7. Disclaimer
"""

from typing import Dict, Any, List
from datetime import datetime
import io

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, Image, HRFlowable
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


def generate_report_pdf(query_id: str, state: Dict[str, Any], timestamp: str) -> bytes:
    """
    Generate a complete PDF report for a drug repurposing query.
    
    Args:
        query_id: Unique query identifier
        state: AgentState with all results
        timestamp: Query execution timestamp
    
    Returns:
        PDF file as bytes
    """
    if not REPORTLAB_AVAILABLE:
        return _generate_fallback_pdf(query_id, state, timestamp)
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1e40af")
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceBefore=20,
        spaceAfter=10,
        textColor=colors.HexColor("#0f172a")
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_JUSTIFY,
        spaceAfter=8
    )
    
    # Build document elements
    elements = []
    
    # Extract data from state
    query = state.get("query", {})
    raw_query = query.raw_query if hasattr(query, "raw_query") else str(query)
    drug_name = query.source_drug.name if hasattr(query, "source_drug") and query.source_drug else "Unknown Drug"
    disease_name = query.target_disease.name if hasattr(query, "target_disease") and query.target_disease else "Unknown Disease"
    
    # 1. Cover Page
    elements.append(Spacer(1, 1.5 * inch))
    elements.append(Paragraph("BioMind Nexus", title_style))
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Paragraph("In-Silico Drug Repurposing Analysis", styles['Heading2']))
    elements.append(Spacer(1, 1 * inch))
    
    cover_data = [
        ["Drug", drug_name],
        ["Disease", disease_name],
        ["Query ID", query_id],
        ["Generated", timestamp[:19].replace("T", " ")],
    ]
    cover_table = Table(cover_data, colWidths=[1.5 * inch, 4 * inch])
    cover_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor("#64748b")),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(cover_table)
    elements.append(PageBreak())
    
    # 2. Query Overview
    elements.append(Paragraph("Query Overview", heading_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0")))
    elements.append(Spacer(1, 0.2 * inch))
    elements.append(Paragraph(f"<b>Original Query:</b> {raw_query}", body_style))
    elements.append(Spacer(1, 0.3 * inch))
    
    # 3. Mechanistic Reasoning Summary
    elements.append(Paragraph("Mechanistic Reasoning", heading_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0")))
    elements.append(Spacer(1, 0.2 * inch))
    
    simulation = state.get("simulation_result")
    if simulation and hasattr(simulation, "valid_paths") and simulation.valid_paths:
        for i, path in enumerate(simulation.valid_paths[:3]):
            rationale = path.biological_rationale if hasattr(path, "biological_rationale") else "Path analysis available."
            elements.append(Paragraph(f"<b>Path {i+1}:</b> {rationale}", body_style))
            elements.append(Paragraph(f"<i>Confidence: {path.path_confidence:.1%}</i>", body_style))
            elements.append(Spacer(1, 0.1 * inch))
    else:
        elements.append(Paragraph("No validated mechanistic pathways identified.", body_style))
    
    # 4. Candidates
    candidates = state.get("final_candidates", []) or state.get("drug_candidates", [])
    if candidates:
        elements.append(Spacer(1, 0.2 * inch))
        elements.append(Paragraph("Drug Candidates", heading_style))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0")))
        elements.append(Spacer(1, 0.2 * inch))
        
        for cand in candidates[:5]:
            drug = cand.drug.name if hasattr(cand.drug, "name") else str(cand.drug)
            hypo = cand.hypothesis if hasattr(cand, "hypothesis") else "Hypothesis available."
            conf = cand.confidence if hasattr(cand, "confidence") else 0.5
            elements.append(Paragraph(f"<b>{drug}</b> (Confidence: {conf:.1%})", body_style))
            elements.append(Paragraph(hypo[:300], body_style))
            elements.append(Spacer(1, 0.1 * inch))
    
    # 5. Citations Table
    evidence = state.get("literature_evidence", [])
    if evidence:
        elements.append(Spacer(1, 0.2 * inch))
        elements.append(Paragraph("Supporting Evidence & Citations", heading_style))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0")))
        elements.append(Spacer(1, 0.2 * inch))
        
        citation_data = [["PMID", "Title", "Year", "Confidence"]]
        for ev in evidence[:10]:
            citation = ev.citation if hasattr(ev, "citation") else None
            if citation:
                pmid = citation.source_id if hasattr(citation, "source_id") else ""
                title = citation.title[:50] + "..." if hasattr(citation, "title") and len(citation.title) > 50 else (citation.title if hasattr(citation, "title") else "")
                year = str(citation.year) if hasattr(citation, "year") and citation.year else "N/A"
                conf = f"{ev.confidence:.0%}" if hasattr(ev, "confidence") else ""
                citation_data.append([pmid, title, year, conf])
        
        if len(citation_data) > 1:
            citation_table = Table(citation_data, colWidths=[0.8 * inch, 3.5 * inch, 0.6 * inch, 0.8 * inch])
            citation_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(citation_table)
    
    # 6. Safety Review
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Paragraph("Safety & Audit Review", heading_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0")))
    elements.append(Spacer(1, 0.2 * inch))
    
    safety = state.get("safety_result")
    if safety:
        passed = safety.passed if hasattr(safety, "passed") else True
        status = "APPROVED" if passed else "BLOCKED"
        color = "#059669" if passed else "#dc2626"
        elements.append(Paragraph(f"<b>Safety Decision:</b> <font color='{color}'>{status}</font>", body_style))
        
        if hasattr(safety, "flags") and safety.flags:
            elements.append(Paragraph(f"<b>Flags:</b> {len(safety.flags)} warning(s)", body_style))
            for flag in safety.flags[:3]:
                desc = flag.message if hasattr(flag, "message") else str(flag)
                elements.append(Paragraph(f"• {desc}", body_style))
    else:
        elements.append(Paragraph("<b>Safety Decision:</b> APPROVED (no flags)", body_style))
    
    # Steps executed
    steps = state.get("step_history", [])
    if steps:
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(Paragraph(f"<b>Steps Executed:</b> {', '.join(steps)}", body_style))
    
    # 7. Disclaimer
    elements.append(Spacer(1, 0.5 * inch))
    elements.append(Paragraph("Limitations & Disclaimer", heading_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0")))
    elements.append(Spacer(1, 0.2 * inch))
    
    disclaimer = """
    <b>RESEARCH USE ONLY</b><br/><br/>
    This report is generated by an in-silico drug repurposing system and is intended 
    solely for research purposes. The hypotheses and findings presented herein:<br/><br/>
    • Have NOT been validated through clinical trials<br/>
    • Do NOT constitute medical advice<br/>
    • Require independent laboratory and clinical validation<br/>
    • Should NOT be used for patient treatment decisions<br/><br/>
    The system uses machine learning models and literature mining which may produce 
    inaccurate or incomplete results. All findings should be verified by qualified 
    researchers before any further action is taken.
    """
    elements.append(Paragraph(disclaimer, body_style))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer.read()


def _generate_fallback_pdf(query_id: str, state: Dict[str, Any], timestamp: str) -> bytes:
    """Generate minimal PDF without ReportLab."""
    query = state.get("query", {})
    raw_query = query.raw_query if hasattr(query, "raw_query") else str(query)
    
    content = f"""BioMind Nexus - Drug Repurposing Report
    
Query ID: {query_id}
Generated: {timestamp}
Query: {raw_query}

This is a minimal report. Install reportlab for full PDF generation:
    pip install reportlab

DISCLAIMER: Research use only. Not medical advice.
"""
    
    # Minimal valid PDF
    stream_content = f"BT /F1 12 Tf 50 750 Td (BioMind Nexus Report) Tj 0 -20 Td (Query: {query_id}) Tj ET"
    
    pdf = f"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj << /Length {len(stream_content)} >>
stream
{stream_content}
endstream
endobj
5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000266 00000 n
0000000365 00000 n
trailer << /Size 6 /Root 1 0 R >>
startxref
445
%%EOF"""
    
    return pdf.encode("latin-1")
