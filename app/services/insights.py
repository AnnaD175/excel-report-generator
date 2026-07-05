import pandas as pd


def _format_number(value) -> str:
    if pd.isna(value):
        return "нет данных"

    if isinstance(value, float):
        formatted = f"{value:,.2f}".replace(",", " ")
        return formatted.rstrip("0").rstrip(".")

    if isinstance(value, int):
        return f"{value:,}".replace(",", " ")

    return str(value)


def _choose_main_numeric_column(df: pd.DataFrame) -> str | None:
    numeric_columns = df.select_dtypes(include=["number"]).columns.tolist()

    if not numeric_columns:
        return None

    priority_names = [
        "Выручка",
        "Сумма",
        "Доход",
        "Прибыль",
        "Цена",
        "Количество",
        "amount",
        "revenue",
        "total",
        "price",
        "quantity",
    ]

    for name in priority_names:
        for column in numeric_columns:
            if str(column).lower() == name.lower():
                return column

    return numeric_columns[0]


def _choose_category_column(df: pd.DataFrame) -> str | None:
    category_columns = df.select_dtypes(
        include=["object", "category", "string"]
    ).columns.tolist()

    if not category_columns:
        return None

    priority_names = [
        "Категория",
        "Товар",
        "Регион",
        "Отдел",
        "Статус",
        "Канал",
        "Тема",
        "category",
        "product",
        "region",
        "department",
        "status",
    ]

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


def generate_insights(df: pd.DataFrame) -> list[str]:
    insights = []

    if df.empty:
        return ["Загруженный файл не содержит строк для анализа."]

    numeric_column = _choose_main_numeric_column(df)

    if numeric_column is None:
        return [
            "В файле не найдено числовых столбцов, поэтому расчет количественных показателей невозможен.",
            f"Всего в таблице обнаружено {len(df)} строк и {len(df.columns)} столбцов.",
        ]

    clean_numeric = df[numeric_column].dropna()

    if clean_numeric.empty:
        return [
            f"Столбец «{numeric_column}» выбран для анализа, но не содержит корректных числовых значений."
        ]

    total_value = clean_numeric.sum()
    average_value = clean_numeric.mean()
    max_value = clean_numeric.max()
    min_value = clean_numeric.min()

    insights.append(
        f"Общая сумма по показателю «{numeric_column}» составляет {_format_number(total_value)}."
    )

    insights.append(
        f"Среднее значение показателя «{numeric_column}» равно {_format_number(average_value)}."
    )

    insights.append(
        f"Максимальное значение по столбцу «{numeric_column}» составляет {_format_number(max_value)}, "
        f"минимальное — {_format_number(min_value)}."
    )

    category_column = _choose_category_column(df)

    if category_column is not None:
        grouped = (
            df.groupby(category_column, dropna=False)[numeric_column]
            .sum()
            .sort_values(ascending=False)
        )

        if not grouped.empty:
            top_category = grouped.index[0]
            top_value = grouped.iloc[0]

            insights.append(
                f"Наибольшее значение показателя «{numeric_column}» приходится на "
                f"«{top_category}» по столбцу «{category_column}» — {_format_number(top_value)}."
            )

            if len(grouped) > 1:
                min_category = grouped.index[-1]
                min_category_value = grouped.iloc[-1]

                insights.append(
                    f"Наименьшее значение показателя «{numeric_column}» приходится на "
                    f"«{min_category}» — {_format_number(min_category_value)}."
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

            if len(grouped_by_date) >= 2:
                first_value = grouped_by_date.iloc[0]
                last_value = grouped_by_date.iloc[-1]

                if last_value > first_value:
                    insights.append(
                        f"По датам наблюдается рост показателя «{numeric_column}»: "
                        f"с {_format_number(first_value)} до {_format_number(last_value)}."
                    )
                elif last_value < first_value:
                    insights.append(
                        f"По датам наблюдается снижение показателя «{numeric_column}»: "
                        f"с {_format_number(first_value)} до {_format_number(last_value)}."
                    )
                else:
                    insights.append(
                        f"Первое и последнее значения по датам для показателя «{numeric_column}» совпадают."
                    )

                best_date = grouped_by_date.idxmax()
                best_date_value = grouped_by_date.max()

                insights.append(
                    f"Максимальное значение по датам зафиксировано {best_date.strftime('%d.%m.%Y')} "
                    f"и составило {_format_number(best_date_value)}."
                )

    return insights