"""升级版 Plotly Dash 交互式仪表板 - 暗色主题 + 更多交互"""
import dash
from dash import dcc, html, Input, Output, callback_context
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from pathlib import Path

from src.config import get_settings
from src.utils import get_logger

logger = get_logger("dashboard")


def create_dashboard(df: pd.DataFrame, forecast_df: pd.DataFrame = None):
    settings = get_settings()
    theme = settings.dashboard.theme
    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY if "dark" in theme else dbc.themes.FLATLY],
                     title="Retail Sales Dashboard v2.0")

    completed = df[df["order_status"] == "已完成"].copy()
    categories = sorted(df["category"].dropna().unique().tolist())
    regions = sorted(df["region"].dropna().unique().tolist())

    total_rev = completed["final_amount"].sum()
    total_orders = len(completed)
    total_customers = completed["customer_id"].nunique()
    avg_order = completed["final_amount"].mean()

    app.layout = dbc.Container([
        # 顶部标题栏
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H1("Retail Sales Dashboard", className="display-5 fw-bold",
                             style={"color": "#fff"}),
                    html.P("120,000+ Orders | Multi-dimensional Analysis | ML Forecasting",
                            className="text-muted"),
                ], className="mb-3"),
            ], width=8),
            dbc.Col([
                html.Div([
                    dbc.Button("📥 导出CSV", id="btn-export", color="primary", size="sm", className="me-2"),
                    html.A("📄 API文档", href="http://localhost:8000/docs", target="_blank",
                           className="btn btn-outline-light btn-sm"),
                ], className="text-end mt-3"),
            ], width=4),
        ]),

        # KPI卡片
        dbc.Row([
            _kpi_card("💰", "总销售额", f"¥{total_rev/1e6:.1f}M", "#636EFA"),
            _kpi_card("📦", "总订单数", f"{total_orders:,}", "#EF553B"),
            _kpi_card("👥", "客户总数", f"{total_customers:,}", "#00CC96"),
            _kpi_card("🏷️", "客单价", f"¥{avg_order:.0f}", "#AB63FA"),
        ], className="mb-3"),

        # 筛选器
        dbc.Card([
            dbc.CardBody(dbc.Row([
                dbc.Col([
                    html.Label("📅 时间范围", className="text-light small fw-bold"),
                    dcc.DatePickerRange(id="date-range",
                        start_date=completed["order_date"].min().strftime("%Y-%m-%d"),
                        end_date=completed["order_date"].max().strftime("%Y-%m-%d"),
                        display_format="YYYY-MM-DD", className="w-100"),
                ], width=3),
                dbc.Col([
                    html.Label("🏷️ 品类", className="text-light small fw-bold"),
                    dcc.Dropdown(id="cat-filter",
                        options=[{"label": "全部品类", "value": "all"}] + [{"label": c, "value": c} for c in categories],
                        value="all", clearable=False, className="text-dark"),
                ], width=3),
                dbc.Col([
                    html.Label("🗺️ 地区", className="text-light small fw-bold"),
                    dcc.Dropdown(id="reg-filter",
                        options=[{"label": "全部地区", "value": "all"}] + [{"label": r, "value": r} for r in regions],
                        value="all", clearable=False, className="text-dark"),
                ], width=3),
                dbc.Col([
                    html.Label("📊 图表主题", className="text-light small fw-bold"),
                    dcc.Dropdown(id="chart-theme",
                        options=[{"label": "暗色", "value": "plotly_dark"},
                                 {"label": "亮色", "value": "plotly_white"},
                                 {"label": "简约", "value": "simple_white"}],
                        value="plotly_dark", clearable=False, className="text-dark"),
                ], width=3),
            ])),
        ], className="mb-3", color="dark", outline=True),

        # 图表 - 第一行: 趋势 + 预测
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader("📈 销售额趋势 + 预测", className="fw-bold text-light"),
                dbc.CardBody(dcc.Graph(id="trend-chart", config={"displayModeBar": True})),
            ], color="dark", outline=True), width=12),
        ], className="mb-3"),

        # 图表 - 第二行: 星期 + 品类
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader("🗓️ 星期销售分布", className="fw-bold text-light"),
                dbc.CardBody(dcc.Graph(id="weekday-chart")),
            ], color="dark", outline=True), width=6),
            dbc.Col(dbc.Card([
                dbc.CardHeader("🏷️ 品类贡献度", className="fw-bold text-light"),
                dbc.CardBody(dcc.Graph(id="category-chart")),
            ], color="dark", outline=True), width=6),
        ], className="mb-3"),

        # 图表 - 第三行: 区域 + 复购
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader("🗺️ 区域销售", className="fw-bold text-light"),
                dbc.CardBody(dcc.Graph(id="region-chart")),
            ], color="dark", outline=True), width=6),
            dbc.Col(dbc.Card([
                dbc.CardHeader("🔄 复购率 + 客户分群", className="fw-bold text-light"),
                dbc.CardBody(dcc.Graph(id="repurchase-chart")),
            ], color="dark", outline=True), width=6),
        ], className="mb-3"),

        # 图表 - 第四行: 品类月度趋势
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader("📊 品类月度趋势（下滑预警）", className="fw-bold text-light"),
                dbc.CardBody(dcc.Graph(id="cat-trend-chart")),
            ], color="dark", outline=True), width=12),
        ], className="mb-3"),

        # 下载组件
        dcc.Download(id="download-csv"),
        html.Footer(html.P("© 2025 Retail Sales Dashboard v2.0 | Built with Plotly Dash",
                            className="text-center text-muted small py-2")),
    ], fluid=True, className="px-3 py-2", style={"backgroundColor": "#1a1a2e", "minHeight": "100vh"})

    # ============ 回调 ============
    @app.callback(
        [Output("trend-chart", "figure"), Output("weekday-chart", "figure"),
         Output("category-chart", "figure"), Output("region-chart", "figure"),
         Output("repurchase-chart", "figure"), Output("cat-trend-chart", "figure")],
        [Input("date-range", "start_date"), Input("date-range", "end_date"),
         Input("cat-filter", "value"), Input("reg-filter", "value"),
         Input("chart-theme", "value")],
    )
    def update_all(start_date, end_date, category, region, theme):
        f = completed.copy()
        if start_date: f = f[f["order_date"] >= start_date]
        if end_date: f = f[f["order_date"] <= end_date]
        if category != "all": f = f[f["category"] == category]
        if region != "all": f = f[f["region"] == region]

        return (_trend_fig(f, forecast_df, theme), _weekday_fig(f, theme),
                _cat_fig(f, theme), _region_fig(f, theme),
                _repurchase_fig(f, theme), _cat_trend_fig(f, theme))

    @app.callback(Output("download-csv", "data"), Input("btn-export", "n_clicks"), prevent_initial_call=True)
    def export_csv(n_clicks):
        return dcc.send_data_frame(completed.to_csv, "retail_sales_export.csv", index=False)

    return app


def _kpi_card(icon, title, value, color):
    return dbc.Col(dbc.Card(dbc.CardBody([
        html.Div([html.Span(icon, style={"fontSize": "1.8rem"}),
                   html.Div([html.P(title, className="text-muted small mb-0"),
                              html.H4(value, className="fw-bold mb-0", style={"color": color})],
                             className="ms-2")], className="d-flex align-items-center"),
    ]), color="dark", outline=True, className="h-100"))


def _trend_fig(df, forecast_df, theme):
    daily = df.groupby(df["order_date"].dt.date)["final_amount"].sum().reset_index()
    daily.columns = ["date", "revenue"]
    daily["ma7"] = daily["revenue"].rolling(7, min_periods=1).mean()
    fig = go.Figure()
    fig.add_trace(go.Bar(x=daily["date"], y=daily["revenue"], name="日销售额",
                          marker_color="#636EFA", opacity=0.4))
    fig.add_trace(go.Scatter(x=daily["date"], y=daily["ma7"], name="7日均线",
                              line=dict(color="#EF553B", width=2.5)))
    if forecast_df is not None:
        fc = forecast_df[forecast_df["is_forecast"]]
        fig.add_trace(go.Scatter(x=fc["ds"], y=fc["predicted"], name="预测",
                                  line=dict(color="#FFA15A", width=2, dash="dash")))
    fig.update_layout(height=400, template=theme, margin=dict(l=50, r=30, t=30, b=50),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02))
    return fig


def _weekday_fig(df, theme):
    day_names = {0: "周一", 1: "周二", 2: "周三", 3: "周四", 4: "周五", 5: "周六", 6: "周日"}
    w = df.groupby("day_of_week")["final_amount"].sum().reset_index()
    tw = max(1, (df["order_date"].max() - df["order_date"].min()).days / 7)
    w["avg"] = w["final_amount"] / tw
    w["name"] = w["day_of_week"].map(day_names)
    colors = ["#636EFA"] * 5 + ["#EF553B", "#EF553B"]
    fig = go.Figure(go.Bar(x=w["name"], y=w["avg"], marker_color=colors,
                            text=w["avg"].round(0).astype(int).apply(lambda x: f"¥{x:,}"), textposition="outside"))
    fig.update_layout(height=350, template=theme, margin=dict(l=50, r=30, t=30, b=50))
    return fig


def _cat_fig(df, theme):
    cat = df.groupby("category")["final_amount"].sum().reset_index().sort_values("final_amount", ascending=False)
    fig = go.Figure(go.Pie(labels=cat["category"], values=cat["final_amount"], hole=0.45,
                            textinfo="label+percent", marker=dict(colors=px.colors.qualitative.Set2)))
    fig.update_layout(height=350, template=theme, margin=dict(l=30, r=30, t=30, b=30))
    return fig


def _region_fig(df, theme):
    r = df.groupby("region")["final_amount"].sum().reset_index().sort_values("final_amount", ascending=False)
    fig = go.Figure(go.Bar(x=r["region"], y=r["final_amount"], marker_color="#00CC96",
                            text=r["final_amount"].apply(lambda x: f"¥{x/1e6:.1f}M"), textposition="outside"))
    fig.update_layout(height=350, template=theme, margin=dict(l=50, r=30, t=30, b=50))
    return fig


def _repurchase_fig(df, theme):
    cust = df.groupby(["customer_id", "customer_type"])["order_id"].count().reset_index()
    ts = cust.groupby("customer_type").agg(total=("customer_id", "count"),
                                            repeat=("order_id", lambda x: (x > 1).sum())).reset_index()
    ts["rate"] = (ts["repeat"] / ts["total"] * 100).round(1)
    colors = {"VIP": "#00CC96", "老客": "#636EFA", "新客": "#EF553B"}
    fig = go.Figure(go.Bar(x=ts["customer_type"], y=ts["rate"],
                            marker_color=[colors.get(t, "#AB63FA") for t in ts["customer_type"]],
                            text=ts["rate"].astype(str) + "%", textposition="outside"))
    fig.update_layout(height=350, template=theme, margin=dict(l=50, r=30, t=30, b=50))
    return fig


def _cat_trend_fig(df, theme):
    cm = df.groupby(["year_month", "category"])["final_amount"].sum().reset_index()
    cats = sorted(cm["category"].unique())
    fig = go.Figure()
    for cat, color in zip(cats, px.colors.qualitative.Bold[:len(cats)]):
        d = cm[cm["category"] == cat].sort_values("year_month")
        fig.add_trace(go.Scatter(x=d["year_month"], y=d["final_amount"],
                                  mode="lines+markers", name=cat, line=dict(color=color, width=2)))
    fig.update_layout(height=450, template=theme, margin=dict(l=60, r=30, t=30, b=80),
                      legend=dict(orientation="h", yanchor="bottom", y=-0.2))
    return fig


def run_dashboard(df, forecast_df=None, port=8050):
    app = create_dashboard(df, forecast_df)
    logger.info(f"仪表板启动: http://localhost:{port}")
    app.run(debug=False, port=port)
