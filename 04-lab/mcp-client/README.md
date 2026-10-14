# Weather Agent - Google ADK with MCP Server

AI agent built with **Google Agent Development Kit (ADK)** that uses tools from a local **MCP server** via Streamable HTTP transport.
The LLM is **Nemotron** (`nvidia/nemotron-3.5-lightning-30b-a3b`) on **NVIDIA NIM**, called through ADK's `LiteLlm` wrapper.

## Architecture

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────────┐
│   User Browser  │ ───> │  ADK Web UI      │ ───> │  Weather Agent      │
│   localhost:8000│      │  (Google ADK)    │      │  (Agent with MCP)   │
└─────────────────┘      └──────────────────┘      └─────────────────────┘
                                                             │
                                                             │ Streamable HTTP
                                                             ▼
                                                   ┌─────────────────────┐
                                                   │  MCP Server         │
                                                   │  localhost:8085/mcp │
                                                   │  FastMCP + Tools    │
                                                   └─────────────────────┘
                                                             │
                                                             ▼
                                                   ┌─────────────────────┐
                                                   │  OpenWeatherMap     │
                                                   └─────────────────────┘
```

## Features

- **Remote MCP Tools**: Connects to MCP server via Streamable HTTP
- **3 Weather Tools**:
  - `get_current_weather(city)` - Real-time weather conditions
  - `get_forecast(city, days)` - Weather forecast up to 3 days
  - `health_check()` - Server health verification
- **Web Interface**: UI via ADK web
- **Streaming Responses**: Real-time AI responses

## Quick Start

### 1. Start the MCP Server

```bash
cd ../mcp-server
export OPENWEATHER_API_KEY="your_openweather_api_key"
uv run python weather.py
```

### 2. Setup Environment

```bash
cd mcp-client

# Create .env file with your NVIDIA NIM API key
# Get a key from: https://build.nvidia.com
echo "NVIDIA_API_KEY=nvapi-your_key" > .env
```

### 3. Install Dependencies

```bash
uv sync
```

### 4. Run the Agent

```bash
uv run adk web
```

### 5. Use the Agent

1. Open browser: http://localhost:8000
2. Select `weather_agent` from dropdown
3. Ask questions like:
   - "What's the weather in Brisbane?"
   - "Give me a 3-day forecast for Tokyo"
   - "How's the weather in New York?"

## Project Structure

```
mcp-client/
├── weather_agent/
│   ├── agent.py           # Main agent with MCP connection
│   └── __init__.py
├── pyproject.toml
├── .env                   # Environment variables (create this)
└── README.md
```

## Configuration

### Agent Configuration

In `weather_agent/agent.py`:

```python
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8085/mcp")

connection_params = StreamableHTTPConnectionParams(
    url=MCP_SERVER_URL,
    timeout=30.0,
)

# NVIDIA NIM is OpenAI-compatible → LiteLLM "openai/" prefix + NIM base URL
model = LiteLlm(
    model=f"openai/{NIM_MODEL}",          # nvidia/nemotron-3.5-lightning-30b-a3b
    api_base=NIM_BASE_URL,                # https://integrate.api.nvidia.com/v1
    api_key=os.getenv("NVIDIA_API_KEY"),
)

root_agent = Agent(
    name="weather_agent",
    model=model,
    instruction=INSTRUCTION,
    tools=[weather_tools],
    generate_content_config=types.GenerateContentConfig(temperature=0.3),
)
```

## Troubleshooting

### Agent won't connect to MCP server

1. **404 errors**: MCP server is not running or wrong port
   - Ensure the MCP server is running on port 8085
   - Check `MCP_SERVER_URL` (env var / `.env`, default `http://localhost:8085/mcp`)

2. **405 errors**: Port conflict with another application
   - Check what's running on the port: `lsof -i :8085`
   - Change port in both server and client if needed

3. **Timeout errors**: Server not started
   - Start the MCP server first, then the ADK client

### Fallback Mode

If MCP connection fails, the agent runs in fallback mode without tools.
Fix the connection and restart ADK web.

## Environment Variables

Create `.env` file:
```bash
NVIDIA_API_KEY=nvapi-your_key
# Optional overrides
NIM_MODEL=nvidia/nemotron-3.5-lightning-30b-a3b
MCP_SERVER_URL=http://localhost:8085/mcp
```

Check the setup (keys, dependencies, MCP server reachable, agent import):
```bash
uv run python verify_setup.py
```

## Resources

- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [MCP Specification](https://modelcontextprotocol.io/)
- [FastMCP GitHub](https://github.com/jlowin/fastmcp)
- [OpenWeatherMap API](https://openweathermap.org/api)
- [NVIDIA NIM (build.nvidia.com)](https://build.nvidia.com)
- [ADK + LiteLLM models](https://google.github.io/adk-docs/agents/models/)
