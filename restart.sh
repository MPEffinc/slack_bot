docker stop ccbot 2>/dev/null

docker rm ccbot 2>/dev/null

docker build -t ccbot .

docker run -d \
  --name ccbot \
  --env-file tokens.env \
    -p 8080:8080 \
  --restart always \
  -e TZ=Asia/Seoul \
  ccbot
