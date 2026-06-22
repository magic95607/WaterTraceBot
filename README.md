# Discord 檔案浮水印 & 洩漏追蹤 Bot 🤖

這是一個基於 Python 與 `discord.py` (v2.x) 開發的 Discord Bot，能夠自動或手動為上傳的圖片加上**動態個人化浮水印**，專門用於**追溯與追蹤圖片洩漏源頭 (Leak Tracing)**。

---

## ✨ 核心特色與洩漏追蹤原理

一般浮水印只能防止直接右鍵下載無水印圖片，但若所有人都下載同一張「一般浮水印圖」，一旦圖檔外流，管理員依然無法得知是「哪一個帳號」洩漏的。

為了實現精準的**洩漏追蹤 (Leak Tracing)**，本 Bot 實作了以下機制：

### 🔒 洩漏追蹤運作機制 (按鈕式專屬加密下載)
1.  **管理員發布圖片**：管理員在啟用監聽的頻道（如 `#作品展示`）上傳原圖。
2.  **自動攔截與原圖備份**：
    *   Bot 自動攔截該訊息，並將無浮水印的**原圖上傳至管理員專用的私密備份頻道**（如 `#原圖備份`）。
    *   Bot 立即**刪除公開頻道中的原圖訊息**，不留任何痕跡。
3.  **公開預覽與按鈕生成**：
    *   Bot 在公開頻道中發送一條預覽訊息，下方附帶一個 **「📥 取得專屬加密原圖」** 的按鈕。
4.  **動態專屬浮水印生成**：
    *   當成員（例如成員 A）點擊該按鈕時，Bot 會從備份伺服器中撈取原圖。
    *   **在記憶體中即時生成該成員專屬的浮水印**（內容包含：`UID: 成員A的DiscordID | 帳號名稱 | 下載時間`），並以極低透明度 (8%) 平鋪滿版覆蓋圖片。
    *   Bot 透過 **Ephemeral 訊息 (僅點擊按鈕的成員本人可看見)** 將這張專屬圖片發送給他。
5.  **洩漏追溯**：
    *   如果網路上出現了外流圖片，管理員只需將該圖片存下，**調高圖片對比度 (Contrast)**，即可清晰看見畫面上平鋪的 Discord ID，進而直接抓出是哪一個帳號將圖檔流出去！

---

## 📂 目錄結構
```text
discord-file/
├── .env.example          # 環境變數設定範本
├── config.json           # Bot 的參數設定檔 (自動產生)
├── images.json           # 儲存預覽訊息與備份原圖對應關係的資料庫 (自動產生)
├── requirements.txt      # Python 依賴庫
├── watermark.py          # 影像浮水印處理核心邏輯 (Pillow)
├── bot.py                # Discord Bot 主程式 (事件、按鈕與指令)
└── README.md             # 本說明文件
```

---

## 🛠️ 安裝與準備步驟

### 步驟 1：取得 Discord Bot Token 與設定權限
1.  前往 [Discord Developer Portal](https://discord.com/developers/applications)。
2.  建立 Application，並在 **Bot** 頁面中：
    *   點擊 **Reset Token** 取得您的 Bot Token。
    *   向下滾動找到 **Privileged Gateway Intents**，將 **Message Content Intent** (訊息內容意圖) 設為 **ON** (極重要！否則無法讀取上傳的圖片)。
3.  前往 **OAuth2** -> **URL Generator** 頁面：
    *   在 **Scopes** 中勾選 `bot` 與 `applications.commands`。
    *   在下方 **Bot Permissions** 中勾選以下權限：
        *   `Read Messages/View Channels` (檢視頻道)
        *   `Send Messages` (發送訊息)
        *   `Manage Messages` (管理訊息 - 自動防護刪除原圖所需)
        *   `Read Message History` (讀取歷史訊息)
        *   `Attach Files` (附加檔案 - 發送專屬水印圖所需)
    *   複製最下方的 **Generated URL**，貼到瀏覽器中將 Bot 邀請至您的伺服器。

### 步驟 2：設定本地環境
1.  複製 `.env.example` 並重新命名為 `.env`。
2.  將您的 Bot Token 填入：
    ```env
    DISCORD_TOKEN=您的_DISCORD_BOT_TOKEN
    ```

### 步驟 3：安裝依賴並啟動
在專案根目錄下執行：

```bash
# 1. 建立虛擬環境 (建議)
python -m venv venv

# 2. 啟用虛擬環境 (Windows PowerShell)
.\venv\Scripts\activate

# 3. 安裝依賴套件
pip install -r requirements.txt

# 4. 啟動 Bot
python bot.py
```

---

### 🐳 替代方案：使用 Docker / Docker Compose 執行
如果您希望在伺服器上長期穩定運行，或是想免去在本機設定 Python 環境的麻煩，直接使用 Docker Compose 是最推薦的做法。

**系統準備：**
- 已安裝 Docker 與 Docker Compose。
- 已將 `.env.example` 複製為 `.env` 並設定好你的 `DISCORD_TOKEN`。
- 專案目錄下已建立 `config.json` 與 `images.json` 檔案（若無，可手動建立空白檔案，或透過 Docker 啟動時自動掛載）。

**執行指令：**

```bash
# 1. 啟動容器 (背景執行)
docker compose up -d

# 2. 查看運行日誌 (確認 Bot 有無成功連線)
docker compose logs -f

# 3. 停止容器
docker compose down
```

> **💡 提示**：此 Docker 映像檔已預先安裝 **文泉驛微米黑字型 (fonts-wqy-microhei)** 並且設定時區為 `Asia/Taipei`，因此在 Docker 中產生的中文浮水印也能完美呈現，不會出現方塊字！

---

## ⚙️ 洩漏追蹤設定教學 (管理員三步驟)

請確保您是伺服器的管理員，在 Discord 中依序執行以下設定：

### 1. 設定原圖備份頻道 (原圖儲存庫)
建立一個只有管理員與 Bot 能看見的**私密文字頻道**（例如 `#原圖備份`），並在伺服器任何地方執行以下指令：
```text
/config_backup channel:#原圖備份
```

### 2. 啟用自動浮水印監聽頻道
前往您希望成員發布圖片的公開頻道（例如 `#作品分享`），在該頻道內執行：
```text
/config_auto_channel action:啟用 (Enable)
```

### 3. 查看設定狀態
執行以下指令檢查是否均設定成功：
```text
/config_view
```
確認輸出中 **洩漏追蹤防護狀態** 顯示為：`🟢 正常運作中 (按鈕式個人專屬加密下載)`。

> **💡 提示**：若未設定「原圖備份頻道」，Bot 將只會對圖片套用一般預設文字水印，而無法啟用個人專屬洩漏追蹤防護。

---

## 💬 指令說明

### 🔹 一般/測試指令
*   `/watermark [attachment] [text] [position] [opacity] [personalize]`
    *   **用途**：手動上傳圖片加上水印。
    *   **參數**：
        *   `attachment`：要處理的圖片檔案。
        *   `personalize`：設為 `True` 時，將自動忽略 `text`，直接**嵌入您本人的 Discord ID 與名稱**以進行效果測試。

### 🔸 管理員設定指令
*   `/config_view`：查看目前的浮水印與備份頻道設定。
*   `/config_default [text] [position] [opacity]`：修改預設的浮水印文字、位置與不透明度。
*   `/config_auto_channel [action]`：開啟/關閉當前頻道的自動監聽防護。
*   `/config_backup [channel]`：設定/取消儲存無水印原圖的備份頻道。
