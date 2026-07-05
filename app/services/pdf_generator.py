from pathlib import Path
from datetime import datetime

import pandas as pd

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
)

from app.services.analyzer import analyze_dataframe
from app.services.charts import generate_charts
from xml.sax.saxutils import escape
from app.services.insights import generate_insights


REPORTS_DIR = Path("reports")


def _register_font() -> str:
    font_paths = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/Arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
    ]

    for font_path in font_paths:
        if Path(font_path).exists():
            pdfmetrics.registerFont(TTFont("CustomFont", font_path))
            return "CustomFont"

    return "Helvetica"


def _format_value(value):
    if pd.isna(value):
        return ""

    if isinstance(value, float):
        return round(value, 2)

    return str(value)


def _chart_url_to_path(url: str) -> Path:
    return Path("app") / url.lstrip("/")


def generate_pdf_report(excel_path: str, output_filename: str) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_excel(excel_path)

    analysis = analyze_dataframe(df)
    charts = generate_charts(df)
    insights = generate_insights(df)

    output_path = REPORTS_DIR / output_filename

    font_name = _register_font()

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()

    for style_name in styles.byName:
        styles[style_name].fontName = font_name

    elements = []

    elements.append(Paragraph("Аналитический отчет по Excel-файлу", styles["Title"]))
    elements.append(Spacer(1, 12))

    elements.append(
        Paragraph(
            f"Дата формирования отчета: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            styles["Normal"],
        )
    )

    elements.append(Spacer(1, 18))

    elements.append(Paragraph("1. Общая информация", styles["Heading2"]))

    general_data = [
        ["Показатель", "Значение"],
        ["Количество строк", analysis["rows_count"]],
        ["Количество столбцов", analysis["columns_count"]],
        ["Числовые столбцы", ", ".join(analysis["numeric_columns"])],
    ]

    general_table = Table(general_data, colWidths=[7 * cm, 10 * cm])
    general_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    elements.append(general_table)

    elements.append(Paragraph("2. Автоматические выводы", styles["Heading2"]))

    if insights:
        for insight in insights:
            elements.append(
                Paragraph(
                    f"- {escape(str(insight))}",
                    styles["Normal"],
                )
            )
            elements.append(Spacer(1, 6))
    else:
        elements.append(Paragraph("Выводы не были сформированы.", styles["Normal"]))

    elements.append(Spacer(1, 18))

    elements.append(Paragraph("3. Числовые показатели", styles["Heading2"]))

    if analysis["summary"]:
        summary_data = [["Столбец", "Сумма", "Среднее", "Минимум", "Максимум"]]

        for column, values in analysis["summary"].items():
            summary_data.append(
                [
                    column,
                    values["sum"],
                    values["average"],
                    values["min"],
                    values["max"],
                ]
            )

        summary_table = Table(
            summary_data,
            colWidths=[5 * cm, 3 * cm, 3 * cm, 3 * cm, 3 * cm],
        )

        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTNAME", (0, 0), (-1, -1), font_name),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("PADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )

        elements.append(summary_table)
    else:
        elements.append(Paragraph("В файле не найдено числовых столбцов.", styles["Normal"]))

    elements.append(PageBreak())

    elements.append(Paragraph("4. Графики", styles["Heading2"]))

    if charts:
        for chart in charts:
            chart_path = _chart_url_to_path(chart["url"])

            if chart_path.exists():
                elements.append(Paragraph(chart["title"], styles["Heading3"]))
                elements.append(Spacer(1, 8))

                if "Доля" in chart["title"]:
                    chart_image = Image(str(chart_path), width=12 * cm, height=12 * cm)
                else:
                    chart_image = Image(str(chart_path), width=16 * cm, height=8 * cm)

                elements.append(chart_image)
                elements.append(Spacer(1, 18))
    else:
        elements.append(Paragraph("Для построения графиков недостаточно данных.", styles["Normal"]))

    elements.append(PageBreak())

    elements.append(Paragraph("5. Предпросмотр данных", styles["Heading2"]))

    preview_df = df.head(10)

    table_data = [preview_df.columns.tolist()]

    for _, row in preview_df.iterrows():
        table_data.append([_format_value(value) for value in row.tolist()])

    preview_table = Table(table_data, repeatRows=1)

    preview_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("PADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )

    elements.append(preview_table)

    doc.build(elements)

    return output_path