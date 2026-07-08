"""
零售销售数据清洗模块
处理缺失值、异常值，计算多维度指标（日销售额、品类贡献度、复购率）
"""

import pandas as pd
import numpy as np
from scipy import stats
import os
import json
from datetime import datetime


class RetailDataCleaner:
    """零售数据清洗器"""

    def __init__(self, raw_data_path=None, df=None):
        """
        初始化清洗器
        :param raw_data_path: 原始CSV文件路径
        :param df: 或直接传入DataFrame
        """
        if df is not None:
            self.raw_df = df.copy()
        elif raw_data_path:
            self.raw_df = pd.read_csv(raw_data_path, parse_dates=["order_date"])
        else:
            raise ValueError("必须提供 raw_data_path 或 df 参数")

        self.cleaned_df = None
        self.cleaning_report = {}

    def clean(self):
        """执行完整的数据清洗流程"""
        print("=" * 60)
        print("开始数据清洗...")
        print("=" * 60)

        df = self.raw_df.copy()
        self.cleaning_report["原始记录数"] = len(df)

        # Step 1: 基础类型转换
        df = self._convert_types(df)

        # Step 2: 去除完全重复的记录
        df = self._remove_duplicates(df)

        # Step 3: 处理缺失值
        df = self._handle_missing_values(df)

        # Step 4: 处理异常值
        df = self._handle_outliers(df)

        # Step 5: 派生时间维度特征
        df = self._add_time_features(df)

        # Step 6: 计算多维度指标
        df = self._calculate_metrics(df)

        self.cleaned_df = df
        self.cleaning_report["清洗后记录数"] = len(df)

        print(f"\n清洗完成！原始 {self.cleaning_report['原始记录数']} 条 → 清洗后 {len(df)} 条")
        return df

    def _convert_types(self, df):
        """Step 1: 数据类型转换"""
        print("\n[1/6] 数据类型转换...")

        # 确保日期格式正确
        if not pd.api.types.is_datetime64_any_dtype(df["order_date"]):
            df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")

        # 数值类型确保
        for col in ["unit_price", "quantity", "total_amount", "discount_rate", "final_amount"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # 字符串类型确保
        for col in ["category", "product", "region", "city", "channel",
                     "customer_id", "customer_type", "payment_method", "order_status"]:
            if col in df.columns:
                df[col] = df[col].astype(str).replace("nan", np.nan)

        return df

    def _remove_duplicates(self, df):
        """Step 2: 去重"""
        print("\n[2/6] 去除重复记录...")

        dup_count = df.duplicated(subset=["order_id"]).sum()
        if dup_count > 0:
            print(f"  发现 {dup_count} 条重复订单，已删除")
            df = df.drop_duplicates(subset=["order_id"], keep="first")
        else:
            print("  无重复记录")

        self.cleaning_report["删除重复数"] = int(dup_count)
        return df

    def _handle_missing_values(self, df):
        """Step 3: 处理缺失值"""
        print("\n[3/6] 处理缺失值...")

        missing_before = df.isnull().sum()
        missing_before = missing_before[missing_before > 0]

        # 3.1 unit_price 缺失：用同品类中位数填充
        if df["unit_price"].isna().any():
            category_median_price = df.groupby("category")["unit_price"].transform("median")
            global_median_price = df["unit_price"].median()
            df["unit_price"] = df["unit_price"].fillna(category_median_price).fillna(global_median_price)
            print(f"  unit_price: 使用品类中位数填充")

        # 3.2 quantity 缺失：填充为1（默认购买1件）
        if df["quantity"].isna().any():
            df["quantity"] = df["quantity"].fillna(1).astype(int)
            print(f"  quantity: 缺失值填充为1")

        # 3.3 category 缺失：用 "其他" 填充
        if df["category"].isna().any():
            df["category"] = df["category"].fillna("其他")
            print(f"  category: 缺失值填充为'其他'")

        # 3.4 region/city 缺失：用 "未知" 填充
        for col in ["region", "city"]:
            if df[col].isna().any():
                df[col] = df[col].fillna("未知")
                print(f"  {col}: 缺失值填充为'未知'")

        # 3.5 payment_method 缺失：用 "未知" 填充
        if df["payment_method"].isna().any():
            df["payment_method"] = df["payment_method"].fillna("未知")
            print(f"  payment_method: 缺失值填充为'未知'")

        # 3.6 重新计算金额字段
        df["total_amount"] = np.round(df["unit_price"] * df["quantity"], 2)
        df["final_amount"] = np.round(df["total_amount"] * (1 - df["discount_rate"].clip(0, 1)), 2)

        missing_after = df.isnull().sum().sum()
        self.cleaning_report["缺失值处理前"] = int(missing_before.sum()) if len(missing_before) > 0 else 0
        self.cleaning_report["缺失值处理后"] = int(missing_after)
        print(f"  缺失值: {self.cleaning_report['缺失值处理前']} → {self.cleaning_report['缺失值处理后']}")

        return df

    def _handle_outliers(self, df):
        """Step 4: 处理异常值"""
        print("\n[4/6] 处理异常值...")

        outlier_count = 0

        # 4.1 负数量（退货异常）→ 取绝对值
        neg_qty = (df["quantity"] < 0).sum()
        if neg_qty > 0:
            df.loc[df["quantity"] < 0, "quantity"] = df.loc[df["quantity"] < 0, "quantity"].abs()
            outlier_count += neg_qty
            print(f"  负数量: {neg_qty} 条已修正为正值")

        # 4.2 折扣率异常（>1或<0）→ 限制在[0, 0.5]
        disc_outlier = ((df["discount_rate"] > 1) | (df["discount_rate"] < 0)).sum()
        if disc_outlier > 0:
            df["discount_rate"] = df["discount_rate"].clip(0, 0.5)
            outlier_count += disc_outlier
            print(f"  折扣率异常: {disc_outlier} 条已修正到[0, 0.5]范围")

        # 4.3 单价异常高：使用IQR方法检测并截断
        for cat in df["category"].unique():
            mask = df["category"] == cat
            cat_prices = df.loc[mask, "unit_price"]

            Q1 = cat_prices.quantile(0.25)
            Q3 = cat_prices.quantile(0.75)
            IQR = Q3 - Q1
            upper_bound = Q3 + 3 * IQR  # 使用3倍IQR（宽松策略）

            outlier_mask = mask & (df["unit_price"] > upper_bound)
            n_outliers = outlier_mask.sum()
            if n_outliers > 0:
                df.loc[outlier_mask, "unit_price"] = upper_bound
                outlier_count += n_outliers

        print(f"  单价异常: {outlier_count} 条已截断至品类上界")

        # 4.4 重新计算金额
        df["total_amount"] = np.round(df["unit_price"] * df["quantity"], 2)
        df["final_amount"] = np.round(df["total_amount"] * (1 - df["discount_rate"]), 2)

        self.cleaning_report["异常值处理数"] = int(outlier_count)
        return df

    def _add_time_features(self, df):
        """Step 5: 派生时间维度特征"""
        print("\n[5/6] 派生时间特征...")

        df["year"] = df["order_date"].dt.year
        df["month"] = df["order_date"].dt.month
        df["quarter"] = df["order_date"].dt.quarter
        df["week"] = df["order_date"].dt.isocalendar().week.astype(int)
        df["day_of_week"] = df["order_date"].dt.dayofweek  # 0=Monday
        df["day_name"] = df["order_date"].dt.day_name()
        df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
        df["year_month"] = df["order_date"].dt.to_period("M").astype(str)
        df["year_week"] = df["order_date"].dt.strftime("%Y-W%U")

        print(f"  新增字段: year, month, quarter, week, day_of_week, day_name, is_weekend, year_month, year_week")
        return df

    def _calculate_metrics(self, df):
        """Step 6: 计算多维度指标"""
        print("\n[6/6] 计算多维度业务指标...")

        # 只分析已完成的订单
        completed = df[df["order_status"] == "已完成"].copy()

        # 6.1 日销售额
        daily_sales = completed.groupby(completed["order_date"].dt.date).agg(
            daily_revenue=("final_amount", "sum"),
            daily_orders=("order_id", "count"),
            daily_customers=("customer_id", "nunique"),
            avg_order_value=("final_amount", "mean"),
        ).reset_index()
        daily_sales.rename(columns={"order_date": "date"}, inplace=True)
        print(f"  日销售额: {len(daily_sales)} 天, 日均 {daily_sales['daily_revenue'].mean():,.0f} 元")

        # 6.2 品类贡献度
        category_contribution = completed.groupby("category").agg(
            revenue=("final_amount", "sum"),
            order_count=("order_id", "count"),
            avg_price=("unit_price", "mean"),
            customer_count=("customer_id", "nunique"),
        ).reset_index()
        total_revenue = category_contribution["revenue"].sum()
        category_contribution["revenue_pct"] = (category_contribution["revenue"] / total_revenue * 100).round(2)
        category_contribution = category_contribution.sort_values("revenue", ascending=False)
        print(f"  品类贡献度: Top3 = {', '.join(category_contribution.head(3)['category'].tolist())}")

        # 6.3 复购率
        customer_orders = completed.groupby("customer_id").agg(
            order_count=("order_id", "count"),
            total_spent=("final_amount", "sum"),
            first_order=("order_date", "min"),
            last_order=("order_date", "max"),
        ).reset_index()

        repeat_customers = (customer_orders["order_count"] > 1).sum()
        total_customers = len(customer_orders)
        repurchase_rate = repeat_customers / total_customers * 100

        # 按客户类型统计复购率
        repurchase_by_type = completed.groupby("customer_type")["customer_id"].apply(
            lambda x: (x.value_counts() > 1).sum() / x.nunique() * 100
        ).reset_index()
        repurchase_by_type.columns = ["customer_type", "repurchase_rate"]

        print(f"  复购率: 总体 {repurchase_rate:.1f}% ({repeat_customers}/{total_customers})")
        for _, row in repurchase_by_type.iterrows():
            print(f"    {row['customer_type']}: {row['repurchase_rate']:.1f}%")

        # 6.4 月度/区域销售汇总
        monthly_region = completed.groupby(["year_month", "region"]).agg(
            revenue=("final_amount", "sum"),
            orders=("order_id", "count"),
            customers=("customer_id", "nunique"),
        ).reset_index()

        # 将指标附加到df
        self.metrics = {
            "daily_sales": daily_sales,
            "category_contribution": category_contribution,
            "customer_orders": customer_orders,
            "repurchase_rate": repurchase_rate,
            "repurchase_by_type": repurchase_by_type,
            "monthly_region": monthly_region,
        }

        return df

    def save_cleaned_data(self, output_dir=None):
        """保存清洗后的数据"""
        if self.cleaned_df is None:
            raise ValueError("请先调用 clean() 方法")

        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(__file__), "data")
        os.makedirs(output_dir, exist_ok=True)

        # 保存清洗后主表
        main_path = os.path.join(output_dir, "cleaned_retail_sales.csv")
        self.cleaned_df.to_csv(main_path, index=False, encoding="utf-8-sig")
        print(f"\n清洗后数据已保存: {main_path}")

        # 保存指标数据
        if hasattr(self, "metrics"):
            metrics_path = os.path.join(output_dir, "metrics_daily_sales.csv")
            self.metrics["daily_sales"].to_csv(metrics_path, index=False, encoding="utf-8-sig")

            cat_path = os.path.join(output_dir, "metrics_category_contribution.csv")
            self.metrics["category_contribution"].to_csv(cat_path, index=False, encoding="utf-8-sig")

            mr_path = os.path.join(output_dir, "metrics_monthly_region.csv")
            self.metrics["monthly_region"].to_csv(mr_path, index=False, encoding="utf-8-sig")

            # 保存清洗报告
            report_path = os.path.join(output_dir, "cleaning_report.json")
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(self.cleaning_report, f, ensure_ascii=False, indent=2)

            print(f"指标数据已保存至: {output_dir}")

        return main_path

    def get_summary(self):
        """获取清洗摘要"""
        return self.cleaning_report


if __name__ == "__main__":
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    raw_path = os.path.join(data_dir, "raw_retail_sales.csv")

    if not os.path.exists(raw_path):
        print("原始数据不存在，请先生成数据: python generate_data.py")
        from generate_data import generate_data
        generate_data()

    cleaner = RetailDataCleaner(raw_data_path=raw_path)
    cleaned_df = cleaner.clean()
    cleaner.save_cleaned_data()
    print("\n清洗报告:", cleaner.get_summary())
