# 📈 Stock Analyzer Bot

> 一個輕量級 Telegram 股票機器人，支援即時股價查詢與到價提醒

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python" />
  <img src="https://img.shields.io/badge/Telegram-Bot-26A5E4?logo=telegram" />
  <img src="https://img.shields.io/badge/SQLite-003B57?logo=sqlite" />
  <img src="https://img.shields.io/badge/License-MIT-green.svg" />
</p>

---

## ✨ 功能

- **📊 即時股價查詢** — 輸入股票代號即可取得最新價格、漲跌幅度
- **🔔 到價提醒** — 設定條件（大於 / 小於目標價），Bot 每 5 分鐘自動檢查並通知
- **📋 提醒管理** — 查看、刪除已設定的提醒
- **💾 本地資料庫** — SQLite 儲存提醒與價格快取，重啟後資料不遺失
- **🌏 台股 / 美股雙支援** — 台股加 `.TW`（如 `2330.TW`），美股直接輸入代號（如 `AAPL`）

---

## 🛠️ 技術棧

| 層 | 技術 |
|----|------|
| **Bot 框架** | python-telegram-bot v20+ |
| **股價資料** | yfinance |
| **背景排程** | APScheduler |
| **資料庫** | SQLite |
| **環境管理** | python-dotenv |

---

## 🚀 快速開始

### 1. 環境準備

```bash
# 克隆專案
cd stock-analyzer

# 建立虛擬環境（建議）
python -m venv venv
source venv/bin/activate  # macOS/Linux

# 安裝依賴
pip install -r requirements.txt
```

### 2. 設定環境變數

```bash
cp .env.example .env
```

編輯 `.env`：

```env
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

- `TELEGRAM_BOT_TOKEN`：從 [@BotFather](https://t.me/botfather) 取得
- `TELEGRAM_CHAT_ID`：你的 Telegram User ID（可透過 @userinfobot 查詢）

### 3. 啟動 Bot

```bash
python bot.py
```

看到 `🤖 Bot 啟動中...` 即表示成功。

---

## 📱 指令說明

| 指令 | 說明 | 範例 |
|------|------|------|
| `/start` | 顯示歡迎訊息與指令列表 | `/start` |
| `/price {代號}` | 查詢即時股價 | `/price 2330.TW` |
| `/alert {代號} {>} {<} {價格}` | 設定到價提醒 | `/alert 2330.TW > 700` |
| `/alerts` | 查看所有提醒 | `/alerts` |
| `/delete {id}` | 刪除指定提醒 | `/delete 3` |
| `/help` | 顯示說明 | `/help` |

### 提醒通知範例

```
🚀 價格提醒觸發！

股票: 2330.TW
條件: >= $700
現價: $702.00

提醒 #1 已自動關閉
```

---

## 📁 專案結構

```
stock-analyzer/
├── bot.py              # Bot 主程式與指令處理
├── fetcher.py          # yfinance 股價抓取
├── db.py               # SQLite 資料庫操作
├── config.py           # 環境變數設定
├── requirements.txt    # Python 依賴
├── .env.example        # 環境變數範例
└── stocks.db           # SQLite 資料庫（自動生成）
```

---

## 📝 License

MIT License © 2026
