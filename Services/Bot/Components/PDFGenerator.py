"""
PDFGenerator.py

Genera un PDF médico formateado a partir del texto corregido por el LLM.
El texto puede contener secciones marcadas con *negrita* (estilo Telegram Markdown).
"""

import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    HRFlowable,
    Table,
    TableStyle,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ── Paleta de colores ────────────────────────────────────────────────────────
COLOR_HEADER_BG   = colors.HexColor("#1A3A5C")   # azul marino oscuro
COLOR_HEADER_TEXT = colors.HexColor("#FFFFFF")   # blanco
COLOR_ACCENT      = colors.HexColor("#2E86AB")   # azul medio (líneas, subtítulos)
COLOR_SECTION_BG  = colors.HexColor("#EBF4FA")   # azul muy claro (fondo secciones)
COLOR_BODY        = colors.HexColor("#1C1C1C")   # casi negro
COLOR_FOOTER      = colors.HexColor("#7F8C8D")   # gris


def _parse_sections(text: str) -> list[tuple[str, str]]:
    """
    Parsea el texto del LLM en lista de (título, contenido).
    Las secciones están marcadas con *Título:* al inicio de la línea.
    También acepta líneas sueltas sin sección como bloque sin-título.
    """
    sections: list[tuple[str, str]] = []
    current_title = ""
    current_lines: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # Detecta *Título:* o **Título:**
        if stripped.startswith("*") and ":" in stripped:
            # Cierra sección anterior
            if current_lines:
                sections.append((current_title, " ".join(current_lines)))
                current_lines = []
            # Extrae título eliminando asteriscos y ":"
            raw_title = stripped.split(":", 1)[0].replace("*", "").strip()
            current_title = raw_title
            # Contenido en la misma línea (luego del ":")
            rest = stripped.split(":", 1)[1].strip()
            if rest:
                current_lines.append(rest)
        else:
            current_lines.append(stripped)

    if current_lines:
        sections.append((current_title, " ".join(current_lines)))

    return sections


class PDFGenerator:
    """Genera informes médicos en PDF con diseño profesional."""

    def generate(
        self,
        corrected_text: str,
        raw_text: str,
        username: str,
        timestamp: datetime,
    ) -> bytes:
        """
        Genera el PDF y lo devuelve como bytes.

        Args:
            corrected_text: Informe corregido/formateado por el LLM.
            raw_text:        Transcripción cruda de Azure Speech AI.
            username:        Nombre/usuario del médico en Telegram.
            timestamp:       Fecha y hora del dictado.

        Returns:
            Contenido del PDF como bytes.
        """
        buffer = io.BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=2.2 * cm,
            rightMargin=2.2 * cm,
            topMargin=2.0 * cm,
            bottomMargin=2.5 * cm,
            title="Informe Médico",
            author="Medical ASR Bot",
        )

        styles = getSampleStyleSheet()
        story = []

        # ── Encabezado ────────────────────────────────────────────────────────
        header_data = [[
            Paragraph(
                "<font color='white' size='16'><b>INFORME MÉDICO</b></font>",
                ParagraphStyle("hdr", alignment=TA_CENTER),
            ),
        ]]
        header_table = Table(header_data, colWidths=[doc.width])
        header_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COLOR_HEADER_BG),
            ("TOPPADDING",    (0, 0), (-1, -1), 14),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
            ("LEFTPADDING",   (0, 0), (-1, -1), 16),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 16),
            ("ROUNDEDCORNERS", [6]),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 0.5 * cm))

        # ── Metadatos ─────────────────────────────────────────────────────────
        meta_style = ParagraphStyle(
            "meta",
            fontName="Helvetica",
            fontSize=9,
            textColor=COLOR_FOOTER,
            leading=14,
        )
        fecha_str = timestamp.strftime("%d/%m/%Y  %H:%M hs")
        story.append(Paragraph(f"<b>Médico:</b>  {username}", meta_style))
        story.append(Paragraph(f"<b>Fecha:</b>  {fecha_str}", meta_style))
        story.append(Spacer(1, 0.3 * cm))
        story.append(HRFlowable(width="100%", thickness=1.5, color=COLOR_ACCENT))
        story.append(Spacer(1, 0.5 * cm))

        # ── Secciones del informe ─────────────────────────────────────────────
        title_style = ParagraphStyle(
            "section_title",
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=COLOR_ACCENT,
            spaceBefore=4,
            spaceAfter=3,
        )
        body_style = ParagraphStyle(
            "body",
            fontName="Helvetica",
            fontSize=10,
            textColor=COLOR_BODY,
            leading=16,
            spaceAfter=4,
        )

        sections = _parse_sections(corrected_text)

        if sections:
            for title, content in sections:
                if title:
                    # Caja con fondo azul claro para cada sección
                    section_data = [[
                        Paragraph(title.upper(), title_style),
                        Paragraph(content, body_style),
                    ]]
                    section_table = Table(
                        section_data,
                        colWidths=[4.5 * cm, doc.width - 4.5 * cm],
                    )
                    section_table.setStyle(TableStyle([
                        ("BACKGROUND",    (0, 0), (-1, -1), COLOR_SECTION_BG),
                        ("TOPPADDING",    (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
                        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
                        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
                        ("LINEBELOW",     (0, 0), (-1, -1), 0.5, colors.HexColor("#C8DFF0")),
                    ]))
                    story.append(section_table)
                    story.append(Spacer(1, 0.25 * cm))
                else:
                    story.append(Paragraph(content, body_style))
                    story.append(Spacer(1, 0.2 * cm))
        else:
            # Fallback: texto plano sin secciones detectadas
            for line in corrected_text.splitlines():
                if line.strip():
                    story.append(Paragraph(line.strip(), body_style))
            story.append(Spacer(1, 0.3 * cm))

        # ── Separador ─────────────────────────────────────────────────────────
        story.append(Spacer(1, 0.4 * cm))
        story.append(HRFlowable(width="100%", thickness=0.8, color=COLOR_ACCENT, dash=(4, 3)))
        story.append(Spacer(1, 0.3 * cm))

        # ── Transcripción original ────────────────────────────────────────────
        raw_title_style = ParagraphStyle(
            "raw_title",
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=COLOR_FOOTER,
            spaceAfter=4,
        )
        raw_body_style = ParagraphStyle(
            "raw_body",
            fontName="Helvetica-Oblique",
            fontSize=8,
            textColor=COLOR_FOOTER,
            leading=13,
        )
        story.append(Paragraph("TRANSCRIPCIÓN ORIGINAL (ASR)", raw_title_style))
        story.append(Paragraph(raw_text or "—", raw_body_style))

        # ── Build ─────────────────────────────────────────────────────────────
        doc.build(story)
        buffer.seek(0)
        return buffer.read()
