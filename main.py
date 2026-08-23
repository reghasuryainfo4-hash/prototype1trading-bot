import os
import numpy as np
import pandas as pd
import requests
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

# ==========================================
# 1. YOUR TELEGRAM CONFIGURATION
# ==========================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8093228632:AAGFfQK8-i4jTzBiHdE5bxQgH70M9ODgrRM")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "5978109641")

def send_telegram_alert(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Telegram Error: {e}")

# ==========================================
# 2. QUANT & KERNEL ENGINE
# ==========================================
def rational_quadratic_kernel(src: np.ndarray, h: int = 8, r: float = 8.0, x: int = 25):
    size = len(src)
    yhat = np.zeros(size)
    for i in range(size):
        weight_sum = 0.0
        val_sum = 0.0
        for j in range(max(0, i - x), i + 1):
            d = (i - j)
            w = (1.0 + (d ** 2) / (2.0 * r * (h ** 2))) ** (-r)
            weight_sum += w
            val_sum += w * src[j]
        yhat[i] = val_sum / weight_sum if weight_sum != 0 else src[i]
    return yhat

def calculate_ml_signals(df: pd.DataFrame):
    close = df['close'].to_numpy(dtype=float)
    high = df['high'].to_numpy(dtype=float)
    low = df['low'].to_numpy(dtype=float)
    
    kernel = rational_quadratic_kernel(close)
    df['kernel'] = np.round(kernel, 2)
    
    signals = []
    for i in range(len(df)):
        if i < 2:
            signals.append(0)
            continue
        if kernel[i] > kernel[i-1] and kernel[i-1] <= kernel[i-2] and close[i] > kernel[i]:
            signals.append(1)  # BUY
        elif kernel[i] < kernel[i-1] and kernel[i-1] >= kernel[i-2] and close[i] < kernel[i]:
            signals.append(-1) # SELL
        else:
            signals.append(0)
    df['signal'] = signals
    return df

# ==========================================
# 3. FASTAPI SERVER & WEBHOOK
# ==========================================
app = FastAPI(title="Cloud Quant Terminal")
history_df = pd.DataFrame(columns=['time', 'open', 'high', 'low', 'close', 'volume'])

@app.on_event("startup")
def on_startup():
    send_telegram_alert("☁️ *Cloud AI Quant Server is LIVE (24/7 Active)* 🚀")

@app.post("/webhook")
async def receive_candle(request: Request):
    global history_df
    data = await request.json()
    new_row = pd.DataFrame([{
        'time': data['time'],
        'open': float(data['open']),
        'high': float(data['high']),
        'low': float(data['low']),
        'close': float(data['close']),
        'volume': float(data.get('volume', 100))
    }])
    history_df = pd.concat([history_df, new_row], ignore_index=True).drop_duplicates(subset=['time'])
    df_calc = calculate_ml_signals(history_df.copy())
    
    latest = df_calc.iloc[-1]
    ticker = data.get('ticker', 'LIVE_ASSET')
    
    if latest['signal'] == 1:
        send_telegram_alert(f"🚀 AI QUANT BUY SIGNAL\nTicker: {ticker}\nPrice: {latest['close']}\nTime: {latest['time']}")
    elif latest['signal'] == -1:
        send_telegram_alert(f"🔻 AI QUANT SELL SIGNAL\nTicker: {ticker}\nPrice: {latest['close']}\nTime: {latest['time']}")
        
    return {"status": "success", "bars_count": len(history_df)}

@app.get("/", response_class=HTMLResponse)
async def web_dashboard():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Cloud Quant Terminal</title>
        <script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
        <style>
            body { margin: 0; padding: 0; background-color: #131722; color: #d1d4dc; font-family: sans-serif; }
            #header { padding: 15px 20px; background-color: #1e222d; font-size: 18px; font-weight: bold; border-bottom: 1px solid #2a2e39; }
            #chart { width: 100vw; height: calc(100vh - 60px); }
        </style>
    </head>
    <body>
        <div id="header">📊 AI QUANT LIVE TERMINAL (24/7 Cloud Active)</div>
        <div id="chart"></div>
    </body>
    </html>
    """

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
