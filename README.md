# stock_ai_agent（前后端分离版）

项目已拆分为前后端独立入口：

- 后端（FastAPI）：`backend/main.py`
- 前端（Streamlit）：`frontend/app.py`

为兼容原有命令，根目录保留了薄包装入口：

- `main.py` -> 转发到 `backend.main:app`
- `frontend.py` -> 转发到 `frontend.app`

## 目录结构

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
├─ docker-compose.yml
├─ main.py
└─ frontend.py
```

## 本地启动（开发）

### 1) 启动后端

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 2) 启动前端

```bash
streamlit run frontend/app.py --server.port 6006 --server.address 0.0.0.0
```

默认前端请求 `http://localhost:8000`，也可以通过环境变量覆盖：

```bash
set BACKEND_URL=http://localhost:8000
```

## Docker 部署

### 方式一：分别构建与运行

后端：

```bash
docker build -t stock-ai-backend -f backend/Dockerfile .
docker run --rm -p 8000:8000 --env-file .env stock-ai-backend
```

前端：

```bash
docker build -t stock-ai-frontend -f frontend/Dockerfile .
docker run --rm -p 6006:6006 -e BACKEND_URL=http://host.docker.internal:8000 stock-ai-frontend
```

### 方式二：docker compose（推荐）

```bash
docker compose up --build
```

启动后：

- 后端健康检查：`http://localhost:8000/health`
- 前端页面：`http://localhost:6006`
