"""机器学习模块 - 时间序列预测 + 客户聚类分群"""
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from pathlib import Path

from src.config import get_settings
from src.utils import get_logger

logger = get_logger("models")


class SalesForecaster:
    """销售预测器 - 基于时间序列模型预测未来销售趋势"""

    def __init__(self):
        self.settings = get_settings()
        self.model = None
        self.forecast_df = None

    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """准备时间序列数据"""
        completed = df[df["order_status"] == "已完成"].copy()
        ts = completed.groupby(completed["order_date"].dt.date).agg(
            y=("final_amount", "sum"),
            order_count=("order_id", "count"),
        ).reset_index()
        ts.rename(columns={"order_date": "ds"}, inplace=True)
        ts["ds"] = pd.to_datetime(ts["ds"])
        ts = ts.sort_values("ds").reset_index(drop=True)
        return ts

    def fit_predict_exponential(self, ts: pd.DataFrame) -> pd.DataFrame:
        """指数平滑预测（无需额外依赖）"""
        from scipy.optimize import minimize

        y = ts["y"].values
        n = len(y)
        forecast_days = self.settings.ml.forecast_days

        # Holt-Winters 三重指数平滑
        best_aic = float("inf")
        best_params = (0.3, 0.05, 0.1)

        def holt_winters(params):
            alpha, beta, gamma = params
            if not (0 < alpha < 1 and 0 < beta < 1 and 0 < gamma < 1):
                return np.full(n + forecast_days, np.nan), float("inf")

            period = 7  # 周季节性
            if n < 2 * period:
                return np.full(n + forecast_days, np.nan), float("inf")

            # 初始化
            level = np.mean(y[:period])
            trend = (np.mean(y[period:2*period]) - np.mean(y[:period])) / period
            seasonal = [y[i] - level for i in range(period)]

            fitted = np.zeros(n)
            for t in range(n):
                if t < period:
                    fitted[t] = level + trend + seasonal[t % period]
                else:
                    prev_level = level
                    level = alpha * (y[t] - seasonal[t % period]) + (1 - alpha) * (level + trend)
                    trend = beta * (level - prev_level) + (1 - beta) * trend
                    seasonal[t % period] = gamma * (y[t] - level) + (1 - gamma) * seasonal[t % period]
                    fitted[t] = level + trend + seasonal[t % period]

            # 预测
            forecast = np.zeros(forecast_days)
            for h in range(forecast_days):
                forecast[h] = level + (h + 1) * trend + seasonal[(n + h) % period]

            result = np.concatenate([fitted, np.maximum(forecast, 0)])
            sse = np.sum((y - fitted) ** 2)
            aic = n * np.log(sse / n + 1e-10) + 2 * 3
            return result, aic

        # 网格搜索最优参数
        for alpha in [0.1, 0.2, 0.3, 0.5]:
            for beta in [0.01, 0.05, 0.1]:
                for gamma in [0.05, 0.1, 0.2, 0.3]:
                    _, aic = holt_winters((alpha, beta, gamma))
                    if aic < best_aic:
                        best_aic = aic
                        best_params = (alpha, beta, gamma)

        result, _ = holt_winters(best_params)

        # 构建结果DataFrame
        last_date = ts["ds"].max()
        forecast_dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=forecast_days)
        all_dates = pd.concat([ts["ds"], pd.Series(forecast_dates)], ignore_index=True)

        self.forecast_df = pd.DataFrame({
            "ds": all_dates,
            "actual": np.concatenate([y, np.full(forecast_days, np.nan)]),
            "predicted": result[:n + forecast_days] if len(result) >= n + forecast_days else np.concatenate([result, np.full(max(0, n + forecast_days - len(result)), np.nan)]),
        })
        self.forecast_df["is_forecast"] = self.forecast_df["actual"].isna()

        logger.info(f"指数平滑预测完成: 参数 α={best_params[0]}, β={best_params[1]}, γ={best_params[2]}")
        logger.info(f"预测未来 {forecast_days} 天, 预计总销售额: ¥{self.forecast_df.loc[self.forecast_df['is_forecast'], 'predicted'].sum():,.0f}")
        return self.forecast_df

    def fit_predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """执行预测"""
        ts = self.prepare_data(df)
        return self.fit_predict_exponential(ts)


class CustomerSegmenter:
    """客户聚类分群 - 基于RFM模型"""

    def __init__(self):
        self.settings = get_settings()
        self.segments = None

    def compute_rfm(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算RFM特征"""
        completed = df[df["order_status"] == "已完成"].copy()
        snapshot_date = completed["order_date"].max()

        rfm = completed.groupby("customer_id").agg(
            recency=("order_date", lambda x: (snapshot_date - x.max()).days),
            frequency=("order_id", "count"),
            monetary=("final_amount", "sum"),
            customer_type=("customer_type", "first"),
        ).reset_index()

        # 分位数打分(1-5)
        for col in ["recency", "frequency", "monetary"]:
            rfm[f"{col}_score"] = pd.qcut(rfm[col], q=5, labels=False, duplicates="drop") + 1

        # Recency反转（越小越好）
        rfm["recency_score"] = 6 - rfm["recency_score"]

        return rfm

    def cluster(self, df: pd.DataFrame) -> pd.DataFrame:
        """K-Means聚类分群"""
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler

        rfm = self.compute_rfm(df)
        features = ["recency_score", "frequency_score", "monetary_score"]

        scaler = StandardScaler()
        X = scaler.fit_transform(rfm[features])

        n_clusters = self.settings.ml.n_clusters
        kmeans = KMeans(n_clusters=n_clusters, random_state=self.settings.ml.random_state, n_init=10)
        rfm["cluster"] = kmeans.fit_predict(X)

        # 聚类标签
        cluster_profiles = rfm.groupby("cluster").agg(
            avg_recency=("recency", "mean"),
            avg_frequency=("frequency", "mean"),
            avg_monetary=("monetary", "mean"),
            count=("customer_id", "count"),
        ).reset_index()

        # 根据特征给聚类命名
        labels = []
        for _, row in cluster_profiles.iterrows():
            if row["avg_monetary"] > cluster_profiles["avg_monetary"].quantile(0.7):
                labels.append("高价值客户")
            elif row["avg_frequency"] > cluster_profiles["avg_frequency"].quantile(0.7):
                labels.append("高频客户")
            elif row["avg_recency"] > cluster_profiles["avg_recency"].quantile(0.7):
                labels.append("流失风险")
            elif row["avg_frequency"] < cluster_profiles["avg_frequency"].quantile(0.3):
                labels.append("低活跃客户")
            else:
                labels.append("潜力客户")

        label_map = dict(zip(cluster_profiles["cluster"], labels))
        rfm["segment"] = rfm["cluster"].map(label_map)

        self.segments = rfm

        logger.info("客户聚类分群完成:")
        for seg in rfm["segment"].value_counts().items():
            logger.info(f"  {seg[0]}: {seg[1]} 人")

        return rfm

    def get_cluster_summary(self) -> pd.DataFrame:
        """获取聚类汇总"""
        if self.segments is None:
            return pd.DataFrame()
        return self.segments.groupby("segment").agg(
            customer_count=("customer_id", "count"),
            avg_recency_days=("recency", "mean"),
            avg_orders=("frequency", "mean"),
            avg_lifetime_value=("monetary", "mean"),
        ).reset_index().sort_values("avg_lifetime_value", ascending=False)
