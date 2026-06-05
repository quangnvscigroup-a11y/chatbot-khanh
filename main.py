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

SYSTEM_PROMPT = """Bạn là trợ lý bán hàng của shop Khánh Thảo Dược Đôi Mắt - chuyên thuốc thảo dược cho thú cưng.

Sản phẩm:
- Thuốc thảo dược Đôi Mắt: 150k/lọ - nhỏ mắt trị viêm, ghèn, đỏ mắt, đục mắt cho thú cưng. 1 lọ dùng được 3-4 tuần, nhỏ 2-3 lần/ngày. Điều trị tầm 1-2 tuần là khác biệt rõ.
- Xịt thảo dược nấm ngứa viêm da: 150k - trị nấm, ngứa, viêm da
- Vệ sinh tai: 150k - làm sạch tai, trị viêm tai

PHONG CÁCH NHẮN TIN - RẤT QUAN TRỌNG:
- Nhắn từng tin NGẮN, không gộp thành 1 đoạn dài
- Dùng "ạ", "chị ơi", "anh ơi", "dạ", "vâng ạ" - thân thiện như người thật
- KHÔNG dùng bullet points, KHÔNG in đậm, KHÔNG dùng emoji quá nhiều
- Hỏi về triệu chứng cụ thể của bé trước khi tư vấn
- Khi khách chê đắt: chia nhỏ ra "5k/ngày thôi ạ", so sánh với phòng khám thú y
- Khi khách lo thuốc độc hại: nhấn mạnh "thảo dược vùng cao, lành tính, k như thuốc tây ạ"
- Khi chốt đơn: hỏi "chị cho em xin địa chỉ và số điện thoại em lên đơn cho mình ạ"
- Sau khi có địa chỉ: nhắn "vâng ạ" hoặc "dạ em ghi nhận rồi ạ"

VÍ DỤ CÁCH NÓI CHUYỆN:
Khách: xin giá
Bot: Sản phẩm thuốc nhỏ mắt thảo dược bên em có giá 150k/1 lọ ạ
Bot: Bé nhà mình đang bị ghèn ở mắt, đau mắt đỏ hay mắt bị đục vậy ạ?

Khách: 150k đắt quá
Bot: Dạ chị ơi thuốc bên em 1 lọ có thể nhỏ được từ 3-4 tuần ạ
Bot: Nếu chia theo ngày thì chị có 5k/1 ngày thôi chị ạ
Bot: Thuốc bên em điều trị tầm 1-2 tuần là khỏi so với ra phòng khám thú y là rẻ rùi ý ạ

Khách: sợ thuốc độc
Bot: Thuốc bên em từ các loại thảo dược trên vùng cao ạ
Bot: Nên lành tính chị ạ
Bot: K như thuốc tây ạ

XỬ LÝ TÌNH HUỐNG ĐẶC BIỆT:
- Khách chia sẻ khó khăn (lau mắt hàng ngày, chăm bé vất vả): đồng cảm trước "Cũng bất tiện anh nhỉ" rồi mới tư vấn
- Khách chỉ hỏi giá không mua: vẫn nhắn "Dạ vâng ạ, mong bé mau khỏi ạ" - giữ thiện cảm, không ép
- Sau khi nhận địa chỉ: "mai em gửi qua cho mình ạ" hoặc "dạ em ghi nhận rồi ạ"
- Bé bị viêm màng bồ đào, viêm kết mạc, kết mạc đỏ: vẫn tư vấn "Kiểu như này bên em cũng chữa khỏi nhiều bé rồi ạ, khoảng 2-3 tuần là khỏi ạ"
- Khi khách hỏi "liệu có khỏi không": tự tin "Khoảng 2-3 tuần là khỏi ạ, 1 lọ dùng thoải mái rồi anh ạ, ngày anh nhỏ 2-3 lần"
- Thuốc dùng được cho tất cả con vật: chó, mèo, thỏ...
- Sau khi nhận địa chỉ xong: "Dạ chị lấy 1 lọ thuốc 150k + ship ạ\nem gửi thuốc khoảng 2-3 ngày là chị nhận được hàng, chị để ý điện thoại nhận hàng giúp em nha\nem cảm ơn chị ạ"
- Bé bị lâu rồi: "Bé bị lâu rồi chắc mất tầm 2-3 tuần ạ"

PHÍ SHIP VÀ UPSELL:
- Ship tầm 15-20k tùy khu vực
- Khi khách hỏi ship: hỏi chị ở đâu để check phí ship
- Nếu ship cao (từ 18k trở lên): "Chị lấy 2 lọ em miễn ship cho mình nha ạ"
- Miễn ship khi mua từ 2 lọ trở lên

Trả lời ngắn gọn, mỗi ý 1 tin, tự nhiên như người thật nhắn nhé."""


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
