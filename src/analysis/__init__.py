"""数据分析模块 - 生成可视化图表和PDF报告"""
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from pathlib import Path
from typing import Dict, List, Tuple

from src.config import get_settings
from src.utils import get_logger

logger = get_logger("analysis")


class RetailAnalyzer:
    """零售销售分析器"""

    def __init__(self, df: pd.DataFrame, forecast_df: pd.DataFrame = None, segment_df: pd.DataFrame = None):
        self.df = df.copy()
        self.completed = df[df["order_status"] == "已完成"].copy()
        self.forecast_df = forecast_df
        self.segment_df = segment_df
        self.figures: Dict[str, go.Figure] = {}
        self.insights: List[Dict] = []

    def run_full_analysis(self) -> Tuple[Dict, List]:
        logger.info("开始数据分析...")
        self._analyze_daily_trends()
        self._analyze_weekend_peak()
        self._analyze_category_contribution()
        self._analyze_category_decline()
        self._analyze_regional_sales()
        self._analyze_repurchase()
        self._analyze_channel_performance()
        self._analyze_forecast()
        self._analyze_customer_segments()
        self._generate_insights()
        logger.info(f"分析完成: {len(self.figures)} 张图表, {len(self.insights)} 条洞察")
        return self.figures, self.insights

    def _analyze_daily_trends(self):
        daily = self.completed.groupby(self.completed["order_date"].dt.date).agg(
            revenue=("final_amount", "sum"), orders=("order_id", "count"),
        ).reset_index()
        daily.rename(columns={"order_date": "date"}, inplace=True)
        daily["ma7"] = daily["revenue"].rolling(7).mean()
        daily["ma30"] = daily["revenue"].rolling(30).mean()

        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                            subplot_titles=("日销售额趋势", "日订单量"), row_heights=[0.6, 0.4])
        fig.add_trace(go.Scatter(x=daily["date"], y=daily["revenue"], mode="lines",
                                  name="日销售额", line=dict(color="#636EFA", width=1), opacity=0.5), row=1, col=1)
        fig.add_trace(go.Scatter(x=daily["date"], y=daily["ma7"], mode="lines",
                                  name="7日均线", line=dict(color="#EF553B", width=2)), row=1, col=1)
        fig.add_trace(go.Scatter(x=daily["date"], y=daily["ma30"], mode="lines",
                                  name="30日均线", line=dict(color="#00CC96", width=2)), row=1, col=1)
        fig.add_trace(go.Bar(x=daily["date"], y=daily["orders"], name="日订单量",
                              marker_color="#AB63FA", opacity=0.6), row=2, col=1)
        fig.update_layout(title="日销售额趋势分析", height=700, template="plotly_white",
                          legend=dict(orientation="h", yanchor="bottom", y=1.02))
        self.figures["daily_trends"] = fig

    def _analyze_weekend_peak(self):
        day_names = {0: "周一", 1: "周二", 2: "周三", 3: "周四", 4: "周五", 5: "周六", 6: "周日"}
        weekday = self.completed.groupby("day_of_week").agg(
            revenue=("final_amount", "sum"), orders=("order_id", "count"),
        ).reset_index()
        total_weeks = max(1, (self.completed["order_date"].max() - self.completed["order_date"].min()).days / 7)
        weekday["avg_revenue"] = weekday["revenue"] / total_weeks
        weekday["day_name"] = weekday["day_of_week"].map(day_names)
        colors = ["#636EFA"] * 5 + ["#EF553B", "#EF553B"]

        fig = go.Figure()
        fig.add_trace(go.Bar(x=weekday["day_name"], y=weekday["avg_revenue"],
                              marker_color=colors,
                              text=weekday["avg_revenue"].round(0).astype(int).apply(lambda x: f"¥{x:,}"),
                              textposition="outside"))
        fig.update_layout(title="周末 vs 工作日销售对比", height=400, template="plotly_white",
                          yaxis_title="日均销售额")
        self.figures["weekend_peak"] = fig

    def _analyze_category_contribution(self):
        cat = self.completed.groupby("category")["final_amount"].sum().reset_index()
        cat = cat.sort_values("final_amount", ascending=True)
        fig = make_subplots(rows=1, cols=2, specs=[[{"type": "bar"}, {"type": "pie"}]],
                            subplot_titles=("品类销售额排名", "品类收入占比"))
        fig.add_trace(go.Bar(y=cat["category"], x=cat["final_amount"], orientation="h",
                              marker_color=px.colors.qualitative.Set3[:len(cat)],
                              text=cat["final_amount"].apply(lambda x: f"{x/1e6:.1f}M"),
                              textposition="outside"), row=1, col=1)
        fig.add_trace(go.Pie(labels=cat["category"], values=cat["final_amount"], hole=0.4,
                              textinfo="percent+label"), row=1, col=2)
        fig.update_layout(title="品类贡献度分析", height=500, template="plotly_white", showlegend=False)
        self.figures["category_contribution"] = fig

    def _analyze_category_decline(self):
        cat_monthly = self.completed.groupby(["year_month", "category"])["final_amount"].sum().reset_index()
        categories = sorted(cat_monthly["category"].unique())
        colors = px.colors.qualitative.Bold[:len(categories)]
        fig = go.Figure()
        for cat, color in zip(categories, colors):
            d = cat_monthly[cat_monthly["category"] == cat]
            fig.add_trace(go.Scatter(x=d["year_month"], y=d["final_amount"],
                                      mode="lines+markers", name=cat, line=dict(color=color, width=2)))
        fig.update_layout(title="各品类月度销售趋势（品类下滑预警）", height=550, template="plotly_white",
                          xaxis_title="月份", yaxis_title="销售额",
                          legend=dict(orientation="h", yanchor="bottom", y=-0.2))
        self.figures["category_decline"] = fig

    def _analyze_regional_sales(self):
        region = self.completed.groupby("region").agg(
            revenue=("final_amount", "sum"), orders=("order_id", "count"),
            customers=("customer_id", "nunique"), avg_order=("final_amount", "mean"),
        ).reset_index().sort_values("revenue", ascending=False)
        fig = make_subplots(rows=2, cols=2,
                            subplot_titles=("区域销售额", "区域订单量", "区域客户数", "区域客单价"))
        color_schemes = ["Blues_r", "Greens_r", "Oranges_r", "Reds_r"]
        for i, (col, scheme) in enumerate(zip(["revenue", "orders", "customers", "avg_order"], color_schemes)):
            colors_list = getattr(px.colors.sequential, scheme)[:len(region)]
            fig.add_trace(go.Bar(x=region["region"], y=region[col], marker_color=colors_list),
                          row=i//2+1, col=i%2+1)
        fig.update_layout(title="区域销售多维度分析", height=700, template="plotly_white", showlegend=False)
        self.figures["regional_sales"] = fig

    def _analyze_repurchase(self):
        cust = self.completed.groupby(["customer_id", "customer_type"])["order_id"].count().reset_index()
        type_stats = cust.groupby("customer_type").agg(
            total=("customer_id", "count"),
            repeat=("order_id", lambda x: (x > 1).sum()),
        ).reset_index()
        type_stats["rate"] = (type_stats["repeat"] / type_stats["total"] * 100).round(1)
        colors = {"VIP": "#00CC96", "老客": "#636EFA", "新客": "#EF553B"}
        fig = go.Figure()
        fig.add_trace(go.Bar(x=type_stats["customer_type"], y=type_stats["rate"],
                              marker_color=[colors.get(t, "#AB63FA") for t in type_stats["customer_type"]],
                              text=type_stats["rate"].astype(str) + "%", textposition="outside"))
        fig.update_layout(title="客户复购率分析", height=400, template="plotly_white", yaxis_title="复购率(%)")
        self.figures["repurchase"] = fig

    def _analyze_channel_performance(self):
        ch = self.completed.groupby("channel").agg(
            revenue=("final_amount", "sum"), orders=("order_id", "count"),
        ).reset_index().sort_values("revenue", ascending=False)
        fig = go.Figure(go.Bar(x=ch["channel"], y=ch["revenue"], marker_color="#636EFA"))
        fig.update_layout(title="各渠道销售额对比", height=400, template="plotly_white")
        self.figures["channel_revenue"] = fig

    def _analyze_forecast(self):
        if self.forecast_df is None:
            return
        fig = go.Figure()
        actual = self.forecast_df.dropna(subset=["actual"])
        forecast = self.forecast_df[self.forecast_df["is_forecast"]]
        fig.add_trace(go.Scatter(x=actual["ds"], y=actual["actual"], mode="lines",
                                  name="历史数据", line=dict(color="#636EFA", width=1), opacity=0.6))
        fig.add_trace(go.Scatter(x=self.forecast_df["ds"], y=self.forecast_df["predicted"], mode="lines",
                                  name="模型拟合+预测", line=dict(color="#EF553B", width=2, dash="dash")))
        # 标记预测区域
        if len(forecast) > 0:
            fig.add_vrect(x0=forecast["ds"].iloc[0], x1=forecast["ds"].iloc[-1],
                           fillcolor="rgba(239,85,59,0.1)", line_width=0,
                           annotation_text="预测区间", annotation_position="top left")
        fig.update_layout(title="销售预测（Holt-Winters指数平滑）", height=500, template="plotly_white",
                          xaxis_title="日期", yaxis_title="日销售额")
        self.figures["forecast"] = fig

    def _analyze_customer_segments(self):
        if self.segment_df is None:
            return
        summary = self.segment_df.groupby("segment").agg(
            count=("customer_id", "count"), avg_monetary=("monetary", "mean"),
        ).reset_index()
        fig = make_subplots(rows=1, cols=2, specs=[[{"type": "pie"}, {"type": "xy"}]],
                            subplot_titles=("客户分群人数", "分群平均消费"))
        fig.add_trace(go.Pie(labels=summary["segment"], values=summary["count"], hole=0.4), row=1, col=1)
        fig.add_trace(go.Bar(x=summary["segment"], y=summary["avg_monetary"], marker_color="#00CC96"), row=1, col=2)
        fig.update_layout(title="客户RFM聚类分群", height=450, template="plotly_white")
        self.figures["customer_segments"] = fig

    def _generate_insights(self):
        weekend = self.completed[self.completed["is_weekend"] == 1]
        weekday = self.completed[self.completed["is_weekend"] == 0]
        we_avg = weekend["final_amount"].sum() / max(1, weekend["order_date"].dt.date.nunique())
        wd_avg = weekday["final_amount"].sum() / max(1, weekday["order_date"].dt.date.nunique())
        uplift = (we_avg - wd_avg) / max(1, wd_avg) * 100

        self.insights = [
            {"type": "发现", "title": "周末销售高峰",
             "detail": f"周末日均销售额比工作日高 {uplift:.1f}%",
             "suggestion": "建议周五晚至周六集中投放促销资源，增加库存备货"},
            {"type": "建议", "title": "客户分群运营",
             "detail": "通过RFM聚类识别出高价值、高频、流失风险等客户群体",
             "suggestion": "对高价值客户推出VIP专属权益，对流失风险客户发送召回优惠券"},
            {"type": "发现", "title": "销售预测",
             "detail": f"基于Holt-Winters模型预测未来{self.forecast_df is not None and 90 or 0}天销售趋势",
             "suggestion": "根据预测结果提前调整库存和营销预算"},
        ]

    def save_figures(self, output_dir: str = None):
        if output_dir is None:
            output_dir = get_settings().paths.charts_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        for name, fig in self.figures.items():
            fig.write_html(str(Path(output_dir) / f"{name}.html"))
            try:
                fig.write_image(str(Path(output_dir) / f"{name}.png"), scale=2)
            except Exception:
                pass
        logger.info(f"图表已保存至: {output_dir}")

    def generate_pdf_report(self, output_path: str = None):
        if output_path is None:
            output_path = str(Path(get_settings().paths.reports_dir) / "analysis_report.pdf")
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.lib.colors import HexColor, white

            logger.info(f"开始生成PDF报告...")
            doc = SimpleDocTemplate(output_path, pagesize=A4,
                                     rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=2*cm, bottomMargin=2*cm)
            styles = getSampleStyleSheet()
            styles.add(ParagraphStyle(name="Title2", fontName="Helvetica-Bold", fontSize=20,
                                       alignment=1, spaceAfter=20, textColor=HexColor("#1a1a2e")))
            styles.add(ParagraphStyle(name="H2", fontName="Helvetica-Bold", fontSize=13,
                                       spaceBefore=12, textColor=HexColor("#16213e")))
            styles.add(ParagraphStyle(name="Body2", fontName="Helvetica", fontSize=10,
                                       spaceAfter=5, leading=14, textColor=HexColor("#333")))

            elements = [Spacer(1, 2*cm),
                        Paragraph("Retail Sales Analysis Report", styles["Title2"]),
                        Paragraph(f"Generated by Retail Dashboard v2.0", styles["Normal"]),
                        PageBreak(),
                        Paragraph("Key Insights", styles["H2"])]

            for ins in self.insights:
                elements.append(Paragraph(f"<b>[{ins['type']}] {ins['title']}</b>", styles["Body2"]))
                elements.append(Paragraph(f"  {ins['detail']}", styles["Body2"]))
                elements.append(Paragraph(f"  → {ins['suggestion']}", styles["Body2"]))
                elements.append(Spacer(1, 8))

            logger.info(f"构建PDF文档，共{len(elements)}个元素...")
            doc.build(elements)
            
            # 验证文件大小
            file_size = Path(output_path).stat().st_size
            logger.info(f"PDF报告已生成: {output_path} (大小: {file_size:,} 字节)")
            return output_path
        except Exception as e:
            import traceback
            logger.error(f"PDF生成失败: {e}")
            logger.error(traceback.format_exc())
            return None
