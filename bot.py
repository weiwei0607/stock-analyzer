import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

import config
import db
from fetcher import get_price

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

db.init_db()

MAX_BATCH = 5  # /price 一次最多查幾支


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📈 <b>股票分析 Bot</b>\n\n"
        "<b>指令列表：</b>\n"
        "/price 代號 [代號2 …] — 查詢股價（最多 5 支）\n"
        "  例：<code>/price 2330.TW AAPL TSLA</code>\n\n"
        "/alert 代號 >/< 價格 — 設定到價提醒\n"
        "  例：<code>/alert 2330.TW &gt; 700</code>\n\n"
        "/alerts — 查看我的提醒\n"
        "/delete ID — 刪除指定提醒\n"
        "/help — 顯示此說明",
        parse_mode="HTML",
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


async def price_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查詢股價，支援批量（最多 5 支同時查）"""
    if not context.args:
        await update.message.reply_text(
            "❌ 請輸入股票代號，例如：\n"
            "<code>/price 2330.TW</code>\n"
            "<code>/price 2330.TW AAPL TSLA</code>",
            parse_mode="HTML",
        )
        return

    symbols = [s.upper() for s in context.args[:MAX_BATCH]]
    if len(context.args) > MAX_BATCH:
        await update.message.reply_text(f"⚠️ 一次最多查 {MAX_BATCH} 支，已取前 {MAX_BATCH} 支")

    # 並行抓取所有股票（非阻塞）
    results = await asyncio.gather(*[get_price(s) for s in symbols])

    lines = []
    for data in results:
        if "error" in data:
            lines.append(f"❌ {data['error']}")
            continue
        emoji = "📈" if data["change"] >= 0 else "📉"
        lines.append(
            f"{emoji} <b>{data['symbol']}</b>  "
            f"<b>${data['price']:,.2f}</b>  "
            f"{data['change_pct']:+.2f}%\n"
            f"   昨收 ${data['prev_close']:,.2f}  漲跌 {data['change']:+.2f}"
        )
        db.cache_price(data["symbol"], data["price"], data["change_pct"])

    await update.message.reply_text("\n\n".join(lines), parse_mode="HTML")


async def alert_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """設定到價提醒"""
    if len(context.args) != 3:
        await update.message.reply_text(
            "❌ 格式錯誤，範例：\n"
            "<code>/alert 2330.TW &gt; 700</code>\n"
            "<code>/alert AAPL &lt; 150</code>",
            parse_mode="HTML",
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
    user_id = update.effective_user.id
    alert_id = db.add_alert(symbol, cond_type, target, user_id)

    await update.message.reply_text(
        f"✅ 提醒已設定 (#{alert_id})\n"
        f"{symbol} {condition} ${target:,.2f} 時通知你\n\n"
        f"每 5 分鐘自動檢查一次",
    )


async def alerts_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查看自己的所有提醒"""
    user_id = update.effective_user.id
    rows = db.get_user_alerts(user_id)

    if not rows:
        await update.message.reply_text("📭 你目前沒有設定任何提醒")
        return

    lines = ["📋 <b>我的提醒列表：</b>"]
    for alert_id, symbol, cond, price, is_active in rows:
        status = "🟢" if is_active else "⚪ 已觸發"
        sign = ">" if cond == "gt" else "<"
        lines.append(f"#{alert_id}: <b>{symbol}</b> {sign} ${price:,.2f} {status}")

    lines.append("\n<code>/delete ID</code> 可刪除指定提醒")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def delete_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """刪除指定提醒（只能刪自己的）"""
    if not context.args:
        await update.message.reply_text("❌ 請輸入提醒 ID，例如：<code>/delete 3</code>", parse_mode="HTML")
        return

    try:
        alert_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID 必須是數字")
        return

    user_id = update.effective_user.id
    deleted = db.delete_alert(alert_id, user_id)

    if not deleted:
        await update.message.reply_text(f"❌ 找不到提醒 #{alert_id}，或你沒有權限刪除它")
        return

    await update.message.reply_text(f"🗑️ 提醒 #{alert_id} 已刪除")


async def check_alerts(context: ContextTypes.DEFAULT_TYPE):
    """
    背景排程：檢查所有活躍提醒。
    - 按 symbol 去重，每支股票只查一次 API
    - 查完後更新 price_cache
    - 通知發給設定者本人
    """
    alerts = db.get_active_alerts()
    if not alerts:
        return

    # 去重：每個 symbol 只抓一次
    symbols = list({a[2] for a in alerts})
    logger.info(f"check_alerts: 檢查 {len(alerts)} 個提醒，{len(symbols)} 支股票")

    price_map: dict[str, float] = {}
    fetch_results = await asyncio.gather(*[get_price(s) for s in symbols])
    for data in fetch_results:
        if "error" not in data:
            price_map[data["symbol"]] = data["price"]
            db.cache_price(data["symbol"], data["price"], data["change_pct"])

    for alert_id, user_id, symbol, cond_type, target_price in alerts:
        current = price_map.get(symbol)
        if current is None:
            continue

        triggered = (
            (cond_type == "gt" and current >= target_price) or
            (cond_type == "lt" and current <= target_price)
        )
        if not triggered:
            continue

        db.deactivate_alert(alert_id)
        sign = ">=" if cond_type == "gt" else "<="
        emoji = "🚀" if cond_type == "gt" else "🔻"
        chat_id = user_id if user_id else config.TELEGRAM_CHAT_ID

        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"{emoji} <b>價格提醒觸發！</b>\n\n"
                    f"股票: <b>{symbol}</b>\n"
                    f"條件: {sign} ${target_price:,.2f}\n"
                    f"現價: <b>${current:,.2f}</b>\n\n"
                    f"提醒 #{alert_id} 已自動關閉"
                ),
                parse_mode="HTML",
            )
            logger.info(f"提醒 #{alert_id} ({symbol} {sign} {target_price}) 已觸發，通知 user {chat_id}")
        except Exception as e:
            logger.error(f"發送提醒 #{alert_id} 失敗: {e}")


def main():
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("price", price_cmd))
    application.add_handler(CommandHandler("alert", alert_cmd))
    application.add_handler(CommandHandler("alerts", alerts_cmd))
    application.add_handler(CommandHandler("delete", delete_cmd))

    # 使用 python-telegram-bot 內建 JobQueue（APScheduler 由框架管理）
    application.job_queue.run_repeating(check_alerts, interval=300, first=15)

    logger.info("🤖 Bot 啟動中...")
    application.run_polling()


if __name__ == "__main__":
    main()
