"""
零售销售分析 - 动态交互式仪表板
基于 Plotly Dash 构建，支持按时间、品类、地区筛选
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import os
import webbrowser
from threading import Timer


def create_dashboard(df):
    """
    创建并启动交互式仪表板
    :param df: 清洗后的DataFrame
    """
    app = dash.Dash(
        __name__,
        external_stylesheets=[dbc.themes.FLATLY],
        title="零售销售分析仪表板",
    )

    # 获取筛选器选项
    categories = sorted(df["category"].dropna().unique().tolist())
    regions = sorted(df["region"].dropna().unique().tolist())
    channels = sorted(df["channel"].dropna().unique().tolist())
    years = sorted(df["year"].unique().tolist())

    # 只分析已完成订单
    completed = df[df["order_status"] == "已完成"].copy()

    # ============ 布局 ============
    app.layout = dbc.Container([
        # 标题栏
        dbc.Row([
            dbc.Col([
                html.H1("📊 零售销售分析仪表板", className="text-center my-3",
                         style={"color": "#1a1a2e", "fontWeight": "bold"}),
                html.P("Retail Sales Analysis Dashboard | 120,000+ Orders",
                        className="text-center text-muted mb-4"),
            ], width=12),
        ]),

        # KPI卡片行
        dbc.Row([
            dbc.Col(_create_kpi_card("总销售额", f"¥{completed['final_amount'].sum()/1e6:.1f}M", "💰"), width=3),
            dbc.Col(_create_kpi_card("总订单数", f"{len(completed):,}", "📦"), width=3),
            dbc.Col(_create_kpi_card("客户总数", f"{completed['customer_id'].nunique():,}", "👥"), width=3),
            dbc.Col(_create_kpi_card("客单价", f"¥{completed['final_amount'].mean():.0f}", "🏷️"), width=3),
        ], className="mb-4"),

        # 筛选器行
        dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("时间范围", className="fw-bold small"),
                        dcc.DatePickerRange(
                            id="date-range",
                            start_date=completed["order_date"].min().strftime("%Y-%m-%d"),
                            end_date=completed["order_date"].max().strftime("%Y-%m-%d"),
                            display_format="YYYY-MM-DD",
                            className="w-100",
                        ),
                    ], width=3),
                    dbc.Col([
                        html.Label("品类筛选", className="fw-bold small"),
                        dcc.Dropdown(
                            id="category-filter",
                            options=[{"label": "全部品类", "value": "all"}] +
                                     [{"label": c, "value": c} for c in categories],
                            value="all",
                            clearable=False,
                        ),
                    ], width=3),
                    dbc.Col([
                        html.Label("地区筛选", className="fw-bold small"),
                        dcc.Dropdown(
                            id="region-filter",
                            options=[{"label": "全部地区", "value": "all"}] +
                                     [{"label": r, "value": r} for r in regions],
                            value="all",
                            clearable=False,
                        ),
                    ], width=3),
                    dbc.Col([
                        html.Label("渠道筛选", className="fw-bold small"),
                        dcc.Dropdown(
                            id="channel-filter",
                            options=[{"label": "全部渠道", "value": "all"}] +
                                     [{"label": c, "value": c} for c in channels],
                            value="all",
                            clearable=False,
                        ),
                    ], width=3),
                ]),
            ]),
        ], className="mb-4 shadow-sm"),

        # 图表区域 - 第一行
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("📈 销售额趋势", className="fw-bold"),
                    dbc.CardBody(dcc.Graph(id="trend-chart", config={"displayModeBar": True})),
                ], className="shadow-sm"),
            ], width=12),
        ], className="mb-4"),

        # 图表区域 - 第二行
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("🗓️ 星期销售分布", className="fw-bold"),
                    dbc.CardBody(dcc.Graph(id="weekday-chart")),
                ], className="shadow-sm"),
            ], width=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("🏷️ 品类贡献度", className="fw-bold"),
                    dbc.CardBody(dcc.Graph(id="category-chart")),
                ], className="shadow-sm"),
            ], width=6),
        ], className="mb-4"),

        # 图表区域 - 第三行
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("🗺️ 区域销售分布", className="fw-bold"),
                    dbc.CardBody(dcc.Graph(id="region-chart")),
                ], className="shadow-sm"),
            ], width=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("🔄 复购率分析", className="fw-bold"),
                    dbc.CardBody(dcc.Graph(id="repurchase-chart")),
                ], className="shadow-sm"),
            ], width=6),
        ], className="mb-4"),

        # 图表区域 - 第四行
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("📊 月度品类趋势（品类下滑预警）", className="fw-bold"),
                    dbc.CardBody(dcc.Graph(id="category-trend-chart")),
                ], className="shadow-sm"),
            ], width=12),
        ], className="mb-4"),

        # 页脚
        dbc.Row([
            dbc.Col([
                html.Hr(),
                html.P("© 2025 Retail Sales Analysis Dashboard | Built with Plotly Dash",
                        className="text-center text-muted small"),
            ], width=12),
        ]),
    ], fluid=True, className="px-4 py-3")

    # ============ 回调函数 ============
    @app.callback(
        [Output("trend-chart", "figure"),
         Output("weekday-chart", "figure"),
         Output("category-chart", "figure"),
         Output("region-chart", "figure"),
         Output("repurchase-chart", "figure"),
         Output("category-trend-chart", "figure")],
        [Input("date-range", "start_date"),
         Input("date-range", "end_date"),
         Input("category-filter", "value"),
         Input("region-filter", "value"),
         Input("channel-filter", "value")],
    )
    def update_charts(start_date, end_date, category, region, channel):
        # 数据筛选
        filtered = completed.copy()
        if start_date:
            filtered = filtered[filtered["order_date"] >= start_date]
        if end_date:
            filtered = filtered[filtered["order_date"] <= end_date]
        if category != "all":
            filtered = filtered[filtered["category"] == category]
        if region != "all":
            filtered = filtered[filtered["region"] == region]
        if channel != "all":
            filtered = filtered[filtered["channel"] == channel]

        # 1. 销售额趋势
        trend_fig = _make_trend_chart(filtered)

        # 2. 星期销售分布
        weekday_fig = _make_weekday_chart(filtered)

        # 3. 品类贡献度
        category_fig = _make_category_chart(filtered)

        # 4. 区域销售
        region_fig = _make_region_chart(filtered)

        # 5. 复购率
        repurchase_fig = _make_repurchase_chart(filtered)

        # 6. 品类月度趋势
        cat_trend_fig = _make_category_trend_chart(filtered)

        return trend_fig, weekday_fig, category_fig, region_fig, repurchase_fig, cat_trend_fig

    return app


# ============ KPI卡片组件 ============
def _create_kpi_card(title, value, icon="📊"):
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.Span(icon, style={"fontSize": "2rem"}),
                html.Div([
                    html.P(title, className="text-muted small mb-0"),
                    html.H3(value, className="fw-bold mb-0", style={"color": "#1a1a2e"}),
                ], className="ms-2"),
            ], className="d-flex align-items-center"),
        ]),
    ], className="shadow-sm h-100")


# ============ 图表生成函数 ============
def _make_trend_chart(df):
    daily = df.groupby(df["order_date"].dt.date).agg(
        revenue=("final_amount", "sum"),
        orders=("order_id", "count"),
    ).reset_index()
    daily.rename(columns={"order_date": "date"}, inplace=True)
    daily["ma7"] = daily["revenue"].rolling(7, min_periods=1).mean()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=daily["date"], y=daily["revenue"],
        name="日销售额", marker_color="#636EFA", opacity=0.4,
    ))
    fig.add_trace(go.Scatter(
        x=daily["date"], y=daily["ma7"],
        name="7日均线", line=dict(color="#EF553B", width=2.5),
    ))
    fig.update_layout(
        height=400, template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=50, r=30, t=30, b=50),
    )
    return fig


def _make_weekday_chart(df):
    day_names = {0: "周一", 1: "周二", 2: "周三", 3: "周四", 4: "周五", 5: "周六", 6: "周日"}
    weekday = df.groupby("day_of_week").agg(
        revenue=("final_amount", "sum"),
        orders=("order_id", "count"),
    ).reset_index()
    weekday["day_name"] = weekday["day_of_week"].map(day_names)

    # 计算日均
    total_weeks = max(1, (df["order_date"].max() - df["order_date"].min()).days / 7)
    weekday["avg_revenue"] = weekday["revenue"] / total_weeks

    colors = ["#636EFA"] * 5 + ["#EF553B", "#EF553B"]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=weekday["day_name"], y=weekday["avg_revenue"],
        marker_color=colors,
        text=weekday["avg_revenue"].round(0).astype(int).apply(lambda x: f"¥{x:,}"),
        textposition="outside",
    ))
    fig.update_layout(
        height=350, template="plotly_white",
        yaxis_title="日均销售额",
        margin=dict(l=50, r=30, t=30, b=50),
    )
    return fig


def _make_category_chart(df):
    cat = df.groupby("category")["final_amount"].sum().reset_index()
    cat = cat.sort_values("final_amount", ascending=False)

    fig = go.Figure(go.Pie(
        labels=cat["category"], values=cat["final_amount"],
        hole=0.45, textinfo="label+percent",
        marker=dict(colors=px.colors.qualitative.Set2),
    ))
    fig.update_layout(
        height=350, template="plotly_white",
        margin=dict(l=30, r=30, t=30, b=30),
    )
    return fig


def _make_region_chart(df):
    region = df.groupby("region").agg(
        revenue=("final_amount", "sum"),
        orders=("order_id", "count"),
    ).reset_index().sort_values("revenue", ascending=False)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=region["region"], y=region["revenue"],
        name="销售额", marker_color="#00CC96",
        text=region["revenue"].apply(lambda x: f"¥{x/1e6:.1f}M"),
        textposition="outside",
    ))
    fig.update_layout(
        height=350, template="plotly_white",
        yaxis_title="销售额",
        margin=dict(l=50, r=30, t=30, b=50),
    )
    return fig


def _make_repurchase_chart(df):
    cust = df.groupby(["customer_id", "customer_type"])["order_id"].count().reset_index()
    type_stats = cust.groupby("customer_type").agg(
        total=("customer_id", "count"),
        repeat=("order_id", lambda x: (x > 1).sum()),
    ).reset_index()
    type_stats["rate"] = (type_stats["repeat"] / type_stats["total"] * 100).round(1)

    colors = {"VIP": "#00CC96", "老客": "#636EFA", "新客": "#EF553B"}
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=type_stats["customer_type"], y=type_stats["rate"],
        marker_color=[colors.get(t, "#AB63FA") for t in type_stats["customer_type"]],
        text=type_stats["rate"].astype(str) + "%",
        textposition="outside",
    ))
    fig.update_layout(
        height=350, template="plotly_white",
        yaxis_title="复购率(%)",
        margin=dict(l=50, r=30, t=30, b=50),
    )
    return fig


def _make_category_trend_chart(df):
    cat_monthly = df.groupby(["year_month", "category"])["final_amount"].sum().reset_index()
    categories = sorted(cat_monthly["category"].unique())
    colors = px.colors.qualitative.Bold[:len(categories)]

    fig = go.Figure()
    for cat, color in zip(categories, colors):
        cat_data = cat_monthly[cat_monthly["category"] == cat].sort_values("year_month")
        fig.add_trace(go.Scatter(
            x=cat_data["year_month"], y=cat_data["final_amount"],
            mode="lines+markers", name=cat,
            line=dict(color=color, width=2),
        ))

    fig.update_layout(
        height=450, template="plotly_white",
        xaxis_title="月份", yaxis_title="销售额",
        legend=dict(orientation="h", yanchor="bottom", y=-0.2),
        margin=dict(l=60, r=30, t=30, b=80),
    )
    return fig


def run_dashboard(df, port=8050):
    """启动仪表板服务"""
    app = create_dashboard(df)
    print(f"\n{'='*60}")
    print(f"  仪表板启动中: http://localhost:{port}")
    print(f"{'='*60}\n")
    app.run(debug=False, port=port)


if __name__ == "__main__":
    from clean_data import RetailDataCleaner

    data_dir = os.path.join(os.path.dirname(__file__), "data")
    cleaned_path = os.path.join(data_dir, "cleaned_retail_sales.csv")

    if not os.path.exists(cleaned_path):
        print("请先运行数据清洗: python clean_data.py")
    else:
        df = pd.read_csv(cleaned_path, parse_dates=["order_date"])
        # 补充时间字段
        df["year"] = df["order_date"].dt.year
        df["month"] = df["order_date"].dt.month
        df["day_of_week"] = df["order_date"].dt.dayofweek
        df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
        df["year_month"] = df["order_date"].dt.to_period("M").astype(str)

        run_dashboard(df)
