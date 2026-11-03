# 이미지 생성 
docker build --platform linux/amd64 -t messenger-ai-platform-v1:latest .

# 이미지 -> tar 
docker save -o ./omni-ai-platform-latest.tar omni-ai-platform:latest

# 서비스 실행 
docker run \
  --restart unless-stopped \
  --env-file .env \
  -p 8000:8000 \
  omni-ai-platform:latest