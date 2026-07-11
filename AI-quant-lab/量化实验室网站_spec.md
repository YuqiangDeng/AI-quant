# 量化实验室网站（AI-quant-lab）规划与规格 v1.0

> 目标：把零散的量化策略看板，整合为一个**可长期扩展的静态网站**。
> 首页是导航中枢，每个策略是一个独立、自包含、可离线运行的模块，未来逐个往里加。
> 部署：GitHub Pages，零构建、零后端。

---

## 1. 定位与原则

| 项 | 说明 |
|----|------|
| 定位 | 个人量化策略作品集 / 学习实验室的对外网站 |
| 核心原则 | 每个策略**自包含可运行**；新增策略**低门槛、标准化**；**零构建**直接上 Pages |
| 复用 | 直接复用已验证的 task3（双均线）、task4（海龟）范式：自包含 HTML + 内联 Plotly + Python 生成/取数 |
| 受众 | 自己学习复盘 + 给老师/同学展示（可离线发文件，也可在线看 Pages） |

---

## 2. 技术选型（推荐及理由）

- **静态多页（MPA），不用 React/Vue 等 SPA 框架**
  - 理由：您量化零基础、时间有限、无 Node 构建经验；现有看板已是纯 HTML；GitHub Pages 原生支持静态文件，无需 CI 构建步骤之外的任何东西。
- **可视化**：Plotly.js（沿用），内联或共享一份。
- **语言**：纯 HTML/CSS/JS（页面）+ Python（取数/生成脚本），与现有完全一致。
- **数据**：前复权日线 CSV（标准字段），放各模块 `data/`。

> 若未来策略变复杂（需服务端计算/数据库），再升级架构；现阶段静态足够。

---

## 3. 目录结构（目标态）

```
AI-quant-lab/
├── index.html                 # 首页：策略卡片导航中枢
├── assets/
│   ├── site.css               # 共享主题/布局样式
│   ├── nav.js                 # 共享顶部导航（站点名 + 返回首页 + 当前策略名）
│   └── vendor/
│       └── plotly.min.js      # 共享 Plotly（避免每个模块重复 4.5MB）
├── strategies.json            # 策略清单（驱动首页卡片，新增策略只改这一处）
├── turtle-trading/            # 策略模块①：海龟交易法则（已有，待迁入）
│   ├── index.html             # 由 task4_turtle_dashboard.html 改名而来
│   ├── data/                  # 5 只标的真前复权日线
│   ├── gen_task4_turtle_dashboard.py
│   └── update_turtle_data.py
├── dual-ma/                   # 策略模块②：双均线（task3，待迁入）
│   ├── index.html
│   ├── gen_task3_dashboard.py
│   └── ...
└── <future-strategy>/         # 未来策略逐个加（均值回归/布林带/动量…）
```

- 站点根：`https://<user>.github.io/AI-quant/`
- 首页：`/index.html`；策略页：`/turtle-trading/`、`/dual-ma/` …

---

## 4. 策略模块契约（contract）

每个策略模块目录 **必须 / 建议** 包含：

| 内容 | 要求 | 说明 |
|------|------|------|
| `index.html` | 必须 | 看板主文件；通过相对路径引用 `../assets/site.css`、`../assets/nav.js`、`../assets/vendor/plotly.min.js` |
| `data/` | 必须 | 该策略数据（标准前复权字段：`ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount`） |
| `update_*.py` | 建议 | 每日增量更新（akshare 新浪源，仅追加 > 末行日期行，幂等，失败优雅退出） |
| `gen_*.py` | 建议 | HTML 生成器（读 data/ → 注入数据 + 内联引擎 → 输出 index.html） |
| `strategies.json` 注册 | 必须 | 加一条记录（见下） |

**`strategies.json` 单条记录示例：**
```json
{
  "slug": "turtle-trading",
  "name": "海龟交易法则",
  "tag": "趋势跟随",
  "desc": "唐奇安突破 + N=ATR 头寸管理，S1/S2/组合回测",
  "color": "#185FA5",
  "status": "ready",
  "lastUpdated": "2026-07-11"
}
```
`status` 取值：`ready`（可用）/ `wip`（施工中）/ `demo`（示例）。

---

## 5. 首页设计

- **顶部**：站点名 `AI-quant-lab` + 一句话简介（"我的量化策略实验室"）+ GitHub 链接。
- **主体**：策略卡片网格，由 `strategies.json` 动态渲染：
  - 卡片显示：名称、**一句话描述**、标签（如"趋势跟随 / 均值回归"）、最近更新日期、**状态徽标**、「打开看板 →」按钮。
  -  hover/点击进入对应 `/<slug>/`。
- **底部**：数据说明（前复权、来源 akshare）+ 免责声明（仅教学，非投资建议）+ 技术栈（静态 HTML / Plotly / GitHub Pages）。
- **响应式**：卡片网格 `auto-fit minmax`，手机也可看。
- **导航**：每张策略页顶部由 `nav.js` 注入「← 返回首页」+ 站点名。

---

## 6. 共享资产与主题

- `site.css`：统一配色（沿用 task4 蓝白科技风 `--blue:#185FA5`、卡片、涨红跌绿）、统一卡片/按钮/响应式栅格。
- `nav.js`：极简脚本，注入统一顶栏（站点名 + 返回首页链接 + 当前策略名由 `data-strategy` 属性读取）。
- 模块 HTML 用相对路径引用 `../assets/...`，保证**离线 file:// 打开也能用**（需整棵树在一起）。

---

## 7. 数据更新自动化（GitHub Actions）

- **统一入口 `daily_update.yml`**：遍历各模块约定命名的 `update_*.py` 并运行，随后对受影响的模块重跑 `gen_*.py` 重新生成 `index.html`，统一 `git commit` 回 `main`。
  - 命名约定：`AI-quant-lab/<slug>/update_<slug>.py`、`gen_<slug>.py`，workflow 用 glob 发现。
- 初期简单起见：先保留 turtle 的 `update_turtle_data.py`，新增模块时再补齐各自的更新脚本。
- 触发：北京时间 06:00 定时 + `workflow_dispatch` 手动。
- 已知限制：akshare 新浪/东财源对境外 IP 易限连，GitHub Actions（美西）抓取可能失败 → 脚本优雅跳过；**最可靠增量更新仍是在中国本机跑 `update_*.py` 后推送**。

---

## 8. 部署（GitHub Pages）

- **`pages.yml` 改为部署整个 `AI-quant-lab/` 根目录**（而非仅 `turtle-trading/`），使首页 `index.html` 成为站点根。
- 启用：仓库 Settings → Pages → Source 选 **GitHub Actions**。
- 旧链接 `…/turtle-trading/task4_turtle_dashboard.html` 在改名后将失效，统一改为 `…/turtle-trading/`（即 `index.html`）。

---

## 9. 迁移现有成果（把已做的两份看板搬进体系）

1. **task4 海龟** → `turtle-trading/index.html`（由 `task4_turtle_dashboard.html` 改名），内部引用改为 `../assets/vendor/plotly.min.js`、`../assets/site.css`、`../assets/nav.js`；注册 `strategies.json`。
2. **task3 双均线** → 新建 `dual-ma/`，把现有 `task3_dashboard.html` 迁入为 `dual-ma/index.html`，同样改共享引用；注册 `strategies.json`。
3. **Plotly** → 从各模块抽出一份放到 `assets/vendor/plotly.min.js`，各模块改引用（见第 10 节决策点）。

> 迁入后首页立即可见 **2 个策略卡片**（海龟 + 双均线），示范"逐个加"的范式。

---

## 10. 实施路线（分阶段）

| 阶段 | 内容 | 产出 |
|------|------|------|
| **P0** | 建 `assets/`（site.css / nav.js / vendor/plotly.min.js）+ `strategies.json` + 首页 `index.html` 骨架 | 空站点可访问 |
| **P1** | 迁入 turtle-trading（改名 index.html + 改共享引用 + 注册 json） | 首页 1 卡片 |
| **P2** | 迁入 dual-ma（task3） | 首页 2 卡片 |
| **P3** | 调整两个 workflow（pages 部署根目录；daily_update 支持多模块） | 自动化覆盖全站 |
| **P4+** | 后续策略逐个加：建 `<slug>/` + 写 `gen_*.py`/`update_*.py` + 注册 json | 网站持续长大 |

每加一个策略 = **建目录 + 写生成/取数脚本 + 在 strategies.json 加一条**，无需改首页代码。

---

## 11. 待确认决策点（请主人拍板）

1. **共享 vendor vs 每模块自包含**
   - 推荐 **共享** `assets/vendor/plotly.min.js`（避免 4.5MB × N 重复，仓库更干净）。
   - 代价：单模块不再能"只发一个文件夹"给别人（需连带 `assets/`）。如需可移植性则保留各自 `vendor/`。
2. **首页卡片渲染方式**
   - 推荐 **`strategies.json` 动态渲染**（加策略只改 JSON，不动 HTML）。
   - 备选：手写 HTML 卡片（更简单但每次加策略要改两处）。
3. **是否现在就把 task3 双均线也迁入**
   - 推荐 **是**，首页立刻有 2 个策略，范式更完整。
4. **站点名 / 风格**
   - 暂用 `AI-quant-lab` + 蓝白科技风；如需中文名（如"小果的量化实验室"）请告知。

---

## 12. 风险与注意

- 共享 vendor 后，离线发单模块需连带 `assets/` 一起发。
- Pages 根目录切换后，旧 `/turtle-trading/task4_turtle_dashboard.html` 链接失效 → 统一用 `/turtle-trading/`。
- akshare 境外限连（同前），CI 侧抓取可能空跑；本机推送最稳。
- 所有数据仅教学演示，不构成投资建议（首页底部固定声明）。
