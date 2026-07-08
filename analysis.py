"""
零售销售分析模块
基于Pandas进行关联分析和分组汇总，生成分析图表和PDF报告
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import os
from datetime import datetime


class RetailAnalyzer:
    """零售销售分析器"""

    def __init__(self, df):
        """
        :param df: 清洗后的DataFrame（需包含时间维度字段）
        """
        self.df = df.copy()
        self.completed = df[df["order_status"] == "已完成"].copy()
        self.figures = {}
        self.insights = []

    def run_full_analysis(self):
        """运行完整分析，生成所有图表"""
        print("开始数据分析...")
        print("=" * 60)

        self._analyze_daily_trends()
        self._analyze_weekend_peak()
        self._analyze_category_contribution()
        self._analyze_category_decline()
        self._analyze_regional_sales()
        self._analyze_repurchase()
        self._analyze_channel_performance()
        self._analyze_payment_methods()
        self._analyze_customer_segments()
        self._generate_insights()

        print(f"\n分析完成！共生成 {len(self.figures)} 张图表，{len(self.insights)} 条洞察")
        return self.figures, self.insights

    def _analyze_daily_trends(self):
        """分析日销售额趋势"""
        print("\n[1/9] 日销售额趋势分析...")

        daily = self.completed.groupby(self.completed["order_date"].dt.date).agg(
            revenue=("final_amount", "sum"),
            orders=("order_id", "count"),
            customers=("customer_id", "nunique"),
        ).reset_index()
        daily.rename(columns={"order_date": "date"}, inplace=True)

        # 计算7日和30日移动平均
        daily["ma7"] = daily["revenue"].rolling(7).mean()
        daily["ma30"] = daily["revenue"].rolling(30).mean()

        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            subplot_titles=("日销售额趋势", "日订单量与客户数"),
            row_heights=[0.6, 0.4],
        )

        fig.add_trace(go.Scatter(
            x=daily["date"], y=daily["revenue"],
            mode="lines", name="日销售额",
            line=dict(color="#636EFA", width=1), opacity=0.5,
        ), row=1, col=1)

        fig.add_trace(go.Scatter(
            x=daily["date"], y=daily["ma7"],
            mode="lines", name="7日均线",
            line=dict(color="#EF553B", width=2),
        ), row=1, col=1)

        fig.add_trace(go.Scatter(
            x=daily["date"], y=daily["ma30"],
            mode="lines", name="30日均线",
            line=dict(color="#00CC96", width=2),
        ), row=1, col=1)

        fig.add_trace(go.Bar(
            x=daily["date"], y=daily["orders"],
            name="日订单量", marker_color="#AB63FA", opacity=0.6,
        ), row=2, col=1)

        fig.add_trace(go.Scatter(
            x=daily["date"], y=daily["customers"],
            mode="lines", name="日客户数",
            line=dict(color="#FFA15A", width=2),
        ), row=2, col=1)

        fig.update_layout(
            title="日销售额趋势分析",
            height=700,
            template="plotly_white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )

        self.figures["daily_trends"] = fig
        print(f"  日均销售额: {daily['revenue'].mean():,.0f} 元")
        print(f"  最高日销售额: {daily['revenue'].max():,.0f} 元 ({daily.loc[daily['revenue'].idxmax(), 'date']})")

    def _analyze_weekend_peak(self):
        """发现周末销售高峰"""
        print("\n[2/9] 周末销售高峰分析...")

        # 按星期统计
        day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        weekday_stats = self.completed.groupby("day_of_week").agg(
            avg_revenue=("final_amount", "sum"),
            avg_orders=("order_id", "count"),
        ).reset_index()

        # 归一化到日均值
        total_days = (self.completed["order_date"].max() - self.completed["order_date"].min()).days / 7
        weekday_stats["avg_daily_revenue"] = weekday_stats["avg_revenue"] / total_days
        weekday_stats["avg_daily_orders"] = weekday_stats["avg_orders"] / total_days
        weekday_stats["day_name"] = weekday_stats["day_of_week"].map(
            dict(enumerate(day_names))
        )

        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=("各星期日均销售额", "各星期日均订单量"),
        )

        colors = ["#636EFA"] * 5 + ["#EF553B", "#EF553B"]  # 周末红色高亮

        fig.add_trace(go.Bar(
            x=weekday_stats["day_name"], y=weekday_stats["avg_daily_revenue"],
            marker_color=colors, name="日均销售额",
            text=weekday_stats["avg_daily_revenue"].round(0).astype(int).astype(str),
            textposition="outside",
        ), row=1, col=1)

        fig.add_trace(go.Bar(
            x=weekday_stats["day_name"], y=weekday_stats["avg_daily_orders"],
            marker_color=colors, name="日均订单量",
            text=weekday_stats["avg_daily_orders"].round(0).astype(int).astype(str),
            textposition="outside",
        ), row=1, col=2)

        fig.update_layout(
            title="周末 vs 工作日销售对比",
            height=450,
            template="plotly_white",
            showlegend=False,
        )

        self.figures["weekend_peak"] = fig

        # 计算周末提升幅度
        weekday_avg = weekday_stats[weekday_stats["day_of_week"] < 5]["avg_daily_revenue"].mean()
        weekend_avg = weekday_stats[weekday_stats["day_of_week"] >= 5]["avg_daily_revenue"].mean()
        uplift = (weekend_avg - weekday_avg) / weekday_avg * 100
        print(f"  工作日日均: {weekday_avg:,.0f} 元, 周末日均: {weekend_avg:,.0f} 元")
        print(f"  周末销售提升: {uplift:.1f}%")

    def _analyze_category_contribution(self):
        """品类贡献度分析"""
        print("\n[3/9] 品类贡献度分析...")

        cat_stats = self.completed.groupby("category").agg(
            revenue=("final_amount", "sum"),
            orders=("order_id", "count"),
            customers=("customer_id", "nunique"),
            avg_price=("unit_price", "mean"),
        ).reset_index()
        cat_stats["revenue_pct"] = cat_stats["revenue"] / cat_stats["revenue"].sum() * 100
        cat_stats = cat_stats.sort_values("revenue", ascending=True)

        fig = make_subplots(
            rows=1, cols=2,
            specs=[[{"type": "bar"}, {"type": "pie"}]],
            subplot_titles=("品类销售额排名", "品类收入占比"),
        )

        fig.add_trace(go.Bar(
            y=cat_stats["category"], x=cat_stats["revenue"],
            orientation="h", name="销售额",
            marker_color=px.colors.qualitative.Set3[:len(cat_stats)],
            text=cat_stats["revenue"].apply(lambda x: f"{x/1e6:.1f}M"),
            textposition="outside",
        ), row=1, col=1)

        fig.add_trace(go.Pie(
            labels=cat_stats["category"], values=cat_stats["revenue"],
            hole=0.4, textinfo="percent+label",
        ), row=1, col=2)

        fig.update_layout(
            title="品类贡献度分析",
            height=500,
            template="plotly_white",
            showlegend=False,
        )

        self.figures["category_contribution"] = fig
        top3 = cat_stats.nlargest(3, "revenue")
        print(f"  Top3品类: {', '.join(top3['category'].tolist())}")
        print(f"  Top3合计占比: {top3['revenue_pct'].sum():.1f}%")

    def _analyze_category_decline(self):
        """发现品类下滑问题"""
        print("\n[4/9] 品类下滑趋势分析...")

        cat_monthly = self.completed.groupby(["year_month", "category"])["final_amount"].sum().reset_index()
        cat_monthly = cat_monthly.sort_values(["category", "year_month"])

        # 计算各品类月环比
        cat_monthly["mom_change"] = cat_monthly.groupby("category")["final_amount"].pct_change() * 100

        # 找出连续下滑的品类
        fig = go.Figure()

        categories = sorted(cat_monthly["category"].unique())
        colors = px.colors.qualitative.Bold[:len(categories)]

        for cat, color in zip(categories, colors):
            cat_data = cat_monthly[cat_monthly["category"] == cat]
            fig.add_trace(go.Scatter(
                x=cat_data["year_month"], y=cat_data["final_amount"],
                mode="lines+markers", name=cat,
                line=dict(color=color, width=2),
            ))

        fig.update_layout(
            title="各品类月度销售趋势（发现下滑品类）",
            xaxis_title="月份", yaxis_title="销售额",
            height=550,
            template="plotly_white",
            legend=dict(orientation="h", yanchor="bottom", y=-0.2),
        )

        self.figures["category_decline"] = fig

        # 识别下滑品类
        latest_months = sorted(cat_monthly["year_month"].unique())[-3:]
        for cat in categories:
            cat_data = cat_monthly[cat_monthly["category"] == cat]
            recent = cat_data[cat_data["year_month"].isin(latest_months)]
            if len(recent) >= 2:
                changes = recent["mom_change"].dropna()
                if (changes < 0).all():
                    avg_decline = changes.mean()
                    print(f"  ⚠ 品类下滑预警: {cat} 近{len(changes)}月连续下降，平均环比 {avg_decline:.1f}%")

    def _analyze_regional_sales(self):
        """区域销售分析"""
        print("\n[5/9] 区域销售分析...")

        region_stats = self.completed.groupby("region").agg(
            revenue=("final_amount", "sum"),
            orders=("order_id", "count"),
            customers=("customer_id", "nunique"),
            avg_order=("final_amount", "mean"),
        ).reset_index().sort_values("revenue", ascending=False)

        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=("区域销售额", "区域订单量", "区域客户数", "区域客单价"),
        )

        fig.add_trace(go.Bar(
            x=region_stats["region"], y=region_stats["revenue"],
            marker_color=px.colors.sequential.Blues_r[:len(region_stats)],
            name="销售额",
        ), row=1, col=1)

        fig.add_trace(go.Bar(
            x=region_stats["region"], y=region_stats["orders"],
            marker_color=px.colors.sequential.Greens_r[:len(region_stats)],
            name="订单量",
        ), row=1, col=2)

        fig.add_trace(go.Bar(
            x=region_stats["region"], y=region_stats["customers"],
            marker_color=px.colors.sequential.Oranges_r[:len(region_stats)],
            name="客户数",
        ), row=2, col=1)

        fig.add_trace(go.Bar(
            x=region_stats["region"], y=region_stats["avg_order"],
            marker_color=px.colors.sequential.Reds_r[:len(region_stats)],
            name="客单价",
        ), row=2, col=2)

        fig.update_layout(
            title="区域销售多维度分析",
            height=700,
            template="plotly_white",
            showlegend=False,
        )

        self.figures["regional_sales"] = fig
        print(f"  销售最高区域: {region_stats.iloc[0]['region']} ({region_stats.iloc[0]['revenue']/1e6:.1f}M)")
        print(f"  销售最低区域: {region_stats.iloc[-1]['region']} ({region_stats.iloc[-1]['revenue']/1e6:.1f}M)")

    def _analyze_repurchase(self):
        """复购率分析"""
        print("\n[6/9] 复购率分析...")

        customer_orders = self.completed.groupby(["customer_id", "customer_type"]).agg(
            order_count=("order_id", "count"),
            total_spent=("final_amount", "sum"),
        ).reset_index()

        # 按客户类型统计
        type_stats = customer_orders.groupby("customer_type").agg(
            total_customers=("customer_id", "count"),
            repeat_customers=("order_count", lambda x: (x > 1).sum()),
            avg_orders=("order_count", "mean"),
            avg_spent=("total_spent", "mean"),
        ).reset_index()
        type_stats["repurchase_rate"] = (type_stats["repeat_customers"] / type_stats["total_customers"] * 100).round(1)

        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=("各客户类型复购率", "客户消费金额分布"),
        )

        fig.add_trace(go.Bar(
            x=type_stats["customer_type"], y=type_stats["repurchase_rate"],
            marker_color=["#636EFA", "#EF553B", "#00CC96"],
            text=type_stats["repurchase_rate"].astype(str) + "%",
            textposition="outside",
            name="复购率",
        ), row=1, col=1)

        for i, ct in enumerate(type_stats["customer_type"]):
            ct_data = customer_orders[customer_orders["customer_type"] == ct]
            fig.add_trace(go.Box(
                y=ct_data["total_spent"], name=ct,
                marker_color=["#636EFA", "#EF553B", "#00CC96"][i],
            ), row=1, col=2)

        fig.update_layout(
            title="客户复购率分析",
            height=450,
            template="plotly_white",
        )

        self.figures["repurchase"] = fig

        for _, row in type_stats.iterrows():
            print(f"  {row['customer_type']}: 复购率 {row['repurchase_rate']}%, "
                  f"人均消费 {row['avg_spent']:,.0f} 元")

    def _analyze_channel_performance(self):
        """渠道效果分析"""
        print("\n[7/9] 渠道效果分析...")

        channel_stats = self.completed.groupby("channel").agg(
            revenue=("final_amount", "sum"),
            orders=("order_id", "count"),
            avg_discount=("discount_rate", "mean"),
        ).reset_index().sort_values("revenue", ascending=False)

        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=channel_stats["channel"], y=channel_stats["revenue"],
            name="销售额", marker_color="#636EFA",
        ))

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=channel_stats["revenue"],
            y=channel_stats["avg_discount"] * 100,
            mode="markers+text",
            text=channel_stats["channel"],
            textposition="top center",
            marker=dict(size=channel_stats["orders"] / channel_stats["orders"].max() * 50,
                        color="#EF553B", opacity=0.7),
        ))
        fig2.update_layout(
            title="渠道销售额 vs 平均折扣率（气泡大小=订单量）",
            xaxis_title="销售额", yaxis_title="平均折扣率(%)",
            template="plotly_white", height=450,
        )

        self.figures["channel_revenue"] = fig
        self.figures["channel_scatter"] = fig2
        fig.update_layout(
            title="各渠道销售额对比",
            height=400,
            template="plotly_white",
        )

        print(f"  最优渠道: {channel_stats.iloc[0]['channel']} ({channel_stats.iloc[0]['revenue']/1e6:.1f}M)")

    def _analyze_payment_methods(self):
        """支付方式分析"""
        print("\n[8/9] 支付方式分析...")

        pay_stats = self.completed.groupby("payment_method").agg(
            revenue=("final_amount", "sum"),
            orders=("order_id", "count"),
        ).reset_index().sort_values("revenue", ascending=False)

        fig = go.Figure(go.Pie(
            labels=pay_stats["payment_method"],
            values=pay_stats["orders"],
            hole=0.4,
            textinfo="label+percent",
            marker=dict(colors=px.colors.qualitative.Pastel),
        ))
        fig.update_layout(
            title="支付方式订单占比",
            height=450,
            template="plotly_white",
        )

        self.figures["payment_methods"] = fig

    def _analyze_customer_segments(self):
        """客户细分分析"""
        print("\n[9/9] 客户细分分析...")

        monthly_new_old = self.completed.groupby(["year_month", "customer_type"])["customer_id"].nunique().reset_index()
        monthly_new_old.rename(columns={"customer_id": "customer_count"}, inplace=True)

        fig = px.area(
            monthly_new_old, x="year_month", y="customer_count",
            color="customer_type",
            title="各客户类型月度活跃客户数趋势",
            template="plotly_white",
            height=450,
        )

        self.figures["customer_segments"] = fig

    def _generate_insights(self):
        """生成数据洞察与建议"""
        print("\n生成数据洞察...")

        # 洞察1: 周末高峰
        weekend_data = self.completed[self.completed["is_weekend"] == 1]
        weekday_data = self.completed[self.completed["is_weekend"] == 0]
        weekend_avg = weekend_data["final_amount"].sum() / (weekend_data["order_date"].dt.date.nunique())
        weekday_avg = weekday_data["final_amount"].sum() / (weekday_data["order_date"].dt.date.nunique())
        uplift = (weekend_avg - weekday_avg) / weekday_avg * 100

        self.insights.append({
            "type": "发现",
            "title": "周末销售高峰",
            "detail": f"周末日均销售额比工作日高 {uplift:.1f}%。周六为销售最高峰日。",
            "suggestion": "建议在周五晚至周六集中投放促销资源，增加库存备货，优化物流配送能力。"
        })

        # 洞察2: 品类下滑
        cat_monthly = self.completed.groupby(["year_month", "category"])["final_amount"].sum().reset_index()
        months = sorted(cat_monthly["year_month"].unique())
        decline_cats = []
        for cat in cat_monthly["category"].unique():
            cat_data = cat_monthly[cat_monthly["category"] == cat].sort_values("year_month")
            if len(cat_data) >= 4:
                recent = cat_data.tail(4)
                if recent["final_amount"].is_monotonic_decreasing:
                    total_decline = (recent.iloc[-1]["final_amount"] - recent.iloc[0]["final_amount"]) / recent.iloc[0]["final_amount"] * 100
                    decline_cats.append((cat, total_decline))

        if decline_cats:
            decline_cats.sort(key=lambda x: x[1])
            cat_name, decline_pct = decline_cats[0]
            self.insights.append({
                "type": "预警",
                "title": f"品类下滑: {cat_name}",
                "detail": f"{cat_name}品类近4个月销售额持续下降，累计下滑 {abs(decline_pct):.1f}%。",
                "suggestion": f"建议对{cat_name}品类进行市场调研，分析下滑原因（竞品、季节性、质量问题），"
                             f"考虑加大促销力度、优化商品组合或调整库存策略。"
            })

        # 洞察3: 区域差异
        region_avg = self.completed.groupby("region")["final_amount"].mean()
        max_region = region_avg.idxmax()
        min_region = region_avg.idxmin()
        gap = (region_avg[max_region] - region_avg[min_region]) / region_avg[min_region] * 100

        self.insights.append({
            "type": "建议",
            "title": "区域销售差距",
            "detail": f"{max_region}客单价最高，{min_region}最低，差距达 {gap:.1f}%。",
            "suggestion": f"建议在{min_region}地区增加营销投入，分析{max_region}成功经验并复制推广。"
        })

        # 洞察4: VIP价值
        vip_data = self.completed[self.completed["customer_type"] == "VIP"]
        new_data = self.completed[self.completed["customer_type"] == "新客"]
        if len(vip_data) > 0 and len(new_data) > 0:
            vip_avg = vip_data.groupby("customer_id")["final_amount"].sum().mean()
            new_avg = new_data.groupby("customer_id")["final_amount"].sum().mean()
            ratio = vip_avg / new_avg

            self.insights.append({
                "type": "发现",
                "title": "VIP客户价值",
                "detail": f"VIP客户人均消费是新客的 {ratio:.1f} 倍。",
                "suggestion": "建议加强VIP客户维护计划，推出专属优惠和会员日活动，同时优化新客转化路径。"
            })

        for i, insight in enumerate(self.insights, 1):
            print(f"  [{insight['type']}] {insight['title']}: {insight['detail']}")

    def save_figures(self, output_dir=None):
        """保存所有图表为HTML"""
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(__file__), "output", "charts")
        os.makedirs(output_dir, exist_ok=True)

        for name, fig in self.figures.items():
            path = os.path.join(output_dir, f"{name}.html")
            fig.write_html(path)
        print(f"\n{len(self.figures)} 张图表已保存至: {output_dir}")

    def generate_pdf_report(self, output_path=None):
        """生成PDF分析报告"""
        if output_path is None:
            output_dir = os.path.join(os.path.dirname(__file__), "output")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, "retail_analysis_report.pdf")

        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch, cm
            from reportlab.lib.colors import HexColor
            from reportlab.lib import colors
            import tempfile
        except ImportError:
            print("需要安装 reportlab 才能生成PDF: pip install reportlab")
            return None

        print(f"\n正在生成PDF报告...")

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=1.5*cm, leftMargin=1.5*cm,
            topMargin=2*cm, bottomMargin=2*cm,
        )

        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name="CNTitle", fontName="Helvetica-Bold",
            fontSize=22, alignment=1, spaceAfter=20,
            textColor=HexColor("#1a1a2e"),
        ))
        styles.add(ParagraphStyle(
            name="CNHeading", fontName="Helvetica-Bold",
            fontSize=14, spaceBefore=15, spaceAfter=8,
            textColor=HexColor("#16213e"),
        ))
        styles.add(ParagraphStyle(
            name="CNBody", fontName="Helvetica",
            fontSize=10, spaceAfter=6, leading=16,
            textColor=HexColor("#333333"),
        ))
        styles.add(ParagraphStyle(
            name="CNInsight", fontName="Helvetica",
            fontSize=10, spaceAfter=4, leading=14,
            leftIndent=15, textColor=HexColor("#555555"),
        ))

        elements = []

        # 标题页
        elements.append(Spacer(1, 2*inch))
        elements.append(Paragraph("Retail Sales Analysis Report", styles["CNTitle"]))
        elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]))
        elements.append(Spacer(1, 0.5*inch))

        # 数据概览
        elements.append(Paragraph("1. Data Overview", styles["CNHeading"]))
        total_orders = len(self.completed)
        total_revenue = self.completed["final_amount"].sum()
        total_customers = self.completed["customer_id"].nunique()
        avg_order = self.completed["final_amount"].mean()

        overview_data = [
            ["Metric", "Value"],
            ["Total Orders", f"{total_orders:,}"],
            ["Total Revenue", f"¥{total_revenue:,.0f}"],
            ["Unique Customers", f"{total_customers:,}"],
            ["Avg Order Value", f"¥{avg_order:,.2f}"],
            ["Date Range", f"{self.completed['order_date'].min().strftime('%Y-%m-%d')} ~ {self.completed['order_date'].max().strftime('%Y-%m-%d')}"],
        ]

        table = Table(overview_data, colWidths=[4*cm, 8*cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1a1a2e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
            ("TOPPADDING", (0, 0), (-1, 0), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, HexColor("#f8f9fa")]),
        ]))
        elements.append(table)
        elements.append(PageBreak())

        # 关键洞察
        elements.append(Paragraph("2. Key Insights & Recommendations", styles["CNHeading"]))
        for i, insight in enumerate(self.insights, 1):
            tag = {"发现": "FINDING", "预警": "WARNING", "建议": "SUGGESTION"}.get(insight["type"], insight["type"])
            elements.append(Paragraph(
                f"<b>[{tag}] {insight['title']}</b>", styles["CNBody"]
            ))
            elements.append(Paragraph(insight["detail"], styles["CNInsight"]))
            elements.append(Paragraph(f"→ {insight['suggestion']}", styles["CNInsight"]))
            elements.append(Spacer(1, 8))

        elements.append(PageBreak())

        # 插入图表截图
        elements.append(Paragraph("3. Charts", styles["CNHeading"]))

        chart_dir = os.path.join(os.path.dirname(__file__), "output", "charts")
        if os.path.exists(chart_dir):
            for chart_file in sorted(os.listdir(chart_dir)):
                if chart_file.endswith(".png"):
                    img_path = os.path.join(chart_dir, chart_file)
                    try:
                        img = Image(img_path, width=17*cm, height=10*cm)
                        elements.append(Paragraph(chart_file.replace(".png", "").replace("_", " ").title(), styles["CNBody"]))
                        elements.append(img)
                        elements.append(Spacer(1, 15))
                    except Exception:
                        pass

        # 品类建议
        elements.append(PageBreak())
        elements.append(Paragraph("4. Optimization Recommendations", styles["CNHeading"]))
        recommendations = [
            "Weekend Promotion Strategy: Concentrate marketing resources on Friday evening through Saturday. Increase inventory for high-demand categories before weekends. Optimize logistics and delivery capacity.",
            "Declining Category Action Plan: Conduct market research on declining categories. Analyze competitor pricing and product mix. Consider bundled promotions with popular categories.",
            "Regional Expansion: Increase marketing investment in underperforming regions. Replicate successful strategies from top-performing regions. Consider region-specific product assortments.",
            "VIP Customer Retention: Launch exclusive VIP member days and early access to new products. Implement personalized recommendation engine. Create referral incentive program.",
            "Channel Optimization: Invest more in the highest-performing channel. Analyze discount strategies across channels for optimal ROI. Consider cross-channel promotions.",
        ]
        for rec in recommendations:
            elements.append(Paragraph(f"• {rec}", styles["CNBody"]))
            elements.append(Spacer(1, 4))

        doc.build(elements)
        print(f"PDF报告已生成: {output_path}")
        return output_path


def export_chart_images(figures, output_dir=None):
    """导出图表为PNG（用于PDF报告）"""
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), "output", "charts")
    os.makedirs(output_dir, exist_ok=True)

    for name, fig in figures.items():
        # 保存HTML
        fig.write_html(os.path.join(output_dir, f"{name}.html"))
        # 尝试保存PNG
        try:
            fig.write_image(os.path.join(output_dir, f"{name}.png"), scale=2)
        except Exception as e:
            print(f"  图表 {name} 无法导出PNG（需安装kaleido）: {e}")

    print(f"图表已导出至: {output_dir}")
