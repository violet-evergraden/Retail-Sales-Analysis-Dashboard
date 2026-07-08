"""单元测试 - 数据清洗器"""
import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config import Settings
from src.data import DataGenerator
from src.data.cleaner import DataCleaner


class TestDataCleaner:
    """测试数据清洗器"""

    def setup_method(self):
        Settings._instance = None
        gen = DataGenerator(seed=42)
        self.raw_df = gen.generate(n=5000)
        self.cleaner = DataCleaner()

    def test_clean_returns_dataframe(self):
        df = self.cleaner.clean(self.raw_df)
        assert isinstance(df, pd.DataFrame)

    def test_no_missing_after_clean(self):
        df = self.cleaner.clean(self.raw_df)
        assert df.isnull().sum().sum() == 0

    def test_no_negative_quantity(self):
        df = self.cleaner.clean(self.raw_df)
        assert (df["quantity"] >= 0).all()

    def test_discount_rate_bounded(self):
        df = self.cleaner.clean(self.raw_df)
        assert (df["discount_rate"] >= 0).all()
        assert (df["discount_rate"] <= 0.5).all()

    def test_time_features_added(self):
        df = self.cleaner.clean(self.raw_df)
        time_cols = ["year", "month", "quarter", "day_of_week", "is_weekend", "year_month"]
        for col in time_cols:
            assert col in df.columns, f"缺少时间特征: {col}"

    def test_metrics_computed(self):
        df = self.cleaner.clean(self.raw_df)
        assert "daily_sales" in self.cleaner.metrics
        assert "category_contribution" in self.cleaner.metrics
        assert len(self.cleaner.metrics["daily_sales"]) > 0

    def test_report_generated(self):
        self.cleaner.clean(self.raw_df)
        assert "原始记录数" in self.cleaner.report
        assert "清洗后记录数" in self.cleaner.report
