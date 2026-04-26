from io import BytesIO
from pathlib import Path

def _register_font():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    fonts = [
        Path('C:/Windows/Fonts/arial.ttf'),
        Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
    ]
    for path in fonts:
        if path.exists():
            pdfmetrics.registerFont(TTFont('TripPlannerFont', str(path)))
            return 'TripPlannerFont'
    return 'Helvetica'

def generate_trip_pdf(trip, weather=None):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buf = BytesIO()
    font = _register_font()
    st = getSampleStyleSheet()
    st.add(
        ParagraphStyle(
            name='TripTitle',
            fontName=font,
            fontSize=22,
            leading=28,
            spaceAfter=16,
        )
    )
    st.add(
        ParagraphStyle(
            name='TripText',
            fontName=font,
            fontSize=11,
            leading=16,
        )
    )
    fmt = '%d.%m.%Y'
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    story = [
        Paragraph(f'Маршрут: {trip.title}', st['TripTitle']),
        Paragraph(f'Направление: {trip.destination}', st['TripText']),
        Paragraph(
            f'Даты: {trip.start_date.strftime(fmt)} - '
            f'{trip.end_date.strftime(fmt)} ({trip.days} дн.)',
            st['TripText'],
        ),
        Paragraph(f'Бюджет: {trip.budget} руб.', st['TripText']),
        Spacer(1, 12),
    ]
    if trip.description:
        story.append(Paragraph('Описание', st['TripText']))
        story.append(Paragraph(trip.description, st['TripText']))
        story.append(Spacer(1, 12))
    if weather and weather.get('ok'):
        city = weather['city']
        temp = weather['temperature']
        desc = weather['description']
        wind = weather['wind_speed']
        story.append(Paragraph('Погода', st['TripText']))
        story.append(Paragraph(f'{city}: {temp} °C, {desc}, ветер {wind} м/с', st['TripText']))
        story.append(Spacer(1, 12))
    rows = [['Готово', 'Пункт']]
    for item in trip.checklist_items:
        rows.append(['Да' if item.is_done else 'Нет', item.text])
    if len(rows) > 1:
        story.append(Paragraph('Чек-лист', st['TripText']))
        table = Table(rows, colWidths=[3 * cm, 13 * cm])
        table.setStyle(
            TableStyle(
                [
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e7f1ff')),
                    ('FONTNAME', (0, 0), (-1, -1), font),
                    ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#c7d2fe')),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('PADDING', (0, 0), (-1, -1), 7),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 12))
    if trip.notes:
        story.append(Paragraph('Заметки', st['TripText']))
        for note in trip.notes:
            story.append(Paragraph(f'{note.title}: {note.content}', st['TripText']))
        story.append(Spacer(1, 12))
    if trip.documents:
        story.append(Paragraph('Документы', st['TripText']))
        for doc_file in trip.documents:
            story.append(Paragraph(doc_file.original_name, st['TripText']))
    doc.build(story)
    buf.seek(0)
    return buf
