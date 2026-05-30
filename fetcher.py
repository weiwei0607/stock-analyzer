import asyncio
import logging
import yfinance as yf

logger = logging.getLogger(__name__)


def _fetch_price_sync(symbol: str) -> dict:
    """同步版本，給 run_in_executor 用"""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="2d", interval="1d")

        if hist.empty:
            return {"error": f"找不到股票代號: {symbol}"}

        latest = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) >= 2 else latest

        price = float(latest["Close"])
        prev_close = float(prev["Close"])
        change = price - prev_close
        change_pct = (change / prev_close) * 100 if prev_close else 0

        return {
            "symbol": symbol.upper(),
            "price": round(price, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "prev_close": round(prev_close, 2),
        }
    except Exception as e:
        logger.error(f"抓取 {symbol} 失敗: {e}")
        return {"error": f"抓取失敗: {e}"}


async def get_price(symbol: str) -> dict:
    """非阻塞版本，在 executor 裡執行 yfinance（避免卡住 event loop）"""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _fetch_price_sync, symbol)


def get_price_sync(symbol: str) -> dict:
    """給非 async 場合（如測試）用的同步版"""
    return _fetch_price_sync(symbol)
