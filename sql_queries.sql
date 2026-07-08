-- ============================================================
-- 零售销售分析 - SQL查询脚本
-- 适用于 MySQL 8.0+
-- ============================================================

-- ============================================================
-- 1. 建表语句
-- ============================================================
CREATE DATABASE IF NOT EXISTS retail_sales_db
CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE retail_sales_db;

DROP TABLE IF EXISTS retail_orders;

CREATE TABLE retail_orders (
    order_id        VARCHAR(20) PRIMARY KEY COMMENT '订单编号',
    order_date      DATETIME NOT NULL COMMENT '订单日期',
    category        VARCHAR(20) COMMENT '商品品类',
    product         VARCHAR(50) COMMENT '商品名称',
    region          VARCHAR(20) COMMENT '区域',
    city            VARCHAR(30) COMMENT '城市',
    channel         VARCHAR(20) COMMENT '销售渠道',
    customer_id     VARCHAR(30) COMMENT '客户ID',
    customer_type   VARCHAR(10) COMMENT '客户类型(新客/老客/VIP)',
    unit_price      DECIMAL(12,2) COMMENT '单价',
    quantity        INT COMMENT '数量',
    total_amount    DECIMAL(14,2) COMMENT '总金额',
    discount_rate   DECIMAL(5,4) COMMENT '折扣率',
    final_amount    DECIMAL(14,2) COMMENT '实付金额',
    payment_method  VARCHAR(20) COMMENT '支付方式',
    order_status    VARCHAR(10) COMMENT '订单状态',
    -- 时间维度派生字段
    year_val        INT COMMENT '年份',
    month_val       INT COMMENT '月份',
    quarter_val     INT COMMENT '季度',
    week_num        INT COMMENT '周数',
    day_of_week     INT COMMENT '星期几(0=周一)',
    is_weekend      TINYINT COMMENT '是否周末',
    year_month      VARCHAR(10) COMMENT '年月',
    INDEX idx_order_date (order_date),
    INDEX idx_category (category),
    INDEX idx_region (region),
    INDEX idx_customer (customer_id),
    INDEX idx_year_month (year_month),
    INDEX idx_status (order_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='零售销售订单表';


-- ============================================================
-- 2. 月度销售汇总（含同比环比）
-- ============================================================
WITH monthly_agg AS (
    SELECT
        year_month,
        SUM(final_amount) AS monthly_revenue,
        COUNT(order_id) AS monthly_orders,
        COUNT(DISTINCT customer_id) AS monthly_customers,
        AVG(final_amount) AS avg_order_value
    FROM retail_orders
    WHERE order_status = '已完成'
    GROUP BY year_month
)
SELECT
    a.year_month,
    a.monthly_revenue,
    a.monthly_orders,
    a.monthly_customers,
    a.avg_order_value,
    -- 环比增长率
    ROUND((a.monthly_revenue - b.monthly_revenue) / b.monthly_revenue * 100, 2) AS mom_growth_pct,
    -- 同比增长率
    ROUND((a.monthly_revenue - c.monthly_revenue) / c.monthly_revenue * 100, 2) AS yoy_growth_pct
FROM monthly_agg a
LEFT JOIN monthly_agg b ON b.year_month = DATE_FORMAT(DATE_SUB(STR_TO_DATE(CONCAT(a.year_month, '-01'), '%Y-%m-%d'), INTERVAL 1 MONTH), '%Y-%m')
LEFT JOIN monthly_agg c ON c.year_month = DATE_FORMAT(DATE_SUB(STR_TO_DATE(CONCAT(a.year_month, '-01'), '%Y-%m-%d'), INTERVAL 12 MONTH), '%Y-%m')
ORDER BY a.year_month;


-- ============================================================
-- 3. 区域销售分析（多维度交叉）
-- ============================================================
SELECT
    region,
    year_month,
    SUM(final_amount) AS revenue,
    COUNT(order_id) AS order_count,
    COUNT(DISTINCT customer_id) AS customer_count,
    ROUND(AVG(final_amount), 2) AS avg_order_value,
    ROUND(SUM(final_amount) / COUNT(DISTINCT customer_id), 2) AS revenue_per_customer,
    -- 区域内排名
    RANK() OVER (PARTITION BY year_month ORDER BY SUM(final_amount) DESC) AS region_rank
FROM retail_orders
WHERE order_status = '已完成'
GROUP BY region, year_month
ORDER BY year_month, revenue DESC;


-- ============================================================
-- 4. 品类贡献度分析（含趋势变化）
-- ============================================================
WITH cat_monthly AS (
    SELECT
        category,
        year_month,
        SUM(final_amount) AS revenue,
        COUNT(order_id) AS order_count
    FROM retail_orders
    WHERE order_status = '已完成'
    GROUP BY category, year_month
),
cat_total AS (
    SELECT
        year_month,
        SUM(revenue) AS total_revenue
    FROM cat_monthly
    GROUP BY year_month
)
SELECT
    a.category,
    a.year_month,
    a.revenue,
    a.order_count,
    ROUND(a.revenue / b.total_revenue * 100, 2) AS contribution_pct,
    -- 品类月环比
    ROUND((a.revenue - LAG(a.revenue) OVER (PARTITION BY a.category ORDER BY a.year_month))
          / LAG(a.revenue) OVER (PARTITION BY a.category ORDER BY a.year_month) * 100, 2) AS mom_change_pct
FROM cat_monthly a
JOIN cat_total b ON a.year_month = b.year_month
ORDER BY a.category, a.year_month;


-- ============================================================
-- 5. 客户复购率分析
-- ============================================================
WITH customer_stats AS (
    SELECT
        customer_id,
        customer_type,
        COUNT(order_id) AS total_orders,
        SUM(final_amount) AS total_spent,
        MIN(order_date) AS first_order_date,
        MAX(order_date) AS last_order_date,
        DATEDIFF(MAX(order_date), MIN(order_date)) AS customer_lifetime_days
    FROM retail_orders
    WHERE order_status = '已完成'
    GROUP BY customer_id, customer_type
)
SELECT
    customer_type,
    COUNT(*) AS total_customers,
    SUM(CASE WHEN total_orders > 1 THEN 1 ELSE 0 END) AS repeat_customers,
    ROUND(SUM(CASE WHEN total_orders > 1 THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) AS repurchase_rate_pct,
    ROUND(AVG(total_orders), 2) AS avg_orders_per_customer,
    ROUND(AVG(total_spent), 2) AS avg_lifetime_value,
    ROUND(AVG(customer_lifetime_days), 1) AS avg_lifetime_days
FROM customer_stats
GROUP BY customer_type
ORDER BY repurchase_rate_pct DESC;


-- ============================================================
-- 6. 渠道效果分析
-- ============================================================
SELECT
    channel,
    year_month,
    COUNT(order_id) AS orders,
    SUM(final_amount) AS revenue,
    COUNT(DISTINCT customer_id) AS customers,
    ROUND(AVG(final_amount), 2) AS avg_order_value,
    ROUND(AVG(discount_rate) * 100, 2) AS avg_discount_pct
FROM retail_orders
WHERE order_status = '已完成'
GROUP BY channel, year_month
ORDER BY year_month, revenue DESC;


-- ============================================================
-- 7. 周末 vs 工作日销售对比
-- ============================================================
SELECT
    CASE WHEN is_weekend = 1 THEN '周末' ELSE '工作日' END AS day_type,
    year_month,
    COUNT(order_id) AS order_count,
    SUM(final_amount) AS revenue,
    ROUND(AVG(final_amount), 2) AS avg_order_value,
    COUNT(DISTINCT customer_id) AS customer_count
FROM retail_orders
WHERE order_status = '已完成'
GROUP BY is_weekend, year_month
ORDER BY year_month, day_type;


-- ============================================================
-- 8. 支付方式分析
-- ============================================================
SELECT
    payment_method,
    COUNT(order_id) AS order_count,
    SUM(final_amount) AS total_revenue,
    ROUND(AVG(final_amount), 2) AS avg_amount,
    ROUND(COUNT(order_id) / (SELECT COUNT(*) FROM retail_orders WHERE order_status = '已完成') * 100, 2) AS pct_of_orders
FROM retail_orders
WHERE order_status = '已完成'
GROUP BY payment_method
ORDER BY total_revenue DESC;


-- ============================================================
-- 9. 高价值客户 TOP 100（RFM模型简化版）
-- ============================================================
SELECT
    customer_id,
    customer_type,
    COUNT(order_id) AS frequency,
    SUM(final_amount) AS monetary,
    MAX(order_date) AS recency_date,
    DATEDIFF(NOW(), MAX(order_date)) AS recency_days,
    -- RFM综合评分
    ROUND(
        NTILE(5) OVER (ORDER BY DATEDIFF(NOW(), MAX(order_date)) ASC) * 0.3 +
        NTILE(5) OVER (ORDER BY COUNT(order_id) ASC) * 0.3 +
        NTILE(5) OVER (ORDER BY SUM(final_amount) ASC) * 0.4
    , 2) AS rfm_score
FROM retail_orders
WHERE order_status = '已完成'
GROUP BY customer_id, customer_type
ORDER BY rfm_score DESC
LIMIT 100;


-- ============================================================
-- 10. 品类下滑预警（连续N月环比下降的品类）
-- ============================================================
WITH cat_monthly AS (
    SELECT
        category,
        year_month,
        SUM(final_amount) AS revenue
    FROM retail_orders
    WHERE order_status = '已完成'
    GROUP BY category, year_month
),
cat_mom AS (
    SELECT
        category,
        year_month,
        revenue,
        LAG(revenue) OVER (PARTITION BY category ORDER BY year_month) AS prev_revenue,
        revenue - LAG(revenue) OVER (PARTITION BY category ORDER BY year_month) AS mom_change
    FROM cat_monthly
),
decline_streak AS (
    SELECT
        category,
        year_month,
        revenue,
        mom_change,
        SUM(CASE WHEN mom_change < 0 THEN 1 ELSE 0 END)
            OVER (PARTITION BY category ORDER BY year_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS consecutive_declines
    FROM cat_mom
    WHERE prev_revenue IS NOT NULL
)
SELECT
    category,
    year_month,
    revenue,
    ROUND(mom_change, 2) AS month_over_month_change,
    consecutive_declines
FROM decline_streak
WHERE consecutive_declines >= 2
ORDER BY year_month DESC, category;
