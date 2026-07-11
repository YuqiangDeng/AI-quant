# AI-quant

量化交易学习与研究仓库（武汉大学 · 金融商业数据分析方向）。

本仓库目前包含：

- **`AI-quant-lab/turtle-trading/`** —— 海龟交易法则（Turtle Trading Rules）回测演示看板
  - 自包含、可离线运行的 HTML 看板（内联 Plotly + 纯 JS 海龟回测引擎）
  - 支持：多标的切换、时段选择、海龟参数配置（S1 / S2 / 组合）、回测指标、交易点位与可视化、每日数据增量更新
  - 详见下方说明

---

## 海龟交易法则看板（AI-quant-lab/turtle-trading）

### 功能

| 模块 | 说明 |
|------|------|
| 标的 | 中芯国际A(688981.SH)、比亚迪(002594.SZ)、长江电力(600900.SH)、美的集团(000333.SZ)、中芯国际H(00981.HK) |
| 时段 | 自选起止日期（YYYYMMDD），快捷按钮：近1年 / 近3年 / 全部 |
| 系统 | S1（20日突破/10日离场）、S2（55日突破/20日离场）、S1+S2 组合（40%/60%） |
| 参数 | N周期(ATR)、风险比例、初始资金、加仓间距×N、最大单位数、止损倍数×N、无风险利率、手续费、允许做空 |
| 指标 | 累计/年化收益、夏普比率、最大回撤、胜率、盈亏比、期望收益、交易次数、相对买入持有超额 |
| 可视化 | K线+唐奇安通道+买卖/加仓点、资金曲线、回撤曲线、N(ATR)曲线、交易明细表 |

### 核心算法（海龟法则）

- **N = ATR(20)** —— Wilder 平滑真实波幅，衡量波动
- **单位头寸 Unit** = (账户权益 × 风险%) ÷ N
- **入场** —— 价格突破 N 日唐奇安通道上轨
- **加仓** —— 每上涨 0.5N 加 1 单位，最多 4 单位
- **止损** —— 2N（价格回撤 2N 离场）
- **离场** —— 价格跌破 N 日唐奇安通道下轨
- A 股默认多头（不允许做空），可在看板勾选「允许做空」体验对称逻辑

### 本地运行

```bash
cd AI-quant-lab/turtle-trading
# 1) 更新数据（可选，需能访问 akshare 数据源）
python update_turtle_data.py
# 2) 生成看板 HTML（读取 data/，输出 task4_turtle_dashboard.html）
python gen_task4_turtle_dashboard.py
# 3) 浏览器直接打开 task4_turtle_dashboard.html
```

> 看板为纯静态文件，用浏览器打开即可，无需联网（Plotly 已本地内联于 `vendor/`）。

### 每日自动化（GitHub Actions）

- **`Daily Update`** —— 每天北京时间 06:00 自动拉取最新交易日数据（增量追加），并重生成看板 HTML，提交回 `main`。
- **`Deploy Pages`** —— 把 `AI-quant-lab/turtle-trading/` 部署到 GitHub Pages。

启用步骤（仓库 Settings → Pages → Build and deployment → Source 选 **GitHub Actions**）。

> **注意（CI 数据源限制）**：海龟看板数据来自 akshare 新浪/东财源，这些源多对境外 IP 限连。GitHub Actions 运行于境外服务器时，**A 股/港股增量抓取可能失败**——此时脚本会优雅跳过（exit 0），流水线不中断，但不会产生新数据。
> 因此：**在中国境内本机运行 `update_turtle_data.py` 后再推送**，是获取真实每日增量最可靠的方式；GitHub 侧定时任务则保证流水线结构完整、并在可抓取时自动更新。

### 目录结构

```
AI-quant-lab/turtle-trading/
├── data/                       # 前复权日线 CSV（标准字段）
│   ├── byd_daily_qfq.csv
│   ├── midea_daily_qfq.csv
│   ├── smic_daily_qfq.csv
│   ├── smic_hk_daily.csv
│   └── yangtze_power_daily_qfq.csv
├── vendor/plotly.min.js        # 本地内联 Plotly（离线可用）
├── task4_turtle_dashboard.html # 看板（自包含，双击即用）
├── gen_task4_turtle_dashboard.py  # 看板生成器
├── update_turtle_data.py          # 每日数据增量更新
└── (见 .github/workflows 自动化)
```

---

## 数据说明

- 行情为**前复权**（qfq）日线，标准字段：`ts_code, trade_date, open, high, low, close, pre_close, change, pct_chg, vol, amount`
- 数据仅用于教学与策略演示，不构成任何投资建议。
