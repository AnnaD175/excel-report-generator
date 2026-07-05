from pathlib import Path
from uuid import uuid4

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


CHARTS_DIR = Path("app/static/charts")


def _choose_numeric_column(df: pd.DataFrame) -> str | None:
    numeric_columns = df.select_dtypes(include=["number"]).columns.tolist()

    if not numeric_columns:
        return None

    priority_names = ["Выручка", "Сумма", "Доход", "Цена", "Количество", "amount", "revenue", "total"]

    for name in priority_names:
        for column in numeric_columns:
            if str(column).lower() == name.lower():
                return column

    return numeric_columns[0]


def _choose_category_column(df: pd.DataFrame) -> str | None:
    category_columns = df.select_dtypes(include=["object", "category", "string"]).columns.tolist()

    if not category_columns:
        return None

    priority_names = ["Категория", "Товар", "Регион", "Отдел", "Статус", "category", "product", "region"]

    for name in priority_names:
        for column in category_columns:
            if str(column).lower() == name.lower():
                return column

    return category_columns[0]


def _choose_date_column(df: pd.DataFrame) -> str | None:
    for column in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[column]):
            return column

    for column in df.columns:
        column_name = str(column).lower()

        if "дата" in column_name or "date" in column_name:
            converted = pd.to_datetime(df[column], errors="coerce")

            if converted.notna().sum() >= 2:
                return column

    return None


def _save_current_plot() -> str:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid4().hex}.png"
    file_path = CHARTS_DIR / filename

    plt.tight_layout()
    plt.savefig(file_path, dpi=150)
    plt.close()

    return f"/static/charts/{filename}"


def generate_charts(df: pd.DataFrame) -> list[dict]:
    charts = []

    numeric_column = _choose_numeric_column(df)

    if numeric_column is None:
        return charts

    category_column = _choose_category_column(df)

    if category_column is not None:
        grouped = (
            df.groupby(category_column, dropna=False)[numeric_column]
            .sum()
            .sort_values(ascending=False)
            .head(10)
        )

        plt.figure(figsize=(10, 5))
        grouped.sort_values().plot(kind="barh")
        plt.title(f"{numeric_column} по столбцу «{category_column}»")
        plt.xlabel(numeric_column)
        plt.ylabel(category_column)

        charts.append(
            {
                "title": f"{numeric_column} по столбцу «{category_column}»",
                "url": _save_current_plot(),
            }
        )

    date_column = _choose_date_column(df)

    if date_column is not None:
        temp_df = df.copy()
        temp_df[date_column] = pd.to_datetime(temp_df[date_column], errors="coerce")
        temp_df = temp_df.dropna(subset=[date_column])

        if not temp_df.empty:
            grouped_by_date = (
                temp_df.groupby(temp_df[date_column].dt.date)[numeric_column]
                .sum()
                .sort_index()
            )

            plt.figure(figsize=(10, 5))
            grouped_by_date.plot(kind="line", marker="o")
            plt.title(f"Динамика показателя «{numeric_column}» по датам")
            plt.xlabel("Дата")
            plt.ylabel(numeric_column)
            plt.xticks(rotation=45)

            charts.append(
                {
                    "title": f"Динамика показателя «{numeric_column}» по датам",
                    "url": _save_current_plot(),
                }
            )

    if category_column is not None:
        grouped = (
            df.groupby(category_column, dropna=False)[numeric_column]
            .sum()
            .sort_values(ascending=False)
        )

        top_values = grouped.head(5)

        if len(grouped) > 5:
            other_sum = grouped.iloc[5:].sum()
            top_values.loc["Другое"] = other_sum

        plt.figure(figsize=(8, 8))
        top_values.plot(kind="pie", autopct="%1.1f%%")
        plt.title(f"Доля показателя «{numeric_column}» по столбцу «{category_column}»")
        plt.ylabel("")
        plt.axis("equal")

        charts.append(
            {
                "title": f"Доля показателя «{numeric_column}» по столбцу «{category_column}»",
                "url": _save_current_plot(),
            }
        )

    return charts