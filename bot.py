import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
import db
from fetcher import get_price

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# 初始化資料庫
db.init_db()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """歡迎指令"""
    await update.message.reply_text(
        "📈 股票分析 Bot 已啟動！\n\n"
        "可用指令：\n"
        "/price {代號} — 查詢股價（如 /price 2330.TW）\n"
        "/alert {代號} {>} {<} {價格} — 設定到價提醒（如 /alert 2330.TW > 700）\n"
        "/alerts — 查看所有提醒\n"
        "/delete {id} — 刪除提醒\n"
        "/help — 說明"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


async def price_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查詢股價"""
    if not context.args:
        await update.message.reply_text("❌ 請輸入股票代號，例如：/price 2330.TW")
        return

    symbol = context.args[0].upper()
    data = get_price(symbol)

    if "error" in data:
        await update.message.reply_text(f"❌ {data['error']}")
        return

    emoji = "📈" if data["change"] >= 0 else "📉"
    await update.message.reply_text(
        f"{emoji} <b>{data['symbol']}</b>\n"
        f"現價: <b>${data['price']}</b>\n"
        f"漲跌: {data['change']:+.2f} ({data['change_pct']:+.2f}%)\n"
        f"昨收: ${data['prev_close']}",
        parse_mode="HTML",
    )

    # 快取價格
    db.cache_price(symbol, data["price"], data["change_pct"])


async def alert_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """設定到價提醒"""
    if len(context.args) != 3:
        await update.message.reply_text(
            "❌ 格式錯誤。範例：\n"
            "/alert 2330.TW > 700\n"
            "/alert AAPL < 150"
        )
        return

    symbol = context.args[0].upper()
    condition = context.args[1]
    try:
        target = float(context.args[2])
    except ValueError:
        await update.message.reply_text("❌ 價格必須是數字")
        return

    if condition not in (">", "<"):
        await update.message.reply_text("❌ 條件只能用 > 或 <")
        return

    cond_type = "gt" if condition == ">" else "lt"
    alert_id = db.add_alert(symbol, cond_type, target)

    await update.message.reply_text(
        f"✅ 提醒已設定 (#{alert_id})\n"
        f"{symbol} {condition} ${target} 時通知你"
    )


async def alerts_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查看所有提醒"""
    rows = db.get_all_alerts()
    if not rows:
        await update.message.reply_text("📭 目前沒有設定任何提醒")
        return

    lines = ["📋 提醒列表："]
    for row in rows:
        alert_id, symbol, cond, price, is_active = row
        status = "🟢 啟用" if is_active else "⚪ 已觸發"
        sign = ">" if cond == "gt" else "<"
        lines.append(f"#{alert_id}: {symbol} {sign} ${price} — {status}")

    await update.message.reply_text("\n".join(lines))


async def delete_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """刪除提醒"""
    if not context.args:
        await update.message.reply_text("❌ 請輸入提醒 ID，例如：/delete 3")
        return

    try:
        alert_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID 必須是數字")
        return

    db.delete_alert(alert_id)
    await update.message.reply_text(f"🗑️ 提醒 #{alert_id} 已刪除")


async def check_alerts(context: ContextTypes.DEFAULT_TYPE):
    """背景排程：檢查所有活躍提醒"""
    alerts = db.get_active_alerts()
    if not alerts:
        return

    for alert_id, symbol, cond_type, target_price in alerts:
        data = get_price(symbol)
        if "error" in data:
            continue

        current = data["price"]
        triggered = False

        if cond_type == "gt" and current >= target_price:
            triggered = True
            sign = ">="
        elif cond_type == "lt" and current <= target_price:
            triggered = True
            sign = "<="

        if triggered:
            db.deactivate_alert(alert_id)
            emoji = "🚀" if cond_type == "gt" else "🔻"
            await context.bot.send_message(
                chat_id=config.TELEGRAM_CHAT_ID,
                text=(
                    f"{emoji} <b>價格提醒觸發！</b>\n\n"
                    f"股票: <b>{symbol}</b>\n"
                    f"條件: {sign} ${target_price}\n"
                    f"現價: <b>${current}</b>\n\n"
                    f"提醒 #{alert_id} 已自動關閉"
                ),
                parse_mode="HTML",
            )
            logger.info(f"提醒 #{alert_id} ({symbol} {sign} {target_price}) 已觸發")


def main():
    # 建立 Application
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    # 註冊指令
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("price", price_cmd))
    application.add_handler(CommandHandler("alert", alert_cmd))
    application.add_handler(CommandHandler("alerts", alerts_cmd))
    application.add_handler(CommandHandler("delete", delete_cmd))

    # 設定背景排程：每 5 分鐘檢查一次提醒
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_alerts,
        "interval",
        minutes=5,
        args=[application.bot],
        id="check_alerts",
        replace_existing=True,
    )
    scheduler.start()

    logger.info("🤖 Bot 啟動中...")
    application.run_polling()


if __name__ == "__main__":
    main()
