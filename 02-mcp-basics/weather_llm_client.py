"""MCP + LLM — luồng đầy đủ: MCP khám phá tool, LLM dùng Function Calling để gọi.

So với 01-function-calling:
  - KHÔNG viết schema tay: schema lấy từ session.list_tools() (server tự sinh)
  - KHÔNG chạy hàm trong app: app chuyển lời gọi sang session.call_tool(),
    weather_server.py mới là nơi thực thi

Model (Nemotron qua NVIDIA NIM) vẫn dùng Function Calling để QUYẾT ĐỊNH gọi
tool nào — MCP chỉ là giao thức nối client với server.

Cách chạy (cùng thư mục với weather_server.py, client tự khởi động server):
    pip install -r ../requirements.txt
    export NVIDIA_API_KEY=nvapi-...      # hoặc đặt trong file .env ở thư mục gốc repo
    python weather_llm_client.py
"""

import asyncio
import json
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()

client = OpenAI(
    base_url=os.getenv("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1"),
    api_key=os.environ["NVIDIA_API_KEY"],
)
MODEL = os.getenv("NIM_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b")


async def run(prompt: str) -> str:
    params = StdioServerParameters(command=sys.executable, args=["weather_server.py"])

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1. MCP: khám phá tool tại runtime rồi đổi sang định dạng tool của LLM
            mcp_tools = (await session.list_tools()).tools
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description or "",
                        "parameters": t.input_schema,
                    },
                }
                for t in mcp_tools
            ]
            print(f"[MCP] list_tools -> {[t.name for t in mcp_tools]}")

            messages: list[dict] = [{"role": "user", "content": prompt}]
            resp = client.chat.completions.create(model=MODEL, messages=messages, tools=tools)
            msg = resp.choices[0].message

            # 2. Function Calling: LLM quyết định gọi tool nào
            while msg.tool_calls:
                messages.append({
                    "role": "assistant",
                    "content": msg.content,
                    "tool_calls": [tc.model_dump() for tc in msg.tool_calls],
                })
                for tc in msg.tool_calls:
                    args = json.loads(tc.function.arguments)
                    # 3. MCP: SERVER thực thi tool, app chỉ chuyển tiếp lời gọi
                    result = await session.call_tool(tc.function.name, args)
                    text = result.content[0].text
                    print(f"[LLM -> MCP] {tc.function.name}({args}) -> {text}")
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": text})

                resp = client.chat.completions.create(model=MODEL, messages=messages, tools=tools)
                msg = resp.choices[0].message

            # 4. LLM tổng hợp câu trả lời cuối
            return msg.content


if __name__ == "__main__":
    question = "Thời tiết Hanoi và Danang hôm nay thế nào? Trả lời ngắn gọn bằng tiếng Việt."
    print(f"User: {question}\n")
    print("\nTrả lời:", asyncio.run(run(question)))
