"""数据清洗模块"""
import pandas as pd
import numpy as np
import json
from pathlib import Path
from typing import Dict, Optional, Tuple

from src.config import get_settings
from src.utils import get_logger

logger = get_logger("data.cleaner")


class DataCleaner:
    """零售数据清洗器 - 处理缺失值、异常值，计算多维度指标"""

    def __init__(self):
        self.settings = get_settings()
        self.cfg = self.settings.cleaner
        self.metrics: Dict[str, pd.DataFrame] = {}
        self.report: Dict = {}

    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """执行完整的数据清洗流程"""
        logger.info("=" * 60)
        logger.info("开始数据清洗...")
        self.report["原始记录数"] = len(df)

        df = self._convert_types(df.copy())
        df = self._remove_duplicates(df)
        df = self._handle_missing(df)
        df = self._handle_outliers(df)
        df = self._add_time_features(df)
        self._compute_metrics(df)

        self.report["清洗后记录数"] = len(df)
        logger.info(f"清洗完成: {self.report['原始记录数']} → {len(df)} 条")
        return df

    def _convert_types(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("[1/6] 数据类型转换")
        if not pd.api.types.is_datetime64_any_dtype(df["order_date"]):
            df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
        for col in ["unit_price", "quantity", "total_amount", "discount_rate", "final_amount"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        for col in ["category", "product", "region", "city", "channel",
                     "customer_id", "customer_type", "payment_method", "order_status"]:
            if col in df.columns:
                df[col] = df[col].astype(str).replace("nan", np.nan)
        return df

    def _remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("[2/6] 去除重复记录")
        dup_count = df.duplicated(subset=["order_id"]).sum()
        if dup_count > 0:
            df = df.drop_duplicates(subset=["order_id"], keep="first")
            logger.info(f"  删除 {dup_count} 条重复订单")
        self.report["删除重复数"] = int(dup_count)
        return df

    def _handle_missing(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("[3/6] 处理缺失值")
        missing_before = df.isnull().sum().sum()

        # 单价: 品类中位数 → 全局中位数
        if df["unit_price"].isna().any():
            cat_median = df.groupby("category")["unit_price"].transform("median")
            df["unit_price"] = df["unit_price"].fillna(cat_median).fillna(df["unit_price"].median())

        if df["quantity"].isna().any():
            df["quantity"] = df["quantity"].fillna(self.cfg.default_quantity).astype(int)

        for col in ["category", "region", "city", "payment_method"]:
            if col in df.columns and df[col].isna().any():
                df[col] = df[col].fillna(self.cfg.unknown_fill)

        # 重算金额
        df["total_amount"] = np.round(df["unit_price"] * df["quantity"], 2)
        df["final_amount"] = np.round(df["total_amount"] * (1 - df["discount_rate"].clip(0, 1)), 2)

        missing_after = df.isnull().sum().sum()
        self.report["缺失值"] = {"处理前": int(missing_before), "处理后": int(missing_after)}
        logger.info(f"  缺失值: {missing_before} → {missing_after}")
        return df

    def _handle_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("[4/6] 处理异常值")
        count = 0

        neg = (df["quantity"] < 0).sum()
        if neg > 0:
            df.loc[df["quantity"] < 0, "quantity"] = df.loc[df["quantity"] < 0, "quantity"].abs()
            count += neg

        disc_out = ((df["discount_rate"] > 1) | (df["discount_rate"] < 0)).sum()
        if disc_out > 0:
            df["discount_rate"] = df["discount_rate"].clip(0, self.cfg.max_discount_rate)
            count += disc_out

        # IQR截断
        for cat in df["category"].unique():
            mask = df["category"] == cat
            prices = df.loc[mask, "unit_price"]
            Q1, Q3 = prices.quantile(0.25), prices.quantile(0.75)
            upper = Q3 + self.cfg.iqr_multiplier * (Q3 - Q1)
            outlier = mask & (df["unit_price"] > upper)
            count += outlier.sum()
            df.loc[outlier, "unit_price"] = upper

        df["total_amount"] = np.round(df["unit_price"] * df["quantity"], 2)
        df["final_amount"] = np.round(df["total_amount"] * (1 - df["discount_rate"]), 2)

        self.report["异常值处理数"] = int(count)
        logger.info(f"  处理 {count} 条异常值")
        return df

    def _add_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("[5/6] 派生时间特征")
        df["year"] = df["order_date"].dt.year
        df["month"] = df["order_date"].dt.month
        df["quarter"] = df["order_date"].dt.quarter
        df["week"] = df["order_date"].dt.isocalendar().week.astype(int)
        df["day_of_week"] = df["order_date"].dt.dayofweek
        df["day_name"] = df["order_date"].dt.day_name()
        df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
        df["year_month"] = df["order_date"].dt.to_period("M").astype(str)
        df["year_week"] = df["order_date"].dt.strftime("%Y-W%U")
        return df

    def _compute_metrics(self, df: pd.DataFrame):
        logger.info("[6/6] 计算多维度业务指标")
        completed = df[df["order_status"] == "已完成"].copy()

        # 日销售额
        daily = completed.groupby(completed["order_date"].dt.date).agg(
            revenue=("final_amount", "sum"),
            orders=("order_id", "count"),
            customers=("customer_id", "nunique"),
            avg_order_value=("final_amount", "mean"),
        ).reset_index()
        daily.rename(columns={"order_date": "date"}, inplace=True)
        self.metrics["daily_sales"] = daily

        # 品类贡献度
        cat = completed.groupby("category").agg(
            revenue=("final_amount", "sum"), orders=("order_id", "count"),
            avg_price=("unit_price", "mean"), customers=("customer_id", "nunique"),
        ).reset_index()
        total_rev = cat["revenue"].sum()
        cat["revenue_pct"] = (cat["revenue"] / total_rev * 100).round(2)
        self.metrics["category_contribution"] = cat.sort_values("revenue", ascending=False)

        # 复购率
        cust_orders = completed.groupby("customer_id").agg(
            order_count=("order_id", "count"), total_spent=("final_amount", "sum"),
        ).reset_index()
        self.metrics["customer_orders"] = cust_orders
        self.report["复购率"] = round((cust_orders["order_count"] > 1).sum() / len(cust_orders) * 100, 1)

        # 月度区域
        mr = completed.groupby(["year_month", "region"]).agg(
            revenue=("final_amount", "sum"), orders=("order_id", "count"),
        ).reset_index()
        self.metrics["monthly_region"] = mr

        logger.info(f"  复购率: {self.report['复购率']}%")
        logger.info(f"  日均销售额: {daily['revenue'].mean():,.0f} 元")

    def save(self, df: pd.DataFrame, output_dir: Optional[str] = None) -> str:
        if output_dir is None:
            output_dir = self.settings.paths.data_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        main_path = str(Path(output_dir) / "cleaned_retail_sales.csv")
        df.to_csv(main_path, index=False, encoding="utf-8-sig")

        for name, metric_df in self.metrics.items():
            metric_df.to_csv(str(Path(output_dir) / f"metrics_{name}.csv"), index=False, encoding="utf-8-sig")

        with open(str(Path(output_dir) / "cleaning_report.json"), "w", encoding="utf-8") as f:
            json.dump(self.report, f, ensure_ascii=False, indent=2)

        logger.info(f"清洗结果已保存至: {output_dir}")
        return main_path
