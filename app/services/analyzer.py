import pandas as pd


def analyze_dataframe(df: pd.DataFrame) -> dict:
    numeric_columns = df.select_dtypes(include=["number"]).columns.tolist()

    analysis = {
        "rows_count": len(df),
        "columns_count": len(df.columns),
        "columns": df.columns.tolist(),
        "numeric_columns": numeric_columns,
        "summary": {}
    }

    for column in numeric_columns:
        analysis["summary"][column] = {
            "sum": round(df[column].sum(), 2),
            "average": round(df[column].mean(), 2),
            "min": round(df[column].min(), 2),
            "max": round(df[column].max(), 2)
        }

    return analysis