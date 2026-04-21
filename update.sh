docker stop stock-frontend stock-backend
docker rm stock-frontend stock-backend
docker build -t stock-ai-backend:v1 -f backend/Dockerfile .
docker build -t stock-ai-frontend:v1 -f frontend/Dockerfile .
docker run -d --name stock-frontend --network stock-ai-net -p 6006:6006 -e BACKEND_URL=http://stock-backend:8001 stock-ai-frontend:v1
docker run -d --name stock-backend --network stock-ai-net -p 8001:8001 --env-file .env stock-ai-backend:v1