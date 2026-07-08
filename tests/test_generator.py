"""单元测试 - 数据生成器"""
import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config import Settings
from src.data import DataGenerator


class TestDataGenerator:
    """测试数据生成器"""

    def setup_method(self):
        Settings._instance = None
        self.gen = DataGenerator(seed=42)

    def test_generate_returns_dataframe(self):
        df = self.gen.generate(n=1000)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1000

    def test_required_columns(self):
        df = self.gen.generate(n=100)
        required = ["order_id", "order_date", "category", "product", "region",
                     "city", "channel", "customer_id", "customer_type",
                     "unit_price", "quantity", "total_amount", "discount_rate",
                     "final_amount", "payment_method", "order_status"]
        for col in required:
            assert col in df.columns, f"缺少列: {col}"

    def test_order_ids_unique(self):
        df = self.gen.generate(n=5000)
        assert df["order_id"].nunique() == 5000

    def test_has_missing_values(self):
        df = self.gen.generate(n=10000)
        total_missing = df.isnull().sum().sum()
        assert total_missing > 0, "应包含缺失值"

    def test_has_outliers(self):
        df = self.gen.generate(n=10000)
        neg_qty = (df["quantity"] < 0).sum()
        assert neg_qty > 0, "应包含负数量异常值"

    def test_categories_in_expected_set(self):
        df = self.gen.generate(n=1000)
        expected = set(DataGenerator.__init__.__code__.co_consts)
        valid_cats = {"电子产品", "服装鞋帽", "食品饮料", "家居日用", "美妆个护", "图书文具", "运动户外"}
        actual_cats = set(df["category"].dropna().unique())
        assert actual_cats.issubset(valid_cats | {np.nan})

    def test_date_range(self):
        df = self.gen.generate(n=1000)
        dates = pd.to_datetime(df["order_date"])
        assert dates.min() >= pd.Timestamp("2023-01-01")
        assert dates.max() <= pd.Timestamp("2025-12-31 23:59:59")

    def test_amounts_positive(self):
        df = self.gen.generate(n=1000)
        assert (df["total_amount"].dropna() > 0).all()
