from pathlib import Path

import pandas as pd
from fastapi import UploadFile


MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


class ExcelValidationError(Exception):
    pass


def validate_uploaded_file(file: UploadFile | None) -> None:
    if file is None or not file.filename:
        raise ExcelValidationError("Выберите Excel-файл для загрузки.")

    file_extension = Path(file.filename).suffix.lower()

    if file_extension != ".xlsx":
        raise ExcelValidationError("Поддерживаются только файлы формата .xlsx.")

    content_type = file.content_type or ""

    allowed_content_types = [
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/octet-stream",
    ]

    if content_type not in allowed_content_types:
        raise ExcelValidationError("Загруженный файл не похож на Excel-документ.")


def validate_file_size(file_path: str) -> None:
    size = Path(file_path).stat().st_size

    if size == 0:
        raise ExcelValidationError("Загруженный файл пустой.")

    if size > MAX_FILE_SIZE_BYTES:
        raise ExcelValidationError(
            f"Размер файла превышает допустимый лимит {MAX_FILE_SIZE_MB} МБ."
        )


def validate_dataframe(df: pd.DataFrame) -> None:
    if df.empty:
        raise ExcelValidationError("Excel-файл не содержит строк для анализа.")

    if len(df.columns) == 0:
        raise ExcelValidationError("Excel-файл не содержит столбцов.")

    numeric_columns = df.select_dtypes(include=["number"]).columns.tolist()

    if not numeric_columns:
        raise ExcelValidationError(
            "В Excel-файле не найдено числовых столбцов. "
            "Для построения аналитики нужен хотя бы один числовой столбец."
        )

    if len(df) > 10000:
        raise ExcelValidationError(
            "Файл содержит слишком много строк. "
            "Для текущей версии приложения допустимо не более 10 000 строк."
        )