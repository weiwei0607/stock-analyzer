import yfinance as yf
import logging

logger = logging.getLogger(__name__)


def get_price(symbol: str) -> dict:
    """
    抓取單一股票即時價格
    台股範例: 2330.TW
    美股範例: AAPL
    """
    try:
        ticker = yf.Ticker(symbol)
        # 取最近一天的資料
        hist = ticker.history(period="5d", interval="1d")

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


def get_info(symbol: str) -> dict:
    """取得股票基本資訊"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        return {
            "name": info.get("longName", symbol),
            "sector": info.get("sector", "N/A"),
            "market_cap": info.get("marketCap"),
        }
    except Exception as e:
        return {"error": str(e)}
