from io import BytesIO
from pathlib import Path


def _register_font():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    font_candidates = [
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for font_path in font_candidates:
        if font_path.exists():
            pdfmetrics.registerFont(TTFont("TripPlannerFont", str(font_path)))
            return "TripPlannerFont"
    return "Helvetica"


def generate_trip_pdf(trip, weather=None):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = BytesIO()
    font_name = _register_font()
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="TripTitle",
            fontName=font_name,
            fontSize=22,
            leading=28,
            spaceAfter=16,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TripText",
            fontName=font_name,
            fontSize=11,
            leading=16,
        )
    )

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    story = [
        Paragraph(f"Маршрут: {trip.title}", styles["TripTitle"]),
        Paragraph(f"Направление: {trip.destination}", styles["TripText"]),
        Paragraph(
            f"Даты: {trip.start_date.strftime('%d.%m.%Y')} - "
            f"{trip.end_date.strftime('%d.%m.%Y')} ({trip.duration_days} дн.)",
            styles["TripText"],
        ),
        Paragraph(f"Бюджет: {trip.budget} руб.", styles["TripText"]),
        Spacer(1, 12),
    ]

    if trip.description:
        story.append(Paragraph("Описание", styles["TripText"]))
        story.append(Paragraph(trip.description, styles["TripText"]))
        story.append(Spacer(1, 12))

    if weather and weather.get("ok"):
        story.append(Paragraph("Погода", styles["TripText"]))
        story.append(
            Paragraph(
                f"{weather['city']}: {weather['temperature']} °C, "
                f"{weather['description']}, ветер {weather['wind_speed']} м/с",
                styles["TripText"],
            )
        )
        story.append(Spacer(1, 12))

    checklist_rows = [["Готово", "Пункт"]]
    for item in trip.checklist_items:
        checklist_rows.append(["Да" if item.is_done else "Нет", item.text])
    if len(checklist_rows) > 1:
        story.append(Paragraph("Чек-лист", styles["TripText"]))
        table = Table(checklist_rows, colWidths=[3 * cm, 13 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e7f1ff")),
                    ("FONTNAME", (0, 0), (-1, -1), font_name),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#c7d2fe")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("PADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 12))

    if trip.notes:
        story.append(Paragraph("Заметки", styles["TripText"]))
        for note in trip.notes:
            story.append(Paragraph(f"{note.title}: {note.content}", styles["TripText"]))
        story.append(Spacer(1, 12))

    if trip.documents:
        story.append(Paragraph("Документы", styles["TripText"]))
        for document in trip.documents:
            story.append(Paragraph(document.original_name, styles["TripText"]))

    doc.build(story)
    buffer.seek(0)
    return buffer
