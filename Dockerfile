# 使用輕量級的 Python 基礎鏡像
FROM python:3.11-slim

# 設定環境變數
# - PYTHONUNBUFFERED: 確保 Python 輸出直接印到終端機，方便查看 Docker 日誌
# - PYTHONDONTWRITEBYTECODE: 避免產生 .pyc 暫存檔
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Taipei

# 設定工作目錄
WORKDIR /app

# 安裝系統依賴：
# - tzdata: 用於設定容器時區
# - fonts-wqy-microhei: 安裝文泉驛微米黑字型，確保浮水印能正確顯示中文 (不會出現亂碼/方塊)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    fonts-wqy-microhei \
    && ln -fs /usr/share/zoneinfo/${TZ} /etc/localtime \
    && echo ${TZ} > /etc/timezone \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 先複製 requirements.txt 進行套件安裝（善用 Docker 快取機制）
COPY requirements.txt .

# 安裝 Python 專案依賴套件
RUN pip install --no-cache-dir -r requirements.txt

# 複製專案程式碼與相關檔案
COPY . .

# 建立非 root 的系統使用者來執行 Bot，提升安全性
RUN useradd -u 10001 -m -s /bin/bash appuser && \
    chown -R appuser:appuser /app

# 切換到該安全使用者
USER appuser

# 啟動 Discord Bot
CMD ["python", "bot.py"]
