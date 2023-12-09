# 使用 Python 官方映像檔作為基礎
FROM python:3.10

# 設定工作目錄
WORKDIR /app

# 安裝 wget 和解壓縮工具
RUN apt-get update && apt-get install -y wget unzip

# 下載並安裝 ngrok
RUN curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null \
    && echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | tee /etc/apt/sources.list.d/ngrok.list \
    && apt-get update \
    && apt-get install -y ngrok \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 複製依賴文件
COPY requirements.txt ./

# 安裝依賴
RUN pip install -r requirements.txt

# 複製項目文件
COPY src/ .

# 暴露端口 8000
EXPOSE 8000

# 指定默認執行命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
