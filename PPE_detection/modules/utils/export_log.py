import csv

import os
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER

from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from modules.utils.path_manager import path_manager


def export_to_pdf(data, file_path):
    font_name = "DejaVuSerif"
    try:
        font_path = path_manager.get_font_path('DejaVuSerif.ttf')
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont(font_name, font_path))
    except:
        font_name = "Helvetica"

    # Создаём стиль для ячеек с переносом
    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle(
        'CellStyle',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=8,
        alignment=TA_LEFT,
        leading=10  # межстрочный интервал
    )

    headers = ["Дата", "Время", "ID камеры", "ID нарушителя", "Тип нарушения", "Вероятность", "Путь к скриншоту"]
    violation_map = {
        "no_helmet": "Без каски",
        "no_vest": "Без жилета",
        "no_gloves": "Без перчаток"
    }

    # Создаём данные с Paragraph для длинных строк
    pdf_data = []

    # Заголовки тоже через Paragraph
    header_row = [Paragraph(f"<b>{h}</b>", cell_style) for h in headers]
    pdf_data.append(header_row)

    for row in data:
        violation_type = row.get("violation_type", "")
        violation_display = violation_map.get(violation_type, violation_type)

        # Длинный путь к скриншоту оборачиваем в Paragraph - будет переноситься
        screenshot_path = row.get("screenshot_path", "")
        screenshot_paragraph = Paragraph(screenshot_path, cell_style)

        pdf_row = [
            Paragraph(row.get("date", ""), cell_style),
            Paragraph(row.get("time", ""), cell_style),
            Paragraph(row.get("camera_id", ""), cell_style),
            Paragraph(str(row.get("human_id", "")), cell_style),
            Paragraph(violation_display, cell_style),
            Paragraph(f"{row.get('confidence', 0):.2f}", cell_style),
            screenshot_paragraph,  # <-- многострочный!
        ]
        pdf_data.append(pdf_row)

    doc = SimpleDocTemplate(file_path, pagesize=landscape(A4), topMargin=30, bottomMargin=30)

    # Задаём ширину колонок
    col_widths = [60, 50, 100, 60, 80, 60, 150]
    table = Table(pdf_data, repeatRows=1, colWidths=col_widths)

    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # Выравнивание по верху для многострочности
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('WORDWRAP', (0, 0), (-1, -1), True),  # Включаем перенос слов
    ]))

    title_style = styles['Title']
    title_style.fontName = font_name
    title_style.fontSize = 14
    title_style.alignment = TA_CENTER
    title = Paragraph("Отчёт по нарушениям СИЗ", title_style)

    doc.build([title, Spacer(1, 12), table])

def export_to_csv(data, file_path):
    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        if not data:
            return
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)


def export_to_xlsx(data, file_path):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Нарушения"

    if not data:
        return

    headers = list(data[0].keys())
    ws.append(headers)

    for row in data:
        ws.append([row.get(h, "") for h in headers])

    wb.save(file_path)
