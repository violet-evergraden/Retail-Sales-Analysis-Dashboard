# Retail Sales Analysis Dashboard v2.0

> 基于 Python + Plotly Dash + FastAPI + ML 的全流程零售数据分析平台。处理 **12万+条** 零售订单数据，涵盖数据生成、清洗、机器学习预测、RESTful API、交互式仪表板和 PDF 报告生成。

---

## 目录

- [项目架构](#项目架构)
- [技术栈](#技术栈)
- [快速开始](#快速开始)
- [Docker 部署](#docker-部署)
- [分步运行](#分步运行)
- [API 文档](#api-文档)
- [仪表板功能](#仪表板功能)
- [机器学习模块](#机器学习模块)
- [SQL 查询](#sql-查询)
- [测试](#测试)
- [CI/CD](#cicd)
- [项目结构](#项目结构)
- [配置说明](#配置说明)

---

## 项目架构

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  Data Layer  │ ──▶ │  ML Models   │ ──▶ │  API Service │
│  (Generator  │     │  (Forecast + │     │  (FastAPI)   │
│   + Cleaner) │     │   Clustering)│     │              │
└─────────────┘     └──────────────┘     └──────┬───────┘
                                                │
                    ┌──────────────┐     ┌──────▼───────┐
                    │  PDF Report  │◀─── │  Dashboard   │
                    │  (ReportLab) │     │  (Plotly Dash)│
                    └──────────────┘     └──────────────┘
```

## 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| **数据处理** | Pandas, NumPy, SciPy | ETL、清洗、统计 |
| **机器学习** | scikit-learn | 时间序列预测(Holt-Winters)、客户聚类(K-Means) |
| **可视化** | Plotly, Plotly Express | 交互式图表 |
| **仪表板** | Dash, Dash Bootstrap | Web UI（暗色主题） |
| **API** | FastAPI, Uvicorn | RESTful 接口 + Swagger文档 |
| **数据库** | MySQL, SQLAlchemy | 持久化存储 |
| **报告** | ReportLab | PDF自动生成 |
| **测试** | pytest, pytest-cov | 单元测试 + 覆盖率 |
| **容器化** | Docker, Docker Compose | 一键部署 |
| **CI/CD** | GitHub Actions | 自动测试 + 构建 |
| **配置** | YAML | 集中式配置管理 |
| **日志** | logging + RotatingFileHandler | 结构化日志 |

---

## 快速开始

### 前置要求

- Python 3.10+
- pip

### 安装 & 运行

```bash
# 1. 克隆项目
git clone https://github.com/violet-evergraden/Retail-Sales-Analysis-Dashboard.git
cd Retail-Sales-Analysis-Dashboard

# 2. 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 运行全流程（生成数据 → 清洗 → 分析 → ML → 仪表板）
python main.py
```

访问 `http://localhost:8050` 查看仪表板，`http://localhost:8000/docs` 查看API文档。

---

## Docker 部署

```bash
# 一键启动（MySQL + API + 仪表板）
docker-compose up -d

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f app
```

- 仪表板: `http://localhost:8050`
- API文档: `http://localhost:8000/docs`
- MySQL: `localhost:3306`

---

## 分步运行

通过 `--service` 参数控制运行步骤：

```bash
# 仅生成数据（12万条）
python main.py --service generate

# 仅数据清洗
python main.py --service clean

# 分析 + ML预测 + PDF报告
python main.py --service analyze

# 启动REST API服务
python main.py --service api --port 8000

# 启动交互式仪表板
python main.py --service dashboard --port 8050

# 全流程（API + 仪表板同时启动）
python main.py --service all
```

---

## API 文档

启动API服务后访问 `http://localhost:8000/docs` 查看 Swagger UI。

### 核心接口

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/kpi` | GET | 核心KPI（支持category/region/year筛选） |
| `/api/sales/daily` | GET | 日销售额（支持日期范围） |
| `/api/sales/category` | GET | 品类销售（支持region筛选） |
| `/api/sales/region` | GET | 区域销售（支持category筛选） |
| `/api/sales/monthly` | GET | 月度汇总（含环比） |
| `/api/customers/repurchase` | GET | 复购率数据 |
| `/api/insights` | GET | 数据洞察 |
| `/api/export/summary` | GET | 导出汇总数据 |

### 调用示例

```bash
# 获取KPI
curl http://localhost:8000/api/kpi

# 筛选特定品类和地区
curl "http://localhost:8000/api/kpi?category=电子产品&region=华东"

# 获取日销售额
curl "http://localhost:8000/api/sales/daily?start_date=2025-01-01&end_date=2025-03-31"
```

---

## 仪表板功能

基于 Plotly Dash 构建的暗色主题仪表板，支持：

- **四维筛选器**: 时间范围 + 品类 + 地区 + 图表主题切换
- **KPI面板**: 总销售额、订单数、客户数、客单价
- **趋势图**: 日销售额 + 7日均线 + ML预测曲线
- **星期对比**: 工作日 vs 周末（红色高亮）
- **品类分析**: 贡献度饼图 + 月度趋势（下滑预警）
- **区域分析**: 多维度柱状图
- **复购率**: VIP/老客/新客对比
- **数据导出**: 一键导出CSV

---

## 机器学习模块

### 1. 销售预测 (SalesForecaster)

- **方法**: Holt-Winters 三重指数平滑
- **特性**: 网格搜索最优参数 (α, β, γ)，周季节性建模
- **输出**: 未来90天日销售额预测
- **可视化**: 历史数据 + 拟合曲线 + 预测区间

### 2. 客户聚类 (CustomerSegmenter)

- **方法**: K-Means 聚类 (基于RFM模型)
- **特征**: Recency(最近购买天数) + Frequency(购买频率) + Monetary(消费金额)
- **输出**: 5类客户分群（高价值/高频/潜力/低活跃/流失风险）
- **应用**: 差异化营销策略

---

## SQL 查询

`sql_queries.sql` 包含 10 个 MySQL 复杂查询：

| # | 查询 | 技术点 |
|---|------|--------|
| 1 | 建表 | INDEX, 字符集 |
| 2 | 月度汇总 | CTE, 同比/环比, 自连接 |
| 3 | 区域分析 | 多维GROUP BY, RANK窗口函数 |
| 4 | 品类贡献度 | CTE + LAG, 环比计算 |
| 5 | 复购率 | 子查询, CASE WHEN, LTV |
| 6 | 渠道效果 | 多维聚合 |
| 7 | 周末vs工作日 | 条件分组 |
| 8 | 支付方式 | 占比子查询 |
| 9 | RFM评分 | NTILE窗口函数, 加权 |
| 10 | 下滑预警 | ROWS BETWEEN, 连续检测 |

---

## 测试

```bash
# 运行全部测试
python -m pytest tests/ -v

# 带覆盖率报告
python -m pytest tests/ -v --cov=src --cov-report=term-missing

# 运行特定测试
python -m pytest tests/test_generator.py -v
python -m pytest tests/test_cleaner.py -v
python -m pytest tests/test_api.py -v
```

**测试覆盖:**
- 数据生成器: 8个测试用例（列完整性、唯一性、缺失值、异常值、日期范围）
- 数据清洗器: 7个测试用例（缺失处理、异常修正、时间特征、指标计算）
- API端点: 2个测试用例（模块导入、路由注册）

---

## CI/CD

项目使用 GitHub Actions 自动化流水线：

- **触发**: push/PR to `main` 分支
- **测试**: Python 3.10/3.11/3.12 矩阵测试
- **验证**: 数据管道端到端验证
- **构建**: Docker 镜像构建验证

查看流水线状态: `.github/workflows/ci.yml`

---

## 项目结构

```
Retail-Sales-Analysis-Dashboard/
│
├── src/                           # 源码包
│   ├── __init__.py
│   ├── config/                    # 配置管理
│   │   └── __init__.py           # Settings单例 + YAML加载
│   ├── data/                      # 数据层
│   │   ├── __init__.py           # DataGenerator
│   │   └── cleaner.py            # DataCleaner
│   ├── models/                    # 机器学习
│   │   └── __init__.py           # SalesForecaster + CustomerSegmenter
│   ├── analysis/                  # 分析 & 报告
│   │   └── __init__.py           # RetailAnalyzer + PDF生成
│   ├── api/                       # REST API
│   │   └── __init__.py           # FastAPI应用
│   ├── dashboard/                 # Web仪表板
│   │   └── __init__.py           # Dash应用
│   └── utils/                     # 工具
│       └── __init__.py           # Logger
│
├── tests/                         # 单元测试
│   ├── test_generator.py
│   ├── test_cleaner.py
│   └── test_api.py
│
├── .github/workflows/ci.yml      # GitHub Actions
├── config.yaml                    # 全局配置
├── main.py                        # 主入口
├── sql_queries.sql                # MySQL查询脚本
├── requirements.txt               # Python依赖
├── Dockerfile                     # Docker镜像
├── docker-compose.yml             # 容器编排
├── .gitignore
└── README.md
```

---

## 配置说明

所有配置集中在 `config.yaml`，支持环境变量覆盖：

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `DB_HOST` | MySQL主机 | localhost |
| `DB_PORT` | MySQL端口 | 3306 |
| `DB_USER` | MySQL用户 | root |
| `DB_PASSWORD` | MySQL密码 | (空) |
| `API_PORT` | API端口 | 8000 |
| `DASHBOARD_PORT` | 仪表板端口 | 8050 |

---

## License

MIT License
