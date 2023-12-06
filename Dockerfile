# 使用 Python 官方映像檔作為基礎
FROM python:3.10

# 設定工作目錄
WORKDIR /app

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
