import os
import sys
import json
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
import telebot
import requests

# Add root directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import bot, BOT_TOKEN
from database import init_db

app = FastAPI(title="FPL Assistant Bot Serverless Webhook")

# Ensure DB tables are initialized
try:
    init_db()
except Exception as e:
    print(f"[InitDBError] {e}")

@app.get("/")
def home():
    return {
        "status": "online",
        "service": "FPL Smart Assistant Bot",
        "instructions": "Visit /set_webhook to configure Telegram Webhook."
    }

@app.get("/set_webhook")
def set_webhook(request: Request):
    token = os.environ.get("BOT_TOKEN", BOT_TOKEN)
    if not token:
        return {"error": "BOT_TOKEN environment variable not set."}
        
    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    proto = request.headers.get("x-forwarded-proto", "https")
    
    if not host:
        return {"error": "Could not determine host URL."}
        
    webhook_url = f"{proto}://{host}/api/webhook"
    tg_url = f"https://api.telegram.org/bot{token}/setWebhook?url={webhook_url}"
    
    try:
        resp = requests.get(tg_url, timeout=10)
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/webhook")
async def webhook(request: Request):
    try:
        body_bytes = await request.body()
        if not body_bytes:
            return Response(status_code=200)
            
        json_data = json.loads(body_bytes.decode("utf-8"))
        update = telebot.types.Update.de_json(json_data)
        
        if update:
            bot.process_new_updates([update])
            
        return Response(status_code=200)
    except Exception as e:
        print(f"[WebhookException] {e}")
        return Response(status_code=200)
