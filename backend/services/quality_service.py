from __future__ import annotations

import uuid
from typing import Any

import numpy as np
import pandas as pd

from storage.dataset_store import LocalDatasetStore


class QualityService:
    def __init__(self) -> None:
        self._store = LocalDatasetStore()

    async def run_quality_report(self, dataset_id: uuid.UUID) -> dict[str, Any]:
        df = await self._store.load(dataset_id)
        if df is None or df.empty:
            raise ValueError("Dataset not found or empty")

        missing = await self._check_missing_values(df)
        duplicates = await self._check_duplicates(df)
        outliers = await self._check_outliers(df)
        constants = await self._check_constant_columns(df)
        score = await self._generate_quality_score(df, missing, duplicates, outliers, constants)
        suggestions = await self._suggest_improvements(missing, duplicates, outliers, constants)

        return {
            "dataset_id": str(dataset_id),
            "shape": {"rows": len(df), "columns": len(df.columns)},
            "dtypes": {str(k): str(v) for k, v in df.dtypes.to_dict().items()},
            "missing_values": missing,
            "duplicates": duplicates,
            "outliers": outliers,
            "constant_columns": constants,
            "quality_score": score,
            "suggestions": suggestions,
        }

    async def check_missing_values(
        self,
        dataset_id: uuid.UUID,
    ) -> dict[str, Any]:
        df = await self._store.load(dataset_id)
        if df is None:
            raise ValueError("Dataset not found")
        return await self._check_missing_values(df)

    async def check_duplicates(
        self,
        dataset_id: uuid.UUID,
    ) -> dict[str, Any]:
        df = await self._store.load(dataset_id)
        if df is None:
            raise ValueError("Dataset not found")
        return await self._check_duplicates(df)

    async def check_outliers(
        self,
        dataset_id: uuid.UUID,
    ) -> dict[str, Any]:
        df = await self._store.load(dataset_id)
        if df is None:
            raise ValueError("Dataset not found")
        return await self._check_outliers(df)

    async def check_constant_columns(
        self,
        dataset_id: uuid.UUID,
    ) -> list[str]:
        df = await self._store.load(dataset_id)
        if df is None:
            raise ValueError("Dataset not found")
        return await self._check_constant_columns(df)

    async def _check_missing_values(self, df: pd.DataFrame) -> dict[str, Any]:
        missing_counts = df.isnull().sum()
        missing_percentages = (df.isnull().sum() / len(df)) * 100
        total_missing = int(missing_counts.sum())
        total_cells = df.size

        columns_detail = []
        for col in df.columns:
            count = int(missing_counts[col])
            if count > 0:
                columns_detail.append({
                    "column": col,
                    "missing_count": count,
                    "missing_percentage": round(float(missing_percentages[col]), 2),
                })

        columns_detail.sort(key=lambda x: x["missing_count"], reverse=True)

        return {
            "total_missing": total_missing,
            "total_cells": total_cells,
            "missing_percentage": round((total_missing / total_cells) * 100, 2) if total_cells else 0,
            "columns_with_missing": len(columns_detail),
            "columns_detail": columns_detail,
        }

    async def _check_duplicates(self, df: pd.DataFrame) -> dict[str, Any]:
        full_duplicates = int(df.duplicated(keep="first").sum())
        return {
            "total_duplicate_rows": full_duplicates,
            "duplicate_percentage": round((full_duplicates / len(df)) * 100, 2) if len(df) else 0,
        }

    async def _check_outliers(self, df: pd.DataFrame) -> dict[str, Any]:
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        outlier_info = {}

        for col in numeric_cols:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            lower = Q1 - 1.5 * IQR
            upper = Q3 + 1.5 * IQR
            outliers = df[(df[col] < lower) | (df[col] > upper)]
            outlier_info[col] = {
                "count": len(outliers),
                "percentage": round((len(outliers) / len(df)) * 100, 2) if len(df) else 0,
                "lower_bound": round(float(lower), 4),
                "upper_bound": round(float(upper), 4),
            }

        return {
            "columns_analyzed": list(numeric_cols),
            "outlier_details": outlier_info,
            "total_outliers": sum(v["count"] for v in outlier_info.values()),
        }

    async def _check_constant_columns(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        constant_cols = []
        for col in df.columns:
            unique_count = df[col].nunique(dropna=False)
            if unique_count <= 1:
                constant_cols.append({
                    "column": col,
                    "unique_values": int(unique_count),
                    "value": df[col].iloc[0] if len(df) else None,
                })
        return constant_cols

    async def _generate_quality_score(
        self,
        df: pd.DataFrame,
        missing: dict[str, Any],
        duplicates: dict[str, Any],
        outliers: dict[str, Any],
        constants: list[dict[str, Any]],
    ) -> dict[str, Any]:
        total_cells = df.size
        if total_cells == 0:
            return {"score": 0.0, "grade": "F", "components": {}}

        missing_ratio = missing["total_missing"] / total_cells
        duplicate_ratio = duplicates["total_duplicate_rows"] / len(df) if len(df) else 0
        outlier_ratio = outliers["total_outliers"] / (len(df) * len(outliers["columns_analyzed"])) if outliers["columns_analyzed"] and len(df) else 0
        constant_ratio = len(constants) / len(df.columns) if len(df.columns) else 0

        completeness = 1.0 - missing_ratio
        uniqueness = 1.0 - duplicate_ratio
        consistency = 1.0 - outlier_ratio
        variability = 1.0 - constant_ratio

        score = round((completeness * 0.35 + uniqueness * 0.25 + consistency * 0.25 + variability * 0.15) * 100, 2)

        if score >= 90:
            grade = "A"
        elif score >= 80:
            grade = "B"
        elif score >= 70:
            grade = "C"
        elif score >= 60:
            grade = "D"
        else:
            grade = "F"

        return {
            "score": score,
            "grade": grade,
            "components": {
                "completeness": round(completeness * 100, 2),
                "uniqueness": round(uniqueness * 100, 2),
                "consistency": round(consistency * 100, 2),
                "variability": round(variability * 100, 2),
            },
        }

    async def _suggest_improvements(
        self,
        missing: dict[str, Any],
        duplicates: dict[str, Any],
        outliers: dict[str, Any],
        constants: list[dict[str, Any]],
    ) -> list[dict[str, str]]:
        suggestions = []

        if missing["total_missing"] > 0:
            suggestions.append({
                "issue": "Missing values detected",
                "suggestion": "Use 'Handle Missing Values' to drop, fill with mean/median/mode, or forward/backward fill.",
                "severity": "high" if missing["missing_percentage"] > 10 else "medium",
            })

        if duplicates["total_duplicate_rows"] > 0:
            suggestions.append({
                "issue": "Duplicate rows found",
                "suggestion": "Use 'Remove Duplicates' to clean duplicate records.",
                "severity": "medium",
            })

        if outliers["total_outliers"] > 0:
            suggestions.append({
                "issue": "Outliers detected in numeric columns",
                "suggestion": "Review outliers using Z-score or IQR methods and consider capping or removing extreme values.",
                "severity": "medium",
            })

        if constants:
            suggestions.append({
                "issue": f"Constant columns found: {', '.join(c['column'] for c in constants)}",
                "suggestion": "Consider dropping constant columns as they add no predictive value.",
                "severity": "low",
            })

        return suggestions
