from pathlib import Path
from datetime import datetime


REPORTS_DIR = Path("reports")


def get_reports_history() -> list[dict]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    report_files = sorted(
        REPORTS_DIR.glob("*.pdf"),
        key=lambda file: file.stat().st_mtime,
        reverse=True,
    )

    reports = []

    for file in report_files:
        stat = file.stat()

        reports.append(
            {
                "filename": file.name,
                "created_at": datetime.fromtimestamp(stat.st_mtime).strftime(
                    "%d.%m.%Y %H:%M"
                ),
                "size_kb": round(stat.st_size / 1024, 2),
                "download_url": f"/reports/download/{file.name}",
            }
        )

    return reports