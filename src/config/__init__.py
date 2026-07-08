"""配置管理模块"""
import os
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class ProjectConfig:
    name: str = "Retail Sales Analysis Dashboard"
    version: str = "2.0.0"

@dataclass
class DataGeneratorConfig:
    num_records: int = 120000
    start_date: str = "2023-01-01"
    end_date: str = "2025-12-31"
    missing_rate: Dict[str, float] = field(default_factory=lambda: {
        "unit_price": 0.02, "quantity": 0.015, "category": 0.01,
        "region": 0.005, "payment_method": 0.01
    })
    outlier_rate: Dict[str, float] = field(default_factory=lambda: {
        "high_price": 0.003, "negative_quantity": 0.002, "abnormal_discount": 0.001
    })

@dataclass
class CleanerConfig:
    iqr_multiplier: float = 3.0
    max_discount_rate: float = 0.5
    default_quantity: int = 1
    unknown_fill: str = "未知"

@dataclass
class DatabaseConfig:
    host: str = "localhost"
    port: int = 3306
    user: str = "root"
    password: str = ""
    database: str = "retail_sales_db"

    @property
    def url(self) -> str:
        return f"mysql+mysqlconnector://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

@dataclass
class APIConfig:
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    cors_origins: List[str] = field(default_factory=lambda: ["*"])

@dataclass
class DashboardConfig:
    host: str = "0.0.0.0"
    port: int = 8050
    debug: bool = False
    theme: str = "darkly"

@dataclass
class MLConfig:
    forecast_method: str = "exponential"
    forecast_days: int = 90
    seasonality_mode: str = "multiplicative"
    n_clusters: int = 5
    random_state: int = 42

@dataclass
class PathsConfig:
    data_dir: str = "data"
    output_dir: str = "output"
    charts_dir: str = "output/charts"
    reports_dir: str = "output/reports"


class Settings:
    """全局配置管理器"""

    _instance = None

    def __new__(cls, config_path: Optional[str] = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_path: Optional[str] = None):
        if self._initialized:
            return
        self._initialized = True

        self.project = ProjectConfig()
        self.data_generator = DataGeneratorConfig()
        self.cleaner = CleanerConfig()
        self.database = DatabaseConfig()
        self.api = APIConfig()
        self.dashboard = DashboardConfig()
        self.ml = MLConfig()
        self.paths = PathsConfig()
        self.log_level = "INFO"
        self.log_format = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
        self.log_file = "output/app.log"

        if config_path:
            self._load_from_file(config_path)

        self._resolve_env_vars()
        self._ensure_dirs()

    def _load_from_file(self, config_path: str):
        """从YAML文件加载配置"""
        path = Path(config_path)
        if not path.exists():
            return

        with open(path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        if not cfg:
            return

        # 项目配置
        proj = cfg.get("project", {})
        self.project.name = proj.get("name", self.project.name)
        self.project.version = proj.get("version", self.project.version)

        # 数据生成器
        dg = cfg.get("data_generator", {})
        self.data_generator.num_records = dg.get("num_records", self.data_generator.num_records)
        dr = dg.get("date_range", {})
        self.data_generator.start_date = dr.get("start", self.data_generator.start_date)
        self.data_generator.end_date = dr.get("end", self.data_generator.end_date)
        if "missing_rate" in dg:
            self.data_generator.missing_rate = dg["missing_rate"]
        if "outlier_rate" in dg:
            self.data_generator.outlier_rate = dg["outlier_rate"]

        # 清洗器
        dc = cfg.get("data_cleaner", {})
        self.cleaner.iqr_multiplier = dc.get("iqr_multiplier", self.cleaner.iqr_multiplier)
        self.cleaner.max_discount_rate = dc.get("max_discount_rate", self.cleaner.max_discount_rate)

        # 数据库
        db = cfg.get("database", {})
        self.database.host = db.get("host", self.database.host)
        self.database.port = db.get("port", self.database.port)
        self.database.user = db.get("user", self.database.user)
        self.database.password = db.get("password", self.database.password)
        self.database.database = db.get("database", self.database.database)

        # API
        api = cfg.get("api", {})
        self.api.host = api.get("host", self.api.host)
        self.api.port = api.get("port", self.api.port)

        # 仪表板
        dash = cfg.get("dashboard", {})
        self.dashboard.host = dash.get("host", self.dashboard.host)
        self.dashboard.port = dash.get("port", self.dashboard.port)
        self.dashboard.theme = dash.get("theme", self.dashboard.theme)

        # ML
        ml = cfg.get("ml", {})
        fc = ml.get("forecasting", {})
        self.ml.forecast_method = fc.get("method", self.ml.forecast_method)
        self.ml.forecast_days = fc.get("forecast_days", self.ml.forecast_days)
        cl = ml.get("clustering", {})
        self.ml.n_clusters = cl.get("n_clusters", self.ml.n_clusters)

        # 日志
        log = cfg.get("logging", {})
        self.log_level = log.get("level", self.log_level)
        self.log_format = log.get("format", self.log_format)
        self.log_file = log.get("file", self.log_file)

        # 路径
        paths = cfg.get("paths", {})
        self.paths.data_dir = paths.get("data_dir", self.paths.data_dir)
        self.paths.output_dir = paths.get("output_dir", self.paths.output_dir)
        self.paths.charts_dir = paths.get("charts_dir", self.paths.charts_dir)
        self.paths.reports_dir = paths.get("reports_dir", self.paths.reports_dir)

    def _resolve_env_vars(self):
        """解析环境变量覆盖"""
        self.database.host = os.getenv("DB_HOST", self.database.host)
        self.database.port = int(os.getenv("DB_PORT", self.database.port))
        self.database.user = os.getenv("DB_USER", self.database.user)
        self.database.password = os.getenv("DB_PASSWORD", self.database.password)
        self.api.port = int(os.getenv("API_PORT", self.api.port))
        self.dashboard.port = int(os.getenv("DASHBOARD_PORT", self.dashboard.port))

    def _ensure_dirs(self):
        """确保输出目录存在"""
        for d in [self.paths.data_dir, self.paths.output_dir,
                  self.paths.charts_dir, self.paths.reports_dir]:
            Path(d).mkdir(parents=True, exist_ok=True)


def get_settings(config_path: str = "config.yaml") -> Settings:
    """获取全局配置实例"""
    return Settings(config_path)
