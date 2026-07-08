# Retail Sales Analysis Dashboard（零售销售分析仪表板）

> 基于 Python + Plotly Dash 构建的全流程零售数据分析项目。使用 Pandas 清洗 **12万+条** 零售订单数据，编写复杂 SQL 查询提取多维度指标，通过 Plotly 构建动态交互式仪表板，并自动生成 PDF 分析报告。

---

## 目录

- [项目亮点](#项目亮点)
- [项目结构](#项目结构)
- [环境准备](#环境准备)
- [快速开始（一键运行）](#快速开始一键运行)
- [分步运行指南](#分步运行指南)
  - [Step 1：生成数据](#step-1生成模拟零售数据)
  - [Step 2：数据清洗](#step-2数据清洗与预处理)
  - [Step 3：数据分析与报告](#step-3数据分析与pdf报告生成)
  - [Step 4：交互式仪表板](#step-4启动交互式仪表板)
- [仪表板功能说明](#仪表板功能说明)
- [SQL 查询说明](#sql-查询说明)
- [核心数据洞察](#核心数据洞察)
- [数据字段说明](#数据字段说明)
- [常见问题](#常见问题)
- [技术栈](#技术栈)

---

## 项目亮点

| 能力维度 | 具体实现 |
|---------|---------|
| **数据工程** | 生成12万+条真实感数据，注入缺失值/异常值，模拟周末高峰、季节性趋势、复购行为 |
| **数据清洗** | 品类中位数填充、IQR异常值检测截断、负值修正、折扣率范围约束 |
| **多维度指标** | 日销售额/订单量/客户数、品类贡献度占比、各客户类型复购率 |
| **SQL 能力** | 10个复杂查询：同比环比、窗口函数排名、CTE递归、RFM评分、品类下滑预警 |
| **可视化** | 9张 Plotly 交互图表 + Dash 仪表板（支持时间/品类/地区/渠道四维筛选） |
| **报告自动化** | ReportLab 生成结构化 PDF，含数据表格、关键洞察和优化建议 |

---

## 项目结构

```
Retail-Sales-Analysis-Dashboard/
│
├── main.py                  # 主入口，支持 --step 参数分步运行
├── generate_data.py         # 数据生成器（12万+条模拟订单）
├── clean_data.py            # 数据清洗模块（缺失值/异常值/指标计算）
├── analysis.py              # 数据分析 + 图表生成 + PDF报告
├── dashboard.py             # Plotly Dash 交互式仪表板
├── sql_queries.sql          # MySQL 复杂查询脚本（10个查询）
├── requirements.txt         # Python 依赖列表
├── .gitignore               # Git 忽略规则
├── README.md                # 项目说明文档
│
├── data/                    # 数据目录（自动生成，已git忽略）
│   ├── raw_retail_sales.csv           # 原始数据
│   ├── cleaned_retail_sales.csv       # 清洗后数据
│   ├── metrics_daily_sales.csv        # 日销售指标
│   ├── metrics_category_contribution.csv  # 品类贡献度指标
│   ├── metrics_monthly_region.csv     # 月度区域指标
│   └── cleaning_report.json           # 清洗报告
│
└── output/                  # 输出目录（自动生成，已git忽略）
    ├── retail_analysis_report.pdf     # PDF分析报告
    └── charts/                        # 图表文件
        ├── daily_trends.html
        ├── weekend_peak.html
        ├── category_contribution.html
        └── ...
```

---

## 环境准备

### 前置要求

- **Python** 3.9 或更高版本
- **pip** 包管理器
- （可选）**MySQL** 8.0+ — 用于执行 SQL 查询脚本

### 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/你的用户名/Retail-Sales-Analysis-Dashboard.git
cd Retail-Sales-Analysis-Dashboard

# 2.（推荐）创建虚拟环境
python -m venv venv

# Windows 激活虚拟环境
venv\Scripts\activate

# macOS/Linux 激活虚拟环境
source venv/bin/activate

# 3. 安装所有依赖
pip install -r requirements.txt
```

**依赖说明：**

| 包名 | 用途 |
|------|------|
| pandas, numpy | 数据处理与计算 |
| scipy | 统计分析 |
| plotly | 交互式图表 |
| dash, dash-bootstrap-components | Web 仪表板框架 |
| reportlab | PDF 报告生成 |
| kaleido | 图表导出为 PNG（可选） |
| mysql-connector-python, sqlalchemy | MySQL 数据库连接（可选） |

---

## 快速开始（一键运行）

一条命令完成 **数据生成 → 数据清洗 → 分析出图 → 生成PDF → 启动仪表板** 全流程：

```bash
python main.py
```

运行完成后，浏览器会自动打开仪表板页面（默认 `http://localhost:8050`）。

---

## 分步运行指南

通过 `--step` 参数可以单独运行某个步骤：

```bash
python main.py --step <步骤名称>
```

可选步骤：`generate` | `clean` | `analyze` | `dashboard` | `all`

---

### Step 1：生成模拟零售数据

```bash
python main.py --step generate
# 或直接运行
python generate_data.py
```

**做了什么：**
- 生成 120,000 条零售订单数据
- 覆盖 **2023-01-01 ~ 2025-12-31** 共三年时间跨度
- 包含 **7大品类**（电子产品、服装鞋帽、食品饮料等）、**42种商品**
- 覆盖 **7大区域**（华东/华南/华北等）、**33个城市**
- 模拟真实数据质量问题：
  - ~2% 单价缺失
  - ~1.5% 数量缺失
  - ~1% 品类缺失
  - ~0.3% 金额异常高（模拟输入错误）
  - ~0.2% 数量为负（模拟退货异常）
  - ~0.1% 折扣率超过100%
- 周末订单密度更高（模拟真实消费行为）
- 品类具有季节性趋势（如运动户外夏季高、图书文具开学季高）

**输出文件：** `data/raw_retail_sales.csv`

---

### Step 2：数据清洗与预处理

```bash
python main.py --step clean
# 或直接运行
python clean_data.py
```

**清洗流程（6步）：**

| 步骤 | 操作 | 说明 |
|------|------|------|
| 1 | 类型转换 | 日期、数值、字符串统一转换 |
| 2 | 去重 | 基于 order_id 去重 |
| 3 | 缺失值处理 | 单价→品类中位数填充，数量→填1，品类/地区/支付方式→填"未知" |
| 4 | 异常值处理 | 负数量→取绝对值，折扣率→clip到[0, 0.5]，极端单价→IQR截断 |
| 5 | 时间特征派生 | 新增 year, month, quarter, week, day_of_week, is_weekend, year_month |
| 6 | 指标计算 | 日销售额、品类贡献度、复购率、月度区域汇总 |

**输出文件：**
- `data/cleaned_retail_sales.csv` — 清洗后主表
- `data/metrics_daily_sales.csv` — 日销售指标
- `data/metrics_category_contribution.csv` — 品类贡献度
- `data/metrics_monthly_region.csv` — 月度区域汇总
- `data/cleaning_report.json` — 清洗统计报告

---

### Step 3：数据分析与PDF报告生成

```bash
python main.py --step analyze
```

**生成 9 张分析图表：**

1. **日销售额趋势** — 含7日/30日移动平均线
2. **周末 vs 工作日对比** — 各星期日均销售额和订单量
3. **品类贡献度** — 横向排名 + 饼图占比
4. **品类月度趋势** — 各品类按月走势，识别下滑品类
5. **区域销售多维度分析** — 销售额/订单量/客户数/客单价
6. **复购率分析** — 各客户类型复购率 + 消费金额分布
7. **渠道销售额对比** — 各渠道业绩排名
8. **渠道效率散点图** — 销售额 vs 折扣率（气泡大小=订单量）
9. **客户类型活跃趋势** — 各类型月度活跃客户数

**生成 PDF 报告内容：**
- 数据概览表格（总订单数、总营收、客户数、客单价）
- 关键洞察与优化建议
- 图表截图
- 5条具体运营优化建议

**输出目录：** `output/`

---

### Step 4：启动交互式仪表板

```bash
python main.py --step dashboard --port 8050
# 或直接运行
python dashboard.py
```

启动后在浏览器中访问 `http://localhost:8050` 即可查看仪表板。

---

## 仪表板功能说明

仪表板基于 Plotly Dash 构建，具有以下功能：

### KPI 指标卡
顶部展示四个核心指标：总销售额、总订单数、客户总数、客单价。

### 四维筛选器
- **时间范围** — 日期选择器，可自定义起止日期
- **品类筛选** — 下拉选择单个品类或查看全部
- **地区筛选** — 下拉选择单个地区或查看全部
- **渠道筛选** — 下拉选择单个渠道或查看全部

所有图表会随筛选条件 **实时联动更新**。

### 图表区域
| 图表 | 说明 |
|------|------|
| 销售额趋势 | 柱状图+7日均线，观察整体走势 |
| 星期销售分布 | 工作日蓝色/周末红色，直观对比 |
| 品类贡献度 | 环形饼图，展示各品类收入占比 |
| 区域销售分布 | 柱状图，对比各区域销售额 |
| 复购率分析 | 柱状图，VIP/老客/新客复购率对比 |
| 品类月度趋势 | 多折线图，观察各品类走势和下滑趋势 |

---

## SQL 查询说明

`sql_queries.sql` 文件包含 10 个 MySQL 复杂查询，可直接在 MySQL 中执行。

### 使用方式

```bash
# 登录MySQL后执行
mysql -u root -p < sql_queries.sql

# 或者在MySQL客户端中
source sql_queries.sql
```

### 查询清单

| # | 查询名称 | 涉及技术 |
|---|---------|---------|
| 1 | 建表语句 | CREATE TABLE, INDEX, 字符集配置 |
| 2 | 月度销售汇总 | CTE, 同比/环比, DATE函数, 自连接 |
| 3 | 区域销售分析 | 多维GROUP BY, RANK窗口函数 |
| 4 | 品类贡献度趋势 | CTE双表关联, LAG窗口函数, 环比计算 |
| 5 | 客户复购率 | 子查询聚合, CASE WHEN, 人均LTV |
| 6 | 渠道效果分析 | 多维聚合, 平均折扣率 |
| 7 | 周末vs工作日 | 条件分组, 日期函数 |
| 8 | 支付方式分析 | 占比计算子查询 |
| 9 | RFM客户评分 | NTILE窗口函数, 加权评分, TOP N |
| 10 | 品类下滑预警 | LAG+SUM窗口函数, 连续下降检测, ROWS BETWEEN |

---

## 核心数据洞察

项目运行后会自动生成以下关键洞察：

### 1. 周末销售高峰
- 周末日均销售额比工作日高约 **40%~60%**
- **周六** 为全周销售最高峰
- **建议：** 在周五晚至周六集中投放促销资源，增加库存备货，优化物流配送能力

### 2. 品类下滑预警
- 通过月度趋势图识别连续多月销售额下降的品类
- 如运动户外在冬季持续下滑，图书文具在暑假期间低迷
- **建议：** 对下滑品类进行市场调研，考虑反季促销或与热门品类捆绑销售

### 3. VIP客户高价值
- VIP客户人均消费是新客的 **数倍**
- VIP复购率显著高于新客
- **建议：** 加强VIP维护计划，推出专属优惠和会员日活动，优化新客转化路径

### 4. 区域发展不均衡
- 华东、华南为核心销售区域
- 西北地区客单价和销售规模较低
- **建议：** 在低表现地区增加营销投入，复制高表现区域的成功策略

---

## 数据字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| order_id | VARCHAR | 订单编号，格式 `ORD-00000001` |
| order_date | DATETIME | 订单时间（精确到分钟） |
| category | VARCHAR | 商品品类（7类） |
| product | VARCHAR | 商品名称（42种） |
| region | VARCHAR | 区域（华东/华南/华北/华中/西南/东北/西北） |
| city | VARCHAR | 城市（33个） |
| channel | VARCHAR | 销售渠道（5种） |
| customer_id | VARCHAR | 客户ID（前缀区分VIP/老客/新客） |
| customer_type | VARCHAR | 客户类型：新客 / 老客 / VIP |
| unit_price | DECIMAL | 商品单价 |
| quantity | INT | 购买数量 |
| total_amount | DECIMAL | 总金额（单价×数量） |
| discount_rate | DECIMAL | 折扣率（0~0.5） |
| final_amount | DECIMAL | 实付金额 |
| payment_method | VARCHAR | 支付方式（微信/支付宝/银行卡/信用卡/现金/花呗） |
| order_status | VARCHAR | 订单状态（已完成/已退款/已取消/配送中） |

---

## 常见问题

### Q: 运行 `python main.py` 后报错 "ModuleNotFoundError"
**A:** 请确保已安装所有依赖：
```bash
pip install -r requirements.txt
```

### Q: 仪表板无法打开 / 端口被占用
**A:** 换一个端口：
```bash
python main.py --step dashboard --port 8051
```

### Q: PDF 报告生成失败
**A:** ReportLab 安装可能有问题，尝试：
```bash
pip install --upgrade reportlab
```
PDF 生成为可选功能，不影响其他分析流程。

### Q: 图表无法导出为 PNG
**A:** 需要安装 `kaleido`：
```bash
pip install kaleido
```
如果 kaleido 安装失败，图表仍会以 HTML 格式保存，不影响使用。

### Q: 如何连接 MySQL 执行 SQL 查询？
**A:** 先确保 MySQL 已启动，然后：
```bash
# 方式1：命令行导入
mysql -u root -p retail_sales_db < sql_queries.sql

# 方式2：Python 中通过 SQLAlchemy 连接
from sqlalchemy import create_engine
engine = create_engine("mysql+mysqlconnector://root:密码@localhost/retail_sales_db")
# 使用 pd.read_sql() 执行查询
```

### Q: 数据量太大，电脑运行慢？
**A:** 可以在 `generate_data.py` 中修改 `NUM_RECORDS` 值，例如改为 50000。

---

## 技术栈

| 类别 | 技术 |
|------|------|
| 数据处理 | Python, Pandas, NumPy, SciPy |
| 交互式可视化 | Plotly, Plotly Express |
| Web 仪表板 | Dash, Dash Bootstrap Components |
| 数据库 | MySQL 8.0+, SQLAlchemy |
| 报告生成 | ReportLab |
| 图表导出 | Kaleido |

---

## License

MIT License
