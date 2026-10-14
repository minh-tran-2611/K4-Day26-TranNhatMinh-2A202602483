# Lab 04 — Weather Agent with Remote MCP Server

A weather agent built with Google ADK that connects to an MCP server via Streamable HTTP transport.
The LLM is **Nemotron** (`nvidia/nemotron-3.5-lightning-30b-a3b`) hosted on **NVIDIA NIM**, and the MCP server
fetches real data from **OpenWeatherMap**.

## Architecture

```
┌─────────────────┐   Streamable HTTP    ┌─────────────────┐      REST       ┌─────────────────┐
│   ADK Agent     │ ──────────────────── │   MCP Server    │ ─────────────── │ OpenWeatherMap  │
│  (mcp-client)   │   localhost:8085/mcp │  (mcp-server)   │                 │ (api/data/2.5)  │
└────────┬────────┘                      └─────────────────┘                 └─────────────────┘
         │ OpenAI-compatible API (LiteLLM)
┌────────▼────────┐
│  NVIDIA NIM     │
│  Nemotron 3.5   │
└─────────────────┘
```

## Tools

| Tool | Description |
|------|-------------|
| `get_current_weather(city)` | Get current weather conditions for a city |
| `get_forecast(city, days)` | Get weather forecast (1–5 days, aggregated from OpenWeather 3-hour steps) |
| `health_check()` | Verify server is running |

## ADK làm gì trong Lab này?

ADK (Agent Development Kit) đóng vai trò **MCP Client** 
```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  1. KẾT NỐI tới MCP Server qua Streamable HTTP                  │
│     StreamableHTTPConnectionParams(url="localhost:8085/mcp")    │
│                                                                 │
│  2. KHÁM PHÁ tools tự động (list_tools)                         │
│     McpToolset → tự hỏi server "anh có tool gì?"                │
│     → nhận về: get_current_weather, get_forecast, health_check  │
│                                                                 │
│  3. TRUYỀN tools cho LLM (Nemotron qua NVIDIA NIM)              │
│     Agent(model=LiteLlm(NIM_MODEL), tools=[weather_tools])      │
│     → Nemotron biết nó có thể gọi 3 tools trên                  │
│                                                                 │
│  4. ĐIỀU PHỐI vòng lặp Function Calling                         │
│     User hỏi → Nemotron chọn tool → ADK gọi MCP Server          │
│     → nhận kết quả → đưa lại cho Nemotron tổng hợp              │
│                                                                 │
│  5. CUNG CẤP giao diện web (adk web)                            │
│     → http://localhost:8000 để chat với agent                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

So với bài 02 (viết client thủ công bằng `mcp.ClientSession`), ADK giúp bạn **không phải viết vòng lặp function calling thủ công** nữa. Toàn bộ luồng list_tools → model quyết định → call_tool → model tổng hợp được ADK xử lý tự động.

## Setup

### 1. MCP Server

```bash
cd mcp-server
uv sync

# Set your OpenWeather key (get one free at https://openweathermap.org/api)
export OPENWEATHER_API_KEY="your_openweather_api_key"
# (or put OPENWEATHER_API_KEY=... in mcp-server/.env — the server loads it automatically)

# Start the server (runs on port 8085 by default)
uv run python weather.py
```

The server will be available at `http://localhost:8085/mcp`.

### 2. ADK Agent (Client)

```bash
cd mcp-client
uv sync

# Create .env file with your NVIDIA NIM API key (get one at https://build.nvidia.com)
echo "NVIDIA_API_KEY=nvapi-your_key" > .env

# Optional: check everything (keys, deps, MCP server reachable, agent import)
uv run python verify_setup.py

# Start ADK web interface
uv run adk web
```

Open http://localhost:8000 in your browser, select `weather_agent`, and ask about the weather.

## Configuration

| Variable | Where | Description |
|----------|-------|-------------|
| `OPENWEATHER_API_KEY` | mcp-server (env or `.env`) | API key from openweathermap.org |
| `NVIDIA_API_KEY` | mcp-client/.env | NVIDIA NIM API key (`nvapi-...`) |
| `NIM_MODEL` | mcp-client/.env | Model on NIM (default: `nvidia/nemotron-3.5-lightning-30b-a3b`) |
| `NIM_BASE_URL` | mcp-client/.env | NIM endpoint (default: `https://integrate.api.nvidia.com/v1`) |
| `PORT` | mcp-server (env) | Override server port (default: 8085) |
| `MCP_SERVER_URL` | mcp-client/.env | MCP endpoint the agent connects to (default: `http://localhost:8085/mcp`; set to your Cloud Run URL + `/mcp` when deployed) |
