# 使用 Python 官方映像檔作為基礎
FROM python:3.10

# 設定工作目錄
WORKDIR /app

# 安裝 wget 和解壓縮工具
RUN apt-get update && apt-get install -y wget unzip

# 下載並安裝 ngrok
RUN wget https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-amd64.zip \
    && unzip ngrok-stable-linux-amd64.zip \
    && rm ngrok-stable-linux-amd64.zip \
    && mv ngrok /usr/local/bin \
    && chmod +x /usr/local/bin/ngrok

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
