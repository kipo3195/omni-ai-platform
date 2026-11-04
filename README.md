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

# 개발환경의 Returned Message Topics prompt/결과 payload 로그 활성화
# prompt에 메시지 제목이 포함되므로 운영환경에서는 반드시 production으로 설정한다.
APP_ENV=development
