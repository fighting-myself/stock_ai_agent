# stock_ai_agent（前后端分离 + 多数据源 + 投研工作流）

一个面向金融投资分析的 AI 助手项目，支持：

- FastAPI 后端 + Streamlit 前端
- Tushare 与 Eastmoney 免费接口自动切换
- 技术指标、风险评估、组合分析、轮动比较
- 深度研报、专家辩论、事件冲击分析
- 一键投研策略工作流（仓位、风控、执行计划）

## 项目结构

```text
stock_ai_agent/
├─ backend/
│  ├─ main.py
│  ├─ requirements.txt
│  └─ Dockerfile
├─ frontend/
│  ├─ app.py
│  ├─ requirements.txt
│  └─ Dockerfile
├─ data/
│  ├─ tushare_client.py
│  ├─ eastmoney_api.py
│  └─ calculator.py
├─ docker-compose.yml
├─ main.py
└─ frontend.py
```

> 兼容入口：  
> `main.py` -> `backend.main:app`  
> `frontend.py` -> `frontend.app`

## 启动方式

### 本地开发

后端（8001）：

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8001
```

前端（6006）：

```bash
streamlit run frontend/app.py --server.port 6006 --server.address 0.0.0.0
```

前端默认请求 `http://localhost:8001`，也可通过环境变量覆盖：

```bash
set BACKEND_URL=http://localhost:8001
```

### Docker（推荐 compose）

```bash
docker compose up --build
```

启动后：

- 后端健康检查：`http://localhost:8001/health`
- 前端页面：`http://localhost:6006`

## 数据源策略（自动回退）

当前采用“主源 + 备用源”策略：

- 主源：Tushare
- 备用：Eastmoney（免费）

当主源权限不足、限流或异常时，会自动切换备用源，常见场景：

- 行情快照/实时价：Tushare -> Eastmoney
- 历史日线：Tushare -> Eastmoney K 线
- 估值数据：Tushare `daily_basic` -> Eastmoney 字段

返回结果中通常包含 `source` 字段，表示命中数据源。

## 主要功能（API）

### 基础与量化面板

- `GET /api/market/quote`
- `GET /api/market/history`
- `GET /api/indicator/technical`
- `GET /api/indicator/bollinger`
- `GET /api/indicator/kdj`
- `GET /api/risk/summary`
- `GET /api/risk/var`
- `GET /api/strategy/support-resistance`
- `GET /api/fundamental/valuation`
- `GET /api/workbench/overview`

### 投资分析扩展

- `GET /api/alt/polymarket`
- `GET /api/alert/market-volatility`
- `POST /api/research/deep-report`
- `POST /api/research/expert-debate`
- `GET /api/analysis/technical-score`
- `POST /api/analysis/scenario-impact`
- `POST /api/portfolio/rebalance`
- `GET /api/analysis/sentiment-proxy`
- `GET /api/analysis/ma-backtest`
- `GET /api/analysis/rotation`
- `POST /api/workflow/investment-plan`（一键投研策略工作流）

## 前端功能导航

前端包含两大功能区：

- 金融功能面板（工作台总览 + 10 个常用量化功能）
- 高级投资分析（新增 10 项扩展能力 + 投研策略工作流）

其中“投研策略工作流”会自动输出：

- 市场状态（评分、风险等级、预警）
- 建议仓位（目标仓位 / 现金比例）
- 执行计划（动作、止损止盈、复盘周期）
- 风控检查清单
- LLM 执行摘要
