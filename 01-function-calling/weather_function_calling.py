"""Minh hoạ FUNCTION CALLING thuần với NVIDIA NIM (OpenAI-compatible API).

Tool `get_weather` được định nghĩa schema thủ công VÀ thực thi ngay trong
chính file app này. Model chỉ QUYẾT ĐỊNH gọi tool nào; app mới là nơi chạy.

Model mặc định: nvidia/nemotron-3.5-lightning-30b-a3b (đổi qua biến NIM_MODEL).

Cách chạy:
    pip install -r ../requirements.txt
    export NVIDIA_API_KEY=nvapi-...      # hoặc đặt trong file .env ở thư mục gốc repo
    python weather_function_calling.py
"""

import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # đọc NVIDIA_API_KEY / NIM_MODEL từ .env nếu có

client = OpenAI(
    base_url=os.getenv("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1"),
    api_key=os.environ["NVIDIA_API_KEY"],
)

MODEL = os.getenv("NIM_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b")

SYSTEM_INSTRUCTION = (
    "Bạn là trợ lý thời tiết thân thiện, trả lời bằng tiếng Việt tự nhiên. "
    "Dùng emoji phù hợp (🌧️ 🌤️ 💨 💧). "
    "Tóm tắt ngắn gọn, dễ hiểu, và đưa ra lời khuyên thực tế "
    "(ví dụ: mang ô, mặc áo mỏng, ...)."
)

# 1. App tự định nghĩa schema của tool (định dạng OpenAI / JSON Schema)
get_weather_declaration = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Lấy thời tiết hiện tại của một thành phố",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "Tên thành phố"},
            },
            "required": ["city"],
        },
    },
}

TOOLS = [get_weather_declaration]


# 2. App tự thực thi tool (trong thực tế sẽ gọi API thời tiết thật)
def get_weather(city: str) -> str:
    """Trả về thời tiết (mock) của *city*. Dùng làm tool cho model."""
    mock_data = {
        "Hà Nội": {
            "nhiệt_độ": "29°C",
            "thời_tiết": "trời mưa nhẹ",
            "độ_ẩm": "82%",
            "gió": {"hướng": "Đông Nam", "tốc_độ": "12 km/h"},
        },
        "Hồ Chí Minh": {
            "nhiệt_độ": "33°C",
            "thời_tiết": "mưa rào",
            "độ_ẩm": "75%",
            "gió": {"hướng": "Tây Nam", "tốc_độ": "15 km/h"},
        },
        "Đà Nẵng": {
            "nhiệt_độ": "30°C",
            "thời_tiết": "nhiều mây",
            "độ_ẩm": "78%",
            "gió": {"hướng": "Đông", "tốc_độ": "10 km/h"},
        },
    }

    default = {"nhiệt_độ": "28°C", "thời_tiết": "không có dữ liệu chi tiết"}
    return json.dumps({"city": city, **mock_data.get(city, default)}, ensure_ascii=False)


def run(prompt: str) -> str:
    """Gửi *prompt* tới NIM, tự động xử lý function calling và trả về câu trả lời cuối."""
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_INSTRUCTION},
        {"role": "user", "content": prompt},
    ]

    # 3. Gọi model — model quyết định có gọi tool hay không
    resp = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOLS)
    msg = resp.choices[0].message

    # 4. Vòng lặp: nếu model yêu cầu tool, app TỰ THỰC THI rồi đưa kết quả trả lại
    while msg.tool_calls:
        # Thêm phản hồi của model (chứa các tool_calls) vào lịch sử hội thoại
        messages.append({
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [tc.model_dump() for tc in msg.tool_calls],
        })

        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)
            print(f"  [model yêu cầu] {tc.function.name}({args})")
            result = get_weather(**args)  # <-- app chạy, không phải model
            print(f"  [app thực thi]  -> {result}")
            # Gửi kết quả tool trả về cho model (gắn với id của lời gọi)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

        resp = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOLS)
        msg = resp.choices[0].message

    # 5. Model tổng hợp câu trả lời cuối
    return msg.content


if __name__ == "__main__":
    question = "Thời tiết Hà Nội và Đà Nẵng hôm nay thế nào?"
    print(f"User: {question}\n")
    print("Trả lời:", run(question))
