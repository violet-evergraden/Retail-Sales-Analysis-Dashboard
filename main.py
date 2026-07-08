"""
零售销售分析仪表板 - 主入口
Retail Sales Analysis Dashboard - Main Entry Point

功能:
1. 生成10万+条模拟零售订单数据（含缺失值和异常值）
2. 数据清洗（缺失值处理、异常值修正、多维度指标计算）
3. 运行Plotly Dash交互式仪表板
4. 执行数据分析并生成PDF报告
"""

import os
import sys
import argparse
import pandas as pd


def main():
    parser = argparse.ArgumentParser(description="零售销售分析仪表板")
    parser.add_argument("--step", type=str, default="all",
                        choices=["generate", "clean", "analyze", "dashboard", "all"],
                        help="运行步骤: generate(生成数据), clean(清洗), analyze(分析), dashboard(仪表板), all(全部)")
    parser.add_argument("--port", type=int, default=8050, help="仪表板端口号")
    parser.add_argument("--records", type=int, default=120000, help="生成数据条数")
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    raw_path = os.path.join(data_dir, "raw_retail_sales.csv")
    cleaned_path = os.path.join(data_dir, "cleaned_retail_sales.csv")

    print("""
╔══════════════════════════════════════════════════════════╗
║       📊 零售销售分析仪表板 (Retail Sales Dashboard)      ║
║                                                          ║
║  • 120,000+ 条零售订单数据                                ║
║  • 多维度分析: 时间/品类/区域/渠道/客户                    ║
║  • Plotly Dash 交互式仪表板                               ║
║  • 自动生成PDF分析报告                                    ║
╚══════════════════════════════════════════════════════════╝
    """)

    # ========== Step 1: 数据生成 ==========
    if args.step in ("generate", "all"):
        print("\n" + "=" * 60)
        print("STEP 1: 数据生成")
        print("=" * 60)

        from generate_data import generate_data, NUM_RECORDS
        raw_df = generate_data()
        print(f"\n✅ 数据生成完成: {len(raw_df)} 条记录")

    # ========== Step 2: 数据清洗 ==========
    if args.step in ("clean", "all"):
        print("\n" + "=" * 60)
        print("STEP 2: 数据清洗")
        print("=" * 60)

        if not os.path.exists(raw_path):
            print("原始数据不存在，正在生成...")
            from generate_data import generate_data
            generate_data()

        from clean_data import RetailDataCleaner
        cleaner = RetailDataCleaner(raw_data_path=raw_path)
        cleaned_df = cleaner.clean()
        cleaner.save_cleaned_data()

        print(f"\n✅ 数据清洗完成!")
        print(f"   清洗报告: {cleaner.get_summary()}")

    # ========== Step 3: 数据分析 ==========
    if args.step in ("analyze", "all"):
        print("\n" + "=" * 60)
        print("STEP 3: 数据分析与报告生成")
        print("=" * 60)

        if not os.path.exists(cleaned_path):
            print("清洗后数据不存在，正在执行清洗...")
            from clean_data import RetailDataCleaner
            cleaner = RetailDataCleaner(raw_data_path=raw_path)
            cleaned_df = cleaner.clean()
            cleaner.save_cleaned_data()

        df = pd.read_csv(cleaned_path, parse_dates=["order_date"])
        # 补充时间维度字段
        df["year"] = df["order_date"].dt.year
        df["month"] = df["order_date"].dt.month
        df["quarter"] = df["order_date"].dt.quarter
        df["day_of_week"] = df["order_date"].dt.dayofweek
        df["day_name"] = df["order_date"].dt.day_name()
        df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
        df["year_month"] = df["order_date"].dt.to_period("M").astype(str)

        from analysis import RetailAnalyzer, export_chart_images
        analyzer = RetailAnalyzer(df)
        figures, insights = analyzer.run_full_analysis()

        # 保存图表
        analyzer.save_figures()

        # 导出图表图片（用于PDF）
        export_chart_images(figures)

        # 生成PDF报告
        try:
            pdf_path = analyzer.generate_pdf_report()
            if pdf_path:
                print(f"\n✅ PDF报告已生成: {pdf_path}")
        except Exception as e:
            print(f"\n⚠ PDF生成失败（非必需）: {e}")

        print(f"\n✅ 数据分析完成! 共 {len(figures)} 张图表, {len(insights)} 条洞察")

        # 打印洞察
        print("\n📋 关键洞察与建议:")
        print("-" * 60)
        for i, insight in enumerate(insights, 1):
            print(f"\n  [{i}] [{insight['type']}] {insight['title']}")
            print(f"      {insight['detail']}")
            print(f"      → {insight['suggestion']}")

    # ========== Step 4: 启动仪表板 ==========
    if args.step in ("dashboard", "all"):
        print("\n" + "=" * 60)
        print("STEP 4: 启动交互式仪表板")
        print("=" * 60)

        if not os.path.exists(cleaned_path):
            print("清洗后数据不存在，正在执行前置步骤...")
            from generate_data import generate_data
            generate_data()
            from clean_data import RetailDataCleaner
            cleaner = RetailDataCleaner(raw_data_path=raw_path)
            cleaner.clean()
            cleaner.save_cleaned_data()

        df = pd.read_csv(cleaned_path, parse_dates=["order_date"])
        # 补充时间维度字段
        df["year"] = df["order_date"].dt.year
        df["month"] = df["order_date"].dt.month
        df["quarter"] = df["order_date"].dt.quarter
        df["day_of_week"] = df["order_date"].dt.dayofweek
        df["day_name"] = df["order_date"].dt.day_name()
        df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
        df["year_month"] = df["order_date"].dt.to_period("M").astype(str)

        from dashboard import run_dashboard
        run_dashboard(df, port=args.port)


if __name__ == "__main__":
    main()
