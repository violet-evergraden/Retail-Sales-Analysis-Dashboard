"""
零售销售分析仪表板 v2.0 - 主入口
Retail Sales Analysis Dashboard - Main Entry Point

Usage:
    python main.py                          # 运行全流程
    python main.py --service generate       # 仅生成数据
    python main.py --service clean          # 仅数据清洗
    python main.py --service analyze        # 分析+报告
    python main.py --service api            # 启动API服务
    python main.py --service dashboard      # 启动仪表板
    python main.py --service all            # 全流程(API+仪表板)
"""
import argparse
import sys
import pandas as pd
from pathlib import Path

from src.config import get_settings
from src.utils import setup_logger


def main():
    parser = argparse.ArgumentParser(description="零售销售分析仪表板 v2.0")
    parser.add_argument("--service", type=str, default="all",
                        choices=["generate", "clean", "analyze", "api", "dashboard", "all"],
                        help="运行服务: generate/clean/analyze/api/dashboard/all")
    parser.add_argument("--config", type=str, default="config.yaml", help="配置文件路径")
    parser.add_argument("--port", type=int, default=None, help="覆盖端口号")
    parser.add_argument("--records", type=int, default=None, help="覆盖数据条数")
    args = parser.parse_args()

    settings = get_settings(args.config)
    logger = setup_logger("main", settings.log_level, settings.log_format, settings.log_file)

    logger.info("=" * 60)
    logger.info(f"  {settings.project.name} v{settings.project.version}")
    logger.info("=" * 60)

    data_dir = Path(settings.paths.data_dir)
    raw_path = data_dir / "raw_retail_sales.csv"
    cleaned_path = data_dir / "cleaned_retail_sales.csv"

    df = None  # 清洗后的DataFrame
    forecast_df = None  # 预测结果
    segment_df = None  # 客户分群结果

    # ========== 数据生成 ==========
    if args.service in ("generate", "all"):
        logger.info("\n[STEP 1] 数据生成")
        from src.data import DataGenerator
        gen = DataGenerator()
        n = args.records or settings.data_generator.num_records
        raw_df = gen.generate(n=n)
        gen.save(raw_df)
        logger.info(f"数据生成完成: {len(raw_df)} 条")

    # ========== 数据清洗 ==========
    if args.service in ("clean", "analyze", "api", "dashboard", "all"):
        if not raw_path.exists():
            logger.info("原始数据不存在，自动生成...")
            from src.data import DataGenerator
            gen = DataGenerator()
            gen.save(gen.generate())

        logger.info("\n[STEP 2] 数据清洗")
        from src.data.cleaner import DataCleaner
        raw_df = pd.read_csv(raw_path, parse_dates=["order_date"])
        cleaner = DataCleaner()
        df = cleaner.clean(raw_df)
        cleaner.save(df)
        logger.info("数据清洗完成")

    # ========== 数据分析 + ML ==========
    if args.service in ("analyze", "dashboard", "all"):
        if df is None:
            if cleaned_path.exists():
                df = pd.read_csv(cleaned_path, parse_dates=["order_date"])
            else:
                logger.error("无清洗后数据，请先运行 --service clean")
                sys.exit(1)

        logger.info("\n[STEP 3] 数据分析 + 机器学习")

        # ML: 销售预测
        try:
            from src.models import SalesForecaster
            forecaster = SalesForecaster()
            forecast_df = forecaster.fit_predict(df)
            logger.info("销售预测完成")
        except Exception as e:
            logger.warning(f"销售预测跳过: {e}")

        # ML: 客户聚类
        try:
            from src.models import CustomerSegmenter
            segmenter = CustomerSegmenter()
            segment_df = segmenter.cluster(df)
            logger.info("客户聚类完成")
        except Exception as e:
            logger.warning(f"客户聚类跳过: {e}")

        # 分析 + 图表
        from src.analysis import RetailAnalyzer
        analyzer = RetailAnalyzer(df, forecast_df, segment_df)
        figures, insights = analyzer.run_full_analysis()
        analyzer.save_figures()

        try:
            analyzer.generate_pdf_report()
        except Exception as e:
            logger.warning(f"PDF报告生成失败: {e}")

        logger.info(f"分析完成: {len(figures)} 张图表, {len(insights)} 条洞察")

        for i, ins in enumerate(insights, 1):
            logger.info(f"  [{i}] [{ins['type']}] {ins['title']}: {ins['detail']}")

    # ========== API服务 ==========
    if args.service in ("api", "all"):
        logger.info("\n[STEP 4] 启动 API 服务")
        from src.api import app, load_data
        import uvicorn
        load_data()
        port = args.port or settings.api.port
        logger.info(f"  API文档: http://localhost:{port}/docs")
        if args.service == "api":
            uvicorn.run(app, host=settings.api.host, port=port)

    # ========== 仪表板 ==========
    if args.service in ("dashboard", "all"):
        if df is None:
            if cleaned_path.exists():
                df = pd.read_csv(cleaned_path, parse_dates=["order_date"])
            else:
                logger.error("无数据，请先运行全流程")
                sys.exit(1)

        logger.info("\n[STEP 5] 启动交互式仪表板")
        from src.dashboard import run_dashboard
        port = args.port or settings.dashboard.port
        logger.info(f"  仪表板: http://localhost:{port}")
        run_dashboard(df, forecast_df, port=port)


if __name__ == "__main__":
    main()
