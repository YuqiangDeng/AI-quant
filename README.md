# AI-quant

量化交易学习与研究仓库（武汉大学 · 金融商业数据分析方向）。

本仓库内含一个逐步成长的 **量化作品集站点 `AI-quant-lab/`**——从基础认知到完整策略回测，每完成一个 Task 就把它作为一个独立模块加进站点，首页做统一导航。

---

## 作品集站点（AI-quant-lab）

一个**纯静态、零构建、可离线**的量化作品集，部署在 GitHub Pages。

- 站点首页：`AI-quant-lab/index.html`
- 线上地址（启用 Pages 后）：`https://yuqiangdeng.github.io/AI-quant/AI-quant-lab/`
- 本地预览：双击 `AI-quant-lab/index.html` 即可（无需联网；图表库已本地化）

### 作品清单

| 模块 | 路径 | 类型 | 说明 |
|------|------|------|------|
| **Task1** 量化交易基础报告 | `task1/` | 报告页 | 量化交易入门、市场微观结构、基础指标认知 |
| **Task2** 技术指标实验室 | `task2/indicator-tool/` | 交互工具 | MA / MACD / RSI / KDJ 等指标算法演示与参数实验（本地 Chart.js） |
| **Task2** 报告 | `task2/index.html` | 报告页 | Task2 文字报告 |
| **Task3** 双均线策略看板 | `task3/task3_dashboard.html` | 交互看板 | 双均线/唐奇安择时，多标的、可配参数、回测与可视化（内联 Plotly） |
| **Task3** 报告 | `task3/report.html` | 报告页 | Task3 文字报告 |
| **Task4** 海龟交易法则看板 | `turtle-trading/task4_turtle_dashboard.html` | 交互看板 | N/ATR 头寸管理 + 唐奇安突破，多标的回测 + 每日自动更新 |
| **Task4** 双均线指南 | `turtle-trading/guide.html` | 文档页 | 双均线策略说明（内联 Plotly） |
| **行情数据看板** | `market/` | 交互看板 | 比亚迪 / 美的 / 中芯A / 中芯A-H 对比 K 线（ECharts/Plotly） |

### 站点架构

```
AI-quant-lab/
├── index.html                 # 作品集首页（导航中枢）
├── assets/                    # 全站共享资源
│   ├── site.css               #   统一视觉样式
│   ├── nav.js                 #   顶部导航 + 页脚注入（报告/首页用）
│   ├── back.js                #   「🏠 作品集」返回浮标（看板页用）
│   └── vendor/
│       ├── plotly.min.js      #   本地 Plotly（turtle / task3 / guide 用）
│       └── chart.umd.js       #   本地 Chart.js（indicator-tool 用）
├── task1/index.html           # Task1 报告（pandoc 由 docx 生成）
├── task2/
│   ├── index.html             # Task2 报告
│   └── indicator-tool/        # Task2 交互工具（index.html + data.js）
├── task3/
│   ├── task3_dashboard.html   # Task3 双均线看板
│   └── report.html            # Task3 报告
├── turtle-trading/            # Task4 海龟看板（详见下）
└── market/                    # 行情数据看板（4 个个股页）
```

### 如何新增一个策略 / 作品（扩展方式）

站点为**静态多页（MPA）**，新增作品 = 建目录 + 写页面 + 在首页加一张卡片，无需改动框架：

1. 在 `AI-quant-lab/` 下新建模块目录，如 `my-strategy/`；
2. 页面内引入共享导航：
   - 报告/首页类：末尾加
     ```html
     <script>window.__BASE="../";</script>
     <script src="../assets/nav.js"></script>
     ```
   - 看板类（自带复杂布局）：末尾加
     ```html
     <script>window.__BASE="../";</script>
     <script src="../assets/back.js"></script>
     ```
   （两层深的目录用 `../../`）
3. 图表库优先用本地 `assets/vendor/` 下的 Plotly / Chart.js，保证离线可用；
4. 在 `index.html` 对应区块复制一张 `.card`，改标题、描述、链接即可。

> 约定：图表库统一放 `assets/vendor/` 复用，避免每个模块重复打包数百 KB 体积。

---

## 海龟交易法则看板（AI-quant-lab/turtle-trading）

### 功能

| 模块 | 说明 |
|------|------|
| 标的 | 中芯国际A(688981.SH)、比亚迪(002594.SZ)、长江电力(600900.SH)、美的集团(000333.SZ)、中芯国际H(00981.HK) |
| 时段 | 自选起止日期（YYYYMMDD），快捷按钮：近1年 / 近3年 / 全部 |
| 系统 | S1（20日突破/10日离场）、S2（55日突破/20日离场）、S1+S2 组合（40%/60%） |
| 参数 | N周期(ATR)、风险比例、初始资金、加仓间距×N、最大单位数、止损倍数×N、无风险利率、手续费、允许做空 |
| 指标 | 累计/年化收益、夏普比率、最大回撤、胜率、盈亏比、期望收益、交易次数、相对买入持有超额、**峰值持有单位(每系统≤4)、平均持有单位、单笔最大亏损%**（用于校验风控纪律） |
| 可视化 | K线+唐奇安通道+买卖(红)/加仓(橙)/止损(✕)点、资金曲线、回撤曲线、N(ATR)曲线、交易明细表 |
| 系统说明 | 点右上「📖 海龟系统说明」展开：**五大核心要素**、**ATR 公式与含义（正常波动/跳空高低开）**、**头寸规模公式**、**风控纪律**、**海龟交易法则流程图（离线 SVG）** |

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
- **`Deploy Pages`** —— 把整个 `AI-quant-lab/` 部署到 GitHub Pages。

启用步骤（仓库 Settings → Pages → Build and deployment → Source 选 **GitHub Actions**）。

> **注意（CI 数据源限制）**：海龟看板数据来自 akshare 新浪/东财源，这些源多对境外 IP 限连。GitHub Actions 运行于境外服务器时，**A 股/港股增量抓取可能失败**——此时脚本会优雅跳过（exit 0），流水线不中断，但不会产生新数据。
> 因此：**在中国境内本机运行 `update_turtle_data.py` 后再推送**，是获取真实每日增量最可靠的方式；GitHub 侧定时任务则保证流水线结构完整、并在可抓取时自动更新。

---

## 数据说明

- 行情为**前复权**（qfq）日线，标准字段：`ts_code, trade_date, open, high, low, close, pre_close, change, pct_chg, vol, amount`
- 数据仅用于教学与策略演示，不构成任何投资建议。
