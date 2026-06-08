from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
import httpx
import os
import asyncio

app = FastAPI()

PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "khanhthaoduoc2024")

# Lưu danh sách khách đã được trả lời rồi (không trả lời lại)
da_tra_loi = set()

# Các tin nhắn hỏi giá chính xác
GIA_EXACT = ["giá", "gia", "giá?", "gia?", "giá ạ", "giá a", "xin giá", "hỏi giá", "cho hỏi giá"]

# Các cụm từ hỏi giá
GIA_PHRASES = [
    "giá bao nhiêu", "bao nhiêu tiền", "giá thuốc", "giá sản phẩm",
    "giá nhỏ mắt", "giá 1 lọ", "giá 1 hộp", "thuốc bao nhiêu",
    "giá tiền", "giá là bao nhiêu", "giá mua", "mua giá bao nhiêu"
]


@app.get("/webhook")
async def verify_webhook(request: Request):
    params = dict(request.query_params)
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(content=challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhook")
async def receive_message(request: Request):
    body = await request.json()
    if body.get("object") != "page":
        raise HTTPException(status_code=404)

    for entry in body.get("entry", []):
        for event in entry.get("messaging", []):
            sender_id = event["sender"]["id"]
            if "message" not in event:
                continue
            message = event["message"]
            if "text" not in message:
                continue

            user_text = message["text"].lower().strip()

            # Đã trả lời rồi thì bỏ qua
            if sender_id in da_tra_loi:
                continue

            # Kiểm tra có hỏi giá không
            is_ask_price = (
                user_text in GIA_EXACT or
                any(phrase in user_text for phrase in GIA_PHRASES)
            )

            if is_ask_price:
                da_tra_loi.add(sender_id)
                await send_message(sender_id, "Sản phẩm thuốc nhỏ mắt thảo dược bên em có giá 150k/1 hộp ạ")
                await asyncio.sleep(0.8)
                await send_message(sender_id, "Bé nhà mình đang bị ghèn ở mắt, đau mắt đỏ hay mắt bị đục vậy ạ")

    return {"status": "ok"}


async def send_message(recipient_id: str, text: str):
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text},
    }
    async with httpx.AsyncClient(timeout=30) as client:
        await client.post(url, json=payload)
