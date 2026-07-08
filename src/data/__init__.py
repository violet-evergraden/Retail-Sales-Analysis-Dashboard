"""数据生成模块"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import random

from src.config import get_settings
from src.utils import get_logger

logger = get_logger("data.generator")

# ============ 基础维度配置 ============
CATEGORIES = {
    "电子产品": ["手机", "笔记本电脑", "平板电脑", "耳机", "智能手表", "相机"],
    "服装鞋帽": ["男装", "女装", "童装", "运动鞋", "包包", "配饰"],
    "食品饮料": ["零食", "饮料", "生鲜", "乳制品", "酒水", "保健品"],
    "家居日用": ["家具", "厨具", "床品", "清洁用品", "收纳", "装饰"],
    "美妆个护": ["护肤品", "彩妆", "洗护发", "香水", "个护电器", "口腔护理"],
    "图书文具": ["小说", "教材", "文具", "办公用品", "艺术", "儿童读物"],
    "运动户外": ["健身器材", "户外装备", "球类", "骑行", "游泳", "瑜伽"],
}

REGIONS = {
    "华东": ["上海", "杭州", "南京", "苏州", "合肥"],
    "华南": ["广州", "深圳", "东莞", "佛山", "厦门"],
    "华北": ["北京", "天津", "石家庄", "太原", "济南"],
    "华中": ["武汉", "长沙", "郑州", "南昌"],
    "西南": ["成都", "重庆", "昆明", "贵阳"],
    "东北": ["沈阳", "大连", "哈尔滨", "长春"],
    "西北": ["西安", "兰州", "乌鲁木齐"],
}

CHANNELS = ["线上商城", "线下门店", "直播带货", "社交电商", "批发渠道"]
CUSTOMER_TYPES = ["新客", "老客", "VIP"]
PAYMENT_METHODS = ["微信支付", "支付宝", "银行卡", "信用卡", "现金", "花呗"]
ORDER_STATUSES = ["已完成", "已退款", "已取消", "配送中"]

PRICE_RANGES = {
    "电子产品": (200, 15000), "服装鞋帽": (50, 2000), "食品饮料": (5, 500),
    "家居日用": (20, 5000), "美妆个护": (30, 1500), "图书文具": (10, 300),
    "运动户外": (50, 3000),
}

WEEKDAY_MULTIPLIER = {0: 1.0, 1: 0.95, 2: 0.9, 3: 1.05, 4: 1.3, 5: 1.6, 6: 1.5}

CATEGORY_MONTHLY_TREND = {
    "电子产品": [1.2, 0.8, 0.9, 1.0, 1.0, 1.3, 0.9, 0.85, 1.0, 1.1, 1.8, 1.5],
    "服装鞋帽": [0.8, 0.7, 1.2, 1.3, 1.1, 1.5, 0.8, 0.9, 1.2, 1.3, 1.6, 1.0],
    "食品饮料": [1.3, 1.4, 1.0, 1.0, 1.1, 1.2, 1.3, 1.2, 1.0, 1.0, 1.1, 1.5],
    "家居日用": [1.0, 0.9, 1.3, 1.2, 1.1, 1.0, 0.9, 0.9, 1.0, 1.1, 1.4, 1.0],
    "美妆个护": [1.0, 1.1, 1.4, 1.2, 1.3, 1.5, 0.9, 0.8, 1.0, 1.0, 1.6, 1.1],
    "图书文具": [0.9, 1.5, 1.2, 1.0, 0.9, 0.7, 0.6, 1.3, 1.4, 1.0, 1.1, 0.8],
    "运动户外": [0.7, 0.8, 1.1, 1.3, 1.5, 1.4, 1.2, 1.1, 1.0, 0.9, 0.7, 0.6],
}


class DataGenerator:
    """零售销售数据生成器"""

    def __init__(self, seed: int = 42):
        self.settings = get_settings()
        self.seed = seed
        np.random.seed(seed)
        random.seed(seed)

    def generate(self, n: Optional[int] = None) -> pd.DataFrame:
        """生成完整的零售销售数据集"""
        n = n or self.settings.data_generator.num_records
        logger.info(f"开始生成 {n} 条零售订单数据...")

        df = pd.DataFrame({
            "order_id": [f"ORD-{i:08d}" for i in range(1, n + 1)],
            "order_date": self._generate_dates(n),
        })

        # 品类和商品
        categories, products = self._generate_categories(df["order_date"])
        df["category"] = categories
        df["product"] = products

        # 地区
        regions, cities = self._generate_regions(n)
        df["region"] = regions
        df["city"] = cities

        # 渠道和客户
        df["channel"] = np.random.choice(CHANNELS, n, p=[0.35, 0.25, 0.18, 0.12, 0.10])
        df["customer_type"] = np.random.choice(CUSTOMER_TYPES, n, p=[0.40, 0.45, 0.15])
        df["customer_id"] = self._generate_customer_ids(df["customer_type"])

        # 价格和数量
        df["unit_price"] = self._generate_prices(df["category"])
        df["quantity"] = np.random.choice([1,1,1,2,2,3,4,5], n, p=[0.35,0.20,0.10,0.15,0.08,0.06,0.04,0.02])
        df["total_amount"] = np.round(df["unit_price"] * df["quantity"], 2)

        # 折扣和实付
        df["discount_rate"] = np.random.choice([0.0,0.0,0.0,0.05,0.10,0.15,0.20,0.25,0.30,0.50], n)
        df["final_amount"] = np.round(df["total_amount"] * (1 - df["discount_rate"]), 2)

        # 支付方式和状态
        df["payment_method"] = np.random.choice(PAYMENT_METHODS, n, p=[0.35,0.30,0.10,0.10,0.05,0.10])
        df["order_status"] = np.random.choice(ORDER_STATUSES, n, p=[0.75,0.10,0.08,0.07])

        # 注入数据质量问题
        df = self._inject_missing_values(df)
        df = self._inject_outliers(df)

        # 打乱顺序
        df = df.sample(frac=1, random_state=self.seed).reset_index(drop=True)

        logger.info(f"数据生成完成: {len(df)} 条记录")
        return df

    def _generate_dates(self, n: int) -> list:
        start = datetime.strptime(self.settings.data_generator.start_date, "%Y-%m-%d")
        end = datetime.strptime(self.settings.data_generator.end_date, "%Y-%m-%d")
        total_days = (end - start).days + 1

        dates, weights = [], []
        for i in range(total_days):
            d = start + timedelta(days=i)
            dates.append(d)
            weights.append(WEEKDAY_MULTIPLIER[d.weekday()])

        weights = np.array(weights) / sum(weights)
        chosen = np.random.choice(dates, size=n, p=weights)
        hours = np.random.choice(range(8, 23), n)
        minutes = np.random.randint(0, 60, n)
        return [d.replace(hour=int(h), minute=int(m)) for d, h, m in zip(chosen, hours, minutes)]

    def _generate_categories(self, dates):
        cat_names = list(CATEGORIES.keys())
        base_weights = np.array([0.18, 0.20, 0.15, 0.12, 0.14, 0.08, 0.13])
        categories, products = [], []
        for dt in dates:
            month_idx = dt.month - 1
            trend = np.array([CATEGORY_MONTHLY_TREND[c][month_idx] for c in cat_names])
            w = base_weights * trend
            w /= w.sum()
            cat = np.random.choice(cat_names, p=w)
            categories.append(cat)
            products.append(random.choice(CATEGORIES[cat]))
        return categories, products

    def _generate_regions(self, n):
        region_names = list(REGIONS.keys())
        regions = np.random.choice(region_names, n, p=[0.25,0.22,0.20,0.12,0.10,0.06,0.05])
        cities = [random.choice(REGIONS[r]) for r in regions]
        return regions, cities

    def _generate_customer_ids(self, customer_types):
        vip_pool = [f"CUST-VIP-{i:04d}" for i in range(1, 501)]
        old_pool = [f"CUST-OLD-{i:05d}" for i in range(1, 5001)]
        new_pool = [f"CUST-NEW-{i:06d}" for i in range(1, 30001)]
        ids = []
        for ct in customer_types:
            if ct == "VIP": ids.append(random.choice(vip_pool))
            elif ct == "老客": ids.append(random.choice(old_pool))
            else: ids.append(random.choice(new_pool))
        return ids

    def _generate_prices(self, categories):
        prices = []
        for cat in categories:
            low, high = PRICE_RANGES.get(cat, (10, 1000))
            price = np.random.lognormal((np.log(low) + np.log(high)) / 2, 0.5)
            prices.append(round(max(low, min(high * 1.5, price)), 2))
        return np.array(prices)

    def _inject_missing_values(self, df):
        n = len(df)
        rates = self.settings.data_generator.missing_rate
        for col, rate in rates.items():
            mask = np.random.random(n) < rate
            df.loc[mask, col] = np.nan
        return df

    def _inject_outliers(self, df):
        n = len(df)
        rates = self.settings.data_generator.outlier_rate
        # 高价异常
        mask = np.random.random(n) < rates["high_price"]
        df.loc[mask, "unit_price"] *= np.random.uniform(10, 50, mask.sum())
        df.loc[mask, "total_amount"] = df.loc[mask, "unit_price"] * df.loc[mask, "quantity"]
        df.loc[mask, "final_amount"] = df.loc[mask, "total_amount"] * (1 - df.loc[mask, "discount_rate"])
        # 负数量
        mask = np.random.random(n) < rates["negative_quantity"]
        df.loc[mask, "quantity"] = -df.loc[mask, "quantity"]
        # 异常折扣
        mask = np.random.random(n) < rates["abnormal_discount"]
        df.loc[mask, "discount_rate"] = np.random.uniform(1.1, 2.0, mask.sum())
        return df

    def save(self, df: pd.DataFrame, path: Optional[str] = None) -> str:
        if path is None:
            path = str(Path(self.settings.paths.data_dir) / "raw_retail_sales.csv")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False, encoding="utf-8-sig")
        logger.info(f"数据已保存: {path}")
        return path
