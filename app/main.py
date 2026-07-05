from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from app.services.pdf_generator import generate_pdf_report
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from app.services.insights import generate_insights

import shutil
import os

from pathlib import Path
from datetime import datetime

from app.services.excel_parser import read_excel_file
from app.services.analyzer import analyze_dataframe
from app.services.charts import generate_charts
from app.services.report_history import get_reports_history

from app.services.validators import (
    ExcelValidationError,
    validate_uploaded_file,
    validate_file_size,
    validate_dataframe,
)

app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

UPLOAD_DIR = "uploads"

os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={}
    )


@app.post("/upload", response_class=HTMLResponse)
async def upload_file(request: Request, file: UploadFile = File(...)):
    try:
        validate_uploaded_file(file)

        safe_filename = os.path.basename(file.filename)
        file_path = os.path.join(UPLOAD_DIR, safe_filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        validate_file_size(file_path)

        df = read_excel_file(file_path)

        validate_dataframe(df)

        analysis = analyze_dataframe(df)
        charts = generate_charts(df)
        insights = generate_insights(df)

        preview_data = df.head(10).to_dict(orient="records")
        columns = df.columns.tolist()

        return templates.TemplateResponse(
            request=request,
            name="preview.html",
            context={
                "filename": safe_filename,
                "columns": columns,
                "rows": preview_data,
                "analysis": analysis,
                "charts": charts,
                "insights": insights,
            },
        )

    except ExcelValidationError as error:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "error": str(error),
            },
        )

    except Exception:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "error": "Произошла непредвиденная ошибка при обработке файла.",
            },
        )

@app.post("/generate-report")
async def generate_report(request: Request, filename: str = Form(...)):
    try:
        safe_filename = os.path.basename(filename)
        file_path = os.path.join(UPLOAD_DIR, safe_filename)

        if not os.path.exists(file_path):
            return templates.TemplateResponse(
                request=None,
                name="index.html",
                context={
                    "error": "Исходный Excel-файл не найден. Загрузите файл заново."
                },
            )

        source_name = Path(safe_filename).stem
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        report_filename = f"report_{source_name}_{timestamp}.pdf"

        report_path = generate_pdf_report(
            excel_path=file_path,
            output_filename=report_filename,
        )

        return FileResponse(
            path=report_path,
            filename=report_filename,
            media_type="application/pdf",
        )

    except ExcelValidationError as error:
        return {"error": str(error)}

    except Exception:
        return {"error": "Не удалось сформировать PDF-отчет."}

@app.get("/reports", response_class=HTMLResponse)
def reports_page(request: Request):
    reports = get_reports_history()

    status = request.query_params.get("status")

    message = None
    error = None

    if status == "deleted":
        message = "Отчет успешно удален."
    elif status == "not_found":
        error = "Отчет не найден."
    elif status == "invalid":
        error = "Некорректное имя файла отчета."
    elif status == "locked":
        error = "Не удалось удалить отчет. Возможно, файл открыт в другой программе."
    elif status == "delete_error":
        error = "Произошла ошибка при удалении отчета."

    return templates.TemplateResponse(
        request=request,
        name="reports.html",
        context={
            "reports": reports,
            "message": message,
            "error": error,
        },
    )

@app.get("/reports/download/{filename}")
def download_report(filename: str):
    safe_filename = os.path.basename(filename)
    report_path = Path("reports") / safe_filename

    if not report_path.exists():
        return {"error": "Отчет не найден"}

    return FileResponse(
        path=report_path,
        filename=safe_filename,
        media_type="application/pdf",
    )

@app.post("/reports/delete/{filename}")
def delete_report(filename: str):
    safe_filename = os.path.basename(filename)
    report_path = Path("reports") / safe_filename

    if report_path.suffix.lower() != ".pdf":
        return RedirectResponse(url="/reports?status=invalid", status_code=303)

    if not report_path.exists():
        return RedirectResponse(url="/reports?status=not_found", status_code=303)

    try:
        report_path.unlink()
    except PermissionError:
        return RedirectResponse(url="/reports?status=locked", status_code=303)
    except Exception:
        return RedirectResponse(url="/reports?status=delete_error", status_code=303)

    return RedirectResponse(url="/reports?status=deleted", status_code=303)