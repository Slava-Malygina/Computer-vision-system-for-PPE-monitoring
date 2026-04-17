import csv

import os
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER


def export_to_pdf(data, file_path):
    font_name = "DejaVuSerif"
    try:
        font_path = os.path.join(os.path.dirname(__file__), 'fonts', 'DejaVuSerif.ttf')
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont(font_name, font_path))
        else:
            raise FileNotFoundError(f"Шрифт не найден: {font_path}")
    except Exception as e:
        font_name = "Helvetica"
    
    headers = ["Дата", "Время", "ID камеры", "ID нарушителя", "Тип нарушения", "Вероятность", "Путь к скриншоту"]
    violation_map = {
        "no_helmet": "Без каски",
        "no_vest": "Без жилета",
        "no_gloves": "Без перчаток"
    }
    
    pdf_data = [headers]
    for row in data:
        violation_type = row.get("violation_type", "")
        violation_display = violation_map.get(violation_type, violation_type)
        pdf_row = [
            row.get("date", ""),
            row.get("time", ""),
            row.get("camera_id", ""),
            row.get("human_id", ""),
            violation_display,
            f"{row.get('confidence', 0):.2f}",
            row.get("screenshot_path", "")
        ]
        pdf_data.append(pdf_row)
    
    doc = SimpleDocTemplate(file_path, pagesize=landscape(A4), topMargin=30, bottomMargin=30)
    table = Table(pdf_data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    title_style.fontName = font_name
    title_style.fontSize = 16
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
