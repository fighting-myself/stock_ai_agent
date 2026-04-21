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

### 方式一：分别构建与运行（同一网络）

先创建网络（只需一次）：

```bash
docker network create stock-ai-net
```

后端：

```bash
docker build -t stock-ai-backend:v1 -f backend/Dockerfile .
docker run -d --name stock-backend --network stock-ai-net -p 8001:8001 --env-file .env stock-ai-backend:v1
```

前端：

```bash
docker build -t stock-ai-frontend:v1 -f frontend/Dockerfile .
docker run -d --name stock-frontend --network stock-ai-net -p 6006:6006 -e BACKEND_URL=http://stock-backend:8001 stock-ai-frontend:v1
```

说明：前端容器通过容器名 `backend` 访问后端，依赖同一 Docker 网络下的内置 DNS 解析。

### 方式二：docker compose（推荐）

```bash
docker compose up --build
```

启动后：

- 后端健康检查：`http://localhost:8000/health`
- 前端页面：`http://localhost:6006`
