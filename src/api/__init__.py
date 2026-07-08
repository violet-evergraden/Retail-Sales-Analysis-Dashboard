"""FastAPI 后端服务 - 提供数据分析RESTful API"""
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import pandas as pd
import numpy as np
from pathlib import Path

from src.config import get_settings
from src.utils import get_logger

logger = get_logger("api")

app = FastAPI(
    title="零售销售分析API",
    description="提供零售销售数据的RESTful API接口",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局数据存储
_data_store: Dict[str, pd.DataFrame] = {}


def load_data():
    """加载清洗后的数据"""
    path = Path(settings.paths.data_dir) / "cleaned_retail_sales.csv"
    if path.exists():
        df = pd.read_csv(path, parse_dates=["order_date"])
        df["year"] = df["order_date"].dt.year
        df["month"] = df["order_date"].dt.month
        df["day_of_week"] = df["order_date"].dt.dayofweek
        df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
        df["year_month"] = df["order_date"].dt.to_period("M").astype(str)
        _data_store["main"] = df
        _data_store["completed"] = df[df["order_status"] == "已完成"].copy()
        logger.info(f"API数据加载完成: {len(df)} 条记录")
    else:
        logger.warning(f"数据文件不存在: {path}")


@app.on_event("startup")
async def startup():
    load_data()


# ============ Response Models ============
class KPIResponse(BaseModel):
    total_revenue: float
    total_orders: int
    total_customers: int
    avg_order_value: float
    repurchase_rate: float

class DailySalesItem(BaseModel):
    date: str
    revenue: float
    orders: int

class CategoryItem(BaseModel):
    category: str
    revenue: float
    revenue_pct: float
    orders: int

class RegionItem(BaseModel):
    region: str
    revenue: float
    orders: int

class InsightItem(BaseModel):
    type: str
    title: str
    detail: str
    suggestion: str


# ============ API Endpoints ============
@app.get("/", tags=["系统"])
async def root():
    return {"status": "running", "version": "2.0.0", "records": len(_data_store.get("main", []))}


@app.get("/api/health", tags=["系统"])
async def health():
    loaded = "main" in _data_store
    return {"healthy": loaded, "records": len(_data_store.get("main", []))}


@app.get("/api/kpi", response_model=KPIResponse, tags=["核心指标"])
async def get_kpi(
    category: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
):
    """获取核心KPI指标"""
    df = _data_store.get("completed")
    if df is None:
        raise HTTPException(404, "数据未加载")

    filtered = df.copy()
    if category: filtered = filtered[filtered["category"] == category]
    if region: filtered = filtered[filtered["region"] == region]
    if year: filtered = filtered[filtered["year"] == year]

    cust_orders = filtered.groupby("customer_id")["order_id"].count()
    repurchase = (cust_orders > 1).sum() / max(1, len(cust_orders)) * 100

    return KPIResponse(
        total_revenue=round(filtered["final_amount"].sum(), 2),
        total_orders=int(len(filtered)),
        total_customers=int(filtered["customer_id"].nunique()),
        avg_order_value=round(filtered["final_amount"].mean(), 2),
        repurchase_rate=round(repurchase, 1),
    )


@app.get("/api/sales/daily", response_model=List[DailySalesItem], tags=["销售数据"])
async def get_daily_sales(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    """获取日销售额数据"""
    df = _data_store.get("completed")
    if df is None: raise HTTPException(404, "数据未加载")
    filtered = df.copy()
    if start_date: filtered = filtered[filtered["order_date"] >= start_date]
    if end_date: filtered = filtered[filtered["order_date"] <= end_date]

    daily = filtered.groupby(filtered["order_date"].dt.date).agg(
        revenue=("final_amount", "sum"), orders=("order_id", "count"),
    ).reset_index()
    daily.rename(columns={"order_date": "date"}, inplace=True)

    return [DailySalesItem(date=str(r["date"]), revenue=round(r["revenue"], 2),
                            orders=int(r["orders"])) for _, r in daily.iterrows()]


@app.get("/api/sales/category", response_model=List[CategoryItem], tags=["销售数据"])
async def get_category_sales(region: Optional[str] = Query(None)):
    """获取品类销售数据"""
    df = _data_store.get("completed")
    if df is None: raise HTTPException(404, "数据未加载")
    filtered = df.copy()
    if region: filtered = filtered[filtered["region"] == region]

    cat = filtered.groupby("category").agg(
        revenue=("final_amount", "sum"), orders=("order_id", "count"),
    ).reset_index()
    total = cat["revenue"].sum()
    cat["revenue_pct"] = (cat["revenue"] / total * 100).round(2)
    cat = cat.sort_values("revenue", ascending=False)

    return [CategoryItem(**r.to_dict()) for _, r in cat.iterrows()]


@app.get("/api/sales/region", response_model=List[RegionItem], tags=["销售数据"])
async def get_region_sales(category: Optional[str] = Query(None)):
    """获取区域销售数据"""
    df = _data_store.get("completed")
    if df is None: raise HTTPException(404, "数据未加载")
    filtered = df.copy()
    if category: filtered = filtered[filtered["category"] == category]

    region = filtered.groupby("region").agg(
        revenue=("final_amount", "sum"), orders=("order_id", "count"),
    ).reset_index().sort_values("revenue", ascending=False)

    return [RegionItem(**r.to_dict()) for _, r in region.iterrows()]


@app.get("/api/sales/monthly", tags=["销售数据"])
async def get_monthly_sales(region: Optional[str] = Query(None)):
    """获取月度销售汇总（含环比）"""
    df = _data_store.get("completed")
    if df is None: raise HTTPException(404, "数据未加载")
    filtered = df.copy()
    if region: filtered = filtered[filtered["region"] == region]

    monthly = filtered.groupby("year_month").agg(
        revenue=("final_amount", "sum"), orders=("order_id", "count"),
        customers=("customer_id", "nunique"),
    ).reset_index().sort_values("year_month")
    monthly["mom_growth"] = monthly["revenue"].pct_change() * 100

    return monthly.round(2).to_dict(orient="records")


@app.get("/api/customers/repurchase", tags=["客户分析"])
async def get_repurchase():
    """获取复购率数据"""
    df = _data_store.get("completed")
    if df is None: raise HTTPException(404, "数据未加载")

    cust = df.groupby(["customer_id", "customer_type"])["order_id"].count().reset_index()
    result = cust.groupby("customer_type").agg(
        total=("customer_id", "count"),
        repeat=("order_id", lambda x: (x > 1).sum()),
    ).reset_index()
    result["rate"] = (result["repeat"] / result["total"] * 100).round(1)
    return result.to_dict(orient="records")


@app.get("/api/insights", response_model=List[InsightItem], tags=["洞察"])
async def get_insights():
    """获取数据洞察"""
    df = _data_store.get("completed")
    if df is None: raise HTTPException(404, "数据未加载")

    weekend = df[df["is_weekend"] == 1]
    weekday = df[df["is_weekend"] == 0]
    we_avg = weekend["final_amount"].sum() / max(1, weekend["order_date"].dt.date.nunique())
    wd_avg = weekday["final_amount"].sum() / max(1, weekday["order_date"].dt.date.nunique())
    uplift = (we_avg - wd_avg) / max(1, wd_avg) * 100

    return [
        InsightItem(type="发现", title="周末销售高峰",
                     detail=f"周末日均销售额比工作日高{uplift:.1f}%",
                     suggestion="集中促销资源在周末"),
        InsightItem(type="建议", title="品类优化",
                     detail="部分品类存在季节性下滑趋势",
                     suggestion="对下滑品类加大促销或调整库存"),
    ]


@app.get("/api/export/{format}", tags=["导出"])
async def export_data(format: str = "csv"):
    """导出数据"""
    df = _data_store.get("completed")
    if df is None: raise HTTPException(404, "数据未加载")

    if format == "summary":
        summary = df.groupby(["year_month", "category"])["final_amount"].sum().reset_index()
        return summary.to_dict(orient="records")
    raise HTTPException(400, f"不支持的导出格式: {format}")


def run_api():
    """启动API服务"""
    import uvicorn
    logger.info(f"API服务启动: http://{settings.api.host}:{settings.api.port}")
    uvicorn.run(app, host=settings.api.host, port=settings.api.port)


if __name__ == "__main__":
    run_api()
