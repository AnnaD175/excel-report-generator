from pathlib import Path
from datetime import datetime
import re
from xml.sax.saxutils import escape

import pandas as pd

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
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

from app.services.excel_parser import read_excel_file
from app.services.insights import generate_insights
from app.services.charts import generate_charts


REPORTS_DIR = Path("reports")


def _register_fonts() -> tuple[str, str]:
    regular_paths = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    bold_paths = [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/calibrib.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]

    regular_font = "Helvetica"
    bold_font = "Helvetica-Bold"

    for path in regular_paths:
        if Path(path).exists():
            pdfmetrics.registerFont(TTFont("AppFont", path))
            regular_font = "AppFont"
            break

    for path in bold_paths:
        if Path(path).exists():
            pdfmetrics.registerFont(TTFont("AppFontBold", path))
            bold_font = "AppFontBold"
            break

    return regular_font, bold_font


FONT_NAME, FONT_BOLD = _register_fonts()


def _format_number(value) -> str:
    if pd.isna(value):
        return "нет данных"

    if isinstance(value, float):
        text = f"{value:,.2f}".replace(",", " ")
        return text.rstrip("0").rstrip(".")

    if isinstance(value, int):
        return f"{value:,}".replace(",", " ")

    return str(value)


def _bold_numbers(text: str) -> str:
    escaped_text = escape(str(text))

    return re.sub(
        r"(?<!\w)(\d[\d\s.,]*\d|\d)(?!\w)",
        r"<b>\1</b>",
        escaped_text,
    )


def _get_chart_path(chart: dict) -> str | None:
    if "path" in chart and chart["path"]:
        return chart["path"]

    if "filename" in chart and chart["filename"]:
        return str(Path("app/static/charts") / chart["filename"])

    if "url" in chart and chart["url"]:
        url = chart["url"].lstrip("/")
        return str(Path("app") / url)

    return None


def _build_styles():
    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            fontName=FONT_BOLD,
            fontSize=24,
            leading=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#172338"),
            spaceAfter=10,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SectionTitle",
            fontName=FONT_BOLD,
            fontSize=17,
            leading=22,
            textColor=colors.HexColor("#172338"),
            spaceBefore=18,
            spaceAfter=12,
        )
    )

    styles.add(
        ParagraphStyle(
            name="NormalText",
            fontName=FONT_NAME,
            fontSize=10.5,
            leading=15,
            textColor=colors.HexColor("#172338"),
        )
    )

    styles.add(
        ParagraphStyle(
            name="SmallText",
            fontName=FONT_NAME,
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#5f6b7a"),
        )
    )

    styles.add(
        ParagraphStyle(
            name="InsightText",
            fontName=FONT_NAME,
            fontSize=10.5,
            leading=15,
            textColor=colors.HexColor("#172338"),
            leftIndent=0,
        )
    )

    return styles


def _add_page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont(FONT_NAME, 9)
    canvas.setFillColor(colors.HexColor("#6b7280"))

    page_number = f"Страница {doc.page}"
    canvas.drawRightString(200 * mm, 12 * mm, page_number)

    canvas.restoreState()


def _make_info_table(df: pd.DataFrame, styles):
    numeric_columns = df.select_dtypes(include=["number"]).columns.tolist()

    data = [
        [
            Paragraph("<b>Показатель</b>", styles["NormalText"]),
            Paragraph("<b>Значение</b>", styles["NormalText"]),
        ],
        [
            Paragraph("Количество строк", styles["NormalText"]),
            Paragraph(str(len(df)), styles["NormalText"]),
        ],
        [
            Paragraph("Количество столбцов", styles["NormalText"]),
            Paragraph(str(len(df.columns)), styles["NormalText"]),
        ],
        [
            Paragraph("Числовые столбцы", styles["NormalText"]),
            Paragraph(
                ", ".join(map(str, numeric_columns)) or "не найдены",
                styles["NormalText"],
            ),
        ],
    ]

    table = Table(data, colWidths=[60 * mm, 110 * mm])

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef5e7")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#2d5d1d")),
                ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
                ("FONTNAME", (0, 1), (-1, -1), FONT_NAME),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d6e5c5")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )

    return table


def _make_numeric_summary_table(df: pd.DataFrame, styles):
    numeric_columns = df.select_dtypes(include=["number"]).columns.tolist()

    data = [
        [
            Paragraph("<b>Столбец</b>", styles["NormalText"]),
            Paragraph("<b>Сумма</b>", styles["NormalText"]),
            Paragraph("<b>Среднее</b>", styles["NormalText"]),
            Paragraph("<b>Минимум</b>", styles["NormalText"]),
            Paragraph("<b>Максимум</b>", styles["NormalText"]),
        ]
    ]

    for column in numeric_columns:
        series = df[column].dropna()

        if series.empty:
            continue

        data.append(
            [
                Paragraph(escape(str(column)), styles["NormalText"]),
                Paragraph(_format_number(series.sum()), styles["NormalText"]),
                Paragraph(_format_number(series.mean()), styles["NormalText"]),
                Paragraph(_format_number(series.min()), styles["NormalText"]),
                Paragraph(_format_number(series.max()), styles["NormalText"]),
            ]
        )

    if len(data) == 1:
        data.append(
            [
                Paragraph("Нет данных", styles["NormalText"]),
                Paragraph("-", styles["NormalText"]),
                Paragraph("-", styles["NormalText"]),
                Paragraph("-", styles["NormalText"]),
                Paragraph("-", styles["NormalText"]),
            ]
        )

    table = Table(data, colWidths=[48 * mm, 32 * mm, 32 * mm, 29 * mm, 29 * mm])

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef5e7")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#2d5d1d")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d6e5c5")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )

    return table


def _make_insight_card(text: str, styles):
    paragraph = Paragraph(_bold_numbers(text), styles["InsightText"])

    table = Table([[paragraph]], colWidths=[170 * mm])

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f7fbf3")),
                ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#d6e5c5")),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )

    return table


def _make_preview_table(df: pd.DataFrame, styles):
    preview_df = df.head(8).copy()

    data = []

    headers = [
        Paragraph(f"<b>{escape(str(column))}</b>", styles["SmallText"])
        for column in preview_df.columns
    ]

    data.append(headers)

    for _, row in preview_df.iterrows():
        data.append(
            [
                Paragraph(escape(str(value)), styles["SmallText"])
                for value in row.tolist()
            ]
        )

    column_count = len(preview_df.columns)

    if column_count == 0:
        return Paragraph("Нет данных для предпросмотра.", styles["NormalText"])

    available_width = 170 * mm
    column_width = available_width / column_count

    table = Table(data, colWidths=[column_width] * column_count, repeatRows=1)

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef5e7")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#2d5d1d")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8d8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    return table


def generate_pdf_report(excel_path: str, output_filename: str = "report.pdf") -> str:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    df = read_excel_file(excel_path)
    insights = generate_insights(df)
    charts = generate_charts(df)

    excel_filename = Path(excel_path).name
    output_path = REPORTS_DIR / output_filename

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )

    styles = _build_styles()
    elements = []

    elements.append(
        Paragraph(
            f"Аналитический отчет по файлу<br/><b>{escape(excel_filename)}</b>",
            styles["ReportTitle"],
        )
    )
    elements.append(Spacer(1, 12))

    generated_at = datetime.now().strftime("%d.%m.%Y %H:%M")

    elements.append(
        Paragraph(
            f"<b>Дата формирования:</b> {generated_at}",
            styles["NormalText"],
        )
    )

    elements.append(
        Paragraph(
            f"<b>Исходный файл:</b> {escape(excel_filename)}",
            styles["NormalText"],
        )
    )

    elements.append(Spacer(1, 14))

    elements.append(Paragraph("1. Общая информация", styles["SectionTitle"]))
    elements.append(_make_info_table(df, styles))

    elements.append(Paragraph("2. Автоматические выводы", styles["SectionTitle"]))

    if insights:
        for insight in insights:
            elements.append(_make_insight_card(insight, styles))
            elements.append(Spacer(1, 7))
    else:
        elements.append(Paragraph("Выводы не были сформированы.", styles["NormalText"]))

    elements.append(PageBreak())
    elements.append(Paragraph("3. Числовые показатели", styles["SectionTitle"]))
    elements.append(_make_numeric_summary_table(df, styles))

    if charts:
        elements.append(PageBreak())
        elements.append(Paragraph("4. Графики", styles["SectionTitle"]))

        # Первый и второй графики размещаются на одной странице
        first_two_charts = charts[:2]

        for chart in first_two_charts:
            chart_title = chart.get("title", "График")
            chart_path = _get_chart_path(chart)

            elements.append(
                Paragraph(
                    f"<b>{escape(str(chart_title))}</b>",
                    styles["NormalText"],
                )
            )
            elements.append(Spacer(1, 6))

            if chart_path and Path(chart_path).exists():
                img = Image(chart_path)
                img._restrictSize(145 * mm, 68 * mm)
                elements.append(img)
                elements.append(Spacer(1, 10))
            else:
                elements.append(
                    Paragraph(
                        "Изображение графика не найдено.",
                        styles["SmallText"],
                    )
                )
                elements.append(Spacer(1, 10))

        # Третий и последующие графики размещаются отдельно
        remaining_charts = charts[2:]

        for chart in remaining_charts:
            elements.append(PageBreak())

            chart_title = chart.get("title", "График")
            chart_path = _get_chart_path(chart)

            elements.append(
                Paragraph(
                    f"<b>{escape(str(chart_title))}</b>",
                    styles["NormalText"],
                )
            )
            elements.append(Spacer(1, 8))

            if chart_path and Path(chart_path).exists():
                img = Image(chart_path)
                img._restrictSize(155 * mm, 90 * mm)
                elements.append(img)
                elements.append(Spacer(1, 12))
            else:
                elements.append(
                    Paragraph(
                        "Изображение графика не найдено.",
                        styles["SmallText"],
                    )
                )
                elements.append(Spacer(1, 10))

    elements.append(PageBreak())
    elements.append(Paragraph("5. Предпросмотр данных", styles["SectionTitle"]))
    elements.append(
        Paragraph(
            "Ниже показаны первые строки исходной таблицы.",
            styles["SmallText"],
        )
    )
    elements.append(Spacer(1, 8))
    elements.append(_make_preview_table(df, styles))

    doc.build(
        elements,
        onFirstPage=_add_page_number,
        onLaterPages=_add_page_number,
    )

    return str(output_path)