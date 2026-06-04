from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
import httpx
import os
import json

app = FastAPI()

# Lấy từ biến môi trường
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "khanhthaoduoc2024")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

SYSTEM_PROMPT = """Bạn là trợ lý bán hàng thân thiện của shop Khánh Thảo Dược Đôi Mắt - chuyên bán thuốc thảo dược cho thú cưng.

Sản phẩm và giá:
- Thuốc thảo dược Đôi Mắt: 150.000đ (nhỏ mắt, trị viêm mắt, ghèn, đỏ mắt cho thú cưng)
- Xịt thảo dược nấm ngứa viêm da: 150.000đ (trị nấm, ngứa, viêm da cho thú cưng)
- Vệ sinh tai: 150.000đ (làm sạch tai, trị viêm tai cho thú cưng)

Thông tin liên hệ: Liên hệ trực tiếp qua Facebook của shop.

Hướng dẫn:
- Trả lời ngắn gọn, thân thiện, dùng tiếng Việt
- Tư vấn đúng sản phẩm phù hợp với triệu chứng của thú cưng
- Khi khách muốn đặt hàng, hỏi: tên, địa chỉ giao hàng, số điện thoại và sản phẩm muốn mua
- Nếu không chắc về triệu chứng, khuyên khách mô tả rõ hơn
- Luôn nhắc khách rằng đây là thảo dược thiên nhiên, an toàn cho thú cưng"""


@app.get("/webhook")
async def verify_webhook(request: Request):
    """Xác minh webhook với Facebook"""
    params = dict(request.query_params)
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(content=challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhook")
async def receive_message(request: Request):
    """Nhận tin nhắn từ Messenger và trả lời"""
    body = await request.json()

    if body.get("object") != "page":
        raise HTTPException(status_code=404)

    for entry in body.get("entry", []):
        for event in entry.get("messaging", []):
            sender_id = event["sender"]["id"]

            # Chỉ xử lý tin nhắn text
            if "message" not in event:
                continue
            message = event["message"]
            if "text" not in message:
                continue

            user_text = message["text"]

            # Gọi Claude API
            reply = await ask_claude(user_text)

            # Gửi lại Messenger
            await send_message(sender_id, reply)

    return {"status": "ok"}


async def ask_claude(user_message: str) -> str:
    """Gọi Claude API để tạo câu trả lời"""
    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 500,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_message}],
    }
    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
        )
        data = res.json()
        return data["content"][0]["text"]


async def send_message(recipient_id: str, text: str):
    """Gửi tin nhắn qua Messenger API"""
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text},
    }
    async with httpx.AsyncClient(timeout=30) as client:
        await client.post(url, json=payload)
