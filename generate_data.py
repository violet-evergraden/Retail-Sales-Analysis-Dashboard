"""
零售销售数据生成器
生成10万+条模拟零售订单数据，包含缺失值和异常值以模拟真实场景
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import random

# 设置随机种子保证可复现
np.random.seed(42)
random.seed(42)

# ============ 基础维度配置 ============
NUM_RECORDS = 120_000  # 生成12万条数据

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

# ============ 价格区间配置（按品类）============
PRICE_RANGES = {
    "电子产品": (200, 15000),
    "服装鞋帽": (50, 2000),
    "食品饮料": (5, 500),
    "家居日用": (20, 5000),
    "美妆个护": (30, 1500),
    "图书文具": (10, 300),
    "运动户外": (50, 3000),
}

# 周末销售高峰系数
WEEKDAY_MULTIPLIER = {0: 1.0, 1: 0.95, 2: 0.9, 3: 1.05, 4: 1.3, 5: 1.6, 6: 1.5}

# 品类月度趋势（模拟某些品类的季节性下滑）
CATEGORY_MONTHLY_TREND = {
    "电子产品": [1.2, 0.8, 0.9, 1.0, 1.0, 1.3, 0.9, 0.85, 1.0, 1.1, 1.8, 1.5],
    "服装鞋帽": [0.8, 0.7, 1.2, 1.3, 1.1, 1.5, 0.8, 0.9, 1.2, 1.3, 1.6, 1.0],
    "食品饮料": [1.3, 1.4, 1.0, 1.0, 1.1, 1.2, 1.3, 1.2, 1.0, 1.0, 1.1, 1.5],
    "家居日用": [1.0, 0.9, 1.3, 1.2, 1.1, 1.0, 0.9, 0.9, 1.0, 1.1, 1.4, 1.0],
    "美妆个护": [1.0, 1.1, 1.4, 1.2, 1.3, 1.5, 0.9, 0.8, 1.0, 1.0, 1.6, 1.1],
    "图书文具": [0.9, 1.5, 1.2, 1.0, 0.9, 0.7, 0.6, 1.3, 1.4, 1.0, 1.1, 0.8],
    "运动户外": [0.7, 0.8, 1.1, 1.3, 1.5, 1.4, 1.2, 1.1, 1.0, 0.9, 0.7, 0.6],
}


def generate_order_id(n):
    """生成订单编号"""
    return [f"ORD-{i:08d}" for i in range(1, n + 1)]


def generate_dates(n):
    """生成日期序列（2023-01-01 到 2025-12-31），周末密度更高"""
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2025, 12, 31)
    total_days = (end_date - start_date).days + 1

    # 按星期权重采样日期
    dates = []
    day_weights = []
    for i in range(total_days):
        d = start_date + timedelta(days=i)
        dates.append(d)
        day_weights.append(WEEKDAY_MULTIPLIER[d.weekday()])

    day_weights = np.array(day_weights)
    day_weights /= day_weights.sum()

    chosen_dates = np.random.choice(dates, size=n, p=day_weights)

    # 加入小时分钟
    hours = np.random.choice(range(8, 23), size=n, p=np.array(
        [0.02, 0.04, 0.06, 0.08, 0.10, 0.12, 0.10, 0.09, 0.08, 0.07, 0.06, 0.05, 0.04, 0.05, 0.04]
    ))
    minutes = np.random.randint(0, 60, size=n)

    return [d.replace(hour=int(h), minute=int(m)) for d, h, m in zip(chosen_dates, hours, minutes)]


def generate_data():
    """生成完整的零售销售数据集"""
    print(f"正在生成 {NUM_RECORDS} 条零售订单数据...")

    # 1. 订单编号
    order_ids = generate_order_id(NUM_RECORDS)

    # 2. 订单日期
    order_dates = generate_dates(NUM_RECORDS)

    # 3. 品类和商品（按月度趋势加权）
    category_names = list(CATEGORIES.keys())
    base_weights = np.array([0.18, 0.20, 0.15, 0.12, 0.14, 0.08, 0.13])

    categories = []
    products = []
    for dt in order_dates:
        month_idx = dt.month - 1
        # 结合月度趋势调整权重
        trend_weights = np.array([CATEGORY_MONTHLY_TREND[c][month_idx] for c in category_names])
        adjusted_weights = base_weights * trend_weights
        adjusted_weights /= adjusted_weights.sum()

        cat = np.random.choice(category_names, p=adjusted_weights)
        categories.append(cat)
        products.append(random.choice(CATEGORIES[cat]))

    # 4. 地区
    region_names = list(REGIONS.keys())
    region_weights = np.array([0.25, 0.22, 0.20, 0.12, 0.10, 0.06, 0.05])
    regions = np.random.choice(region_names, size=NUM_RECORDS, p=region_weights)
    cities = [random.choice(REGIONS[r]) for r in regions]

    # 5. 渠道
    channel_weights = np.array([0.35, 0.25, 0.18, 0.12, 0.10])
    channels = np.random.choice(CHANNELS, size=NUM_RECORDS, p=channel_weights)

    # 6. 客户类型（老客和VIP复购率更高）
    cust_type_weights = np.array([0.40, 0.45, 0.15])
    customer_types = np.random.choice(CUSTOMER_TYPES, size=NUM_RECORDS, p=cust_type_weights)

    # 7. 客户ID（模拟复购行为）
    # VIP客户少量但高频，老客中频，新客低频
    customer_ids = []
    vip_pool = [f"CUST-VIP-{i:04d}" for i in range(1, 501)]       # 500个VIP
    old_pool = [f"CUST-OLD-{i:05d}" for i in range(1, 5001)]       # 5000个老客
    new_pool = [f"CUST-NEW-{i:06d}" for i in range(1, 30001)]      # 30000个新客
    for ct in customer_types:
        if ct == "VIP":
            customer_ids.append(random.choice(vip_pool))
        elif ct == "老客":
            customer_ids.append(random.choice(old_pool))
        else:
            customer_ids.append(random.choice(new_pool))

    # 8. 单价和数量
    unit_prices = []
    quantities = []
    for cat in categories:
        low, high = PRICE_RANGES[cat]
        price = round(np.random.lognormal(
            mean=(np.log(low) + np.log(high)) / 2,
            sigma=0.5
        ), 2)
        price = max(low, min(high * 1.5, price))
        unit_prices.append(price)
        quantities.append(int(np.random.choice([1, 1, 1, 2, 2, 3, 4, 5], p=[0.35, 0.20, 0.10, 0.15, 0.08, 0.06, 0.04, 0.02])))

    unit_prices = np.array(unit_prices)
    quantities = np.array(quantities)
    total_amounts = np.round(unit_prices * quantities, 2)

    # 9. 折扣率
    discount_rates = np.random.choice(
        [0.0, 0.0, 0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.50],
        size=NUM_RECORDS
    )
    final_amounts = np.round(total_amounts * (1 - discount_rates), 2)

    # 10. 支付方式
    pay_methods = np.random.choice(
        ["微信支付", "支付宝", "银行卡", "信用卡", "现金", "花呗"],
        size=NUM_RECORDS,
        p=[0.35, 0.30, 0.10, 0.10, 0.05, 0.10]
    )

    # 11. 订单状态
    order_statuses = np.random.choice(
        ["已完成", "已完成", "已完成", "已完成", "已退款", "已取消", "配送中"],
        size=NUM_RECORDS,
        p=[0.70, 0.05, 0.03, 0.02, 0.08, 0.07, 0.05]
    )

    # 构建DataFrame
    df = pd.DataFrame({
        "order_id": order_ids,
        "order_date": order_dates,
        "category": categories,
        "product": products,
        "region": regions,
        "city": cities,
        "channel": channels,
        "customer_id": customer_ids,
        "customer_type": customer_types,
        "unit_price": unit_prices,
        "quantity": quantities,
        "total_amount": total_amounts,
        "discount_rate": discount_rates,
        "final_amount": final_amounts,
        "payment_method": pay_methods,
        "order_status": order_statuses,
    })

    # ============ 注入缺失值（模拟真实数据质量）============
    print("注入缺失值和异常值...")
    total_cells = NUM_RECORDS

    # 随机将约2%的unit_price设为NaN
    mask = np.random.random(NUM_RECORDS) < 0.02
    df.loc[mask, "unit_price"] = np.nan

    # 约1.5%的quantity设为NaN
    mask = np.random.random(NUM_RECORDS) < 0.015
    df.loc[mask, "quantity"] = np.nan

    # 约1%的category设为NaN
    mask = np.random.random(NUM_RECORDS) < 0.01
    df.loc[mask, "category"] = np.nan

    # 约0.5%的region设为NaN
    mask = np.random.random(NUM_RECORDS) < 0.005
    df.loc[mask, "region"] = np.nan

    # 约1%的payment_method设为NaN
    mask = np.random.random(NUM_RECORDS) < 0.01
    df.loc[mask, "payment_method"] = np.nan

    # ============ 注入异常值 ============
    # 约0.3%的订单金额异常高（如输入错误）
    outlier_mask = np.random.random(NUM_RECORDS) < 0.003
    df.loc[outlier_mask, "unit_price"] = df.loc[outlier_mask, "unit_price"] * np.random.uniform(10, 50, outlier_mask.sum())
    df.loc[outlier_mask, "total_amount"] = df.loc[outlier_mask, "unit_price"] * df.loc[outlier_mask, "quantity"]
    df.loc[outlier_mask, "final_amount"] = df.loc[outlier_mask, "total_amount"] * (1 - df.loc[outlier_mask, "discount_rate"])

    # 约0.2%的数量为负数（退货异常）
    neg_mask = np.random.random(NUM_RECORDS) < 0.002
    df.loc[neg_mask, "quantity"] = -df.loc[neg_mask, "quantity"]

    # 约0.1%的折扣率异常（>1）
    disc_mask = np.random.random(NUM_RECORDS) < 0.001
    df.loc[disc_mask, "discount_rate"] = np.random.uniform(1.1, 2.0, disc_mask.sum())

    # 打乱顺序
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)

    # 保存
    output_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "raw_retail_sales.csv")
    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"数据生成完成！共 {len(df)} 条记录")
    print(f"  - 时间范围: {df['order_date'].min()} ~ {df['order_date'].max()}")
    print(f"  - 品类数: {df['category'].nunique()}")
    print(f"  - 地区数: {df['region'].nunique()}")
    print(f"  - 客户数: {df['customer_id'].nunique()}")
    print(f"  - 缺失值统计:")
    for col in df.columns:
        missing = df[col].isna().sum()
        if missing > 0:
            print(f"    {col}: {missing} ({missing/len(df)*100:.2f}%)")
    print(f"数据已保存至: {output_path}")

    return df


if __name__ == "__main__":
    generate_data()
