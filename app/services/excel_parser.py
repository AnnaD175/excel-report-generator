import pandas as pd

from app.services.validators import ExcelValidationError


def read_excel_file(file_path: str) -> pd.DataFrame:
    try:
        df = pd.read_excel(file_path)
    except PermissionError:
        raise ExcelValidationError(
            "Не удалось открыть файл. Возможно, он открыт в Excel или заблокирован системой."
        )
    except ValueError:
        raise ExcelValidationError(
            "Не удалось прочитать Excel-файл. Проверьте, что файл не поврежден."
        )
    except Exception:
        raise ExcelValidationError(
            "Произошла ошибка при чтении Excel-файла. Проверьте структуру документа."
        )

    return df