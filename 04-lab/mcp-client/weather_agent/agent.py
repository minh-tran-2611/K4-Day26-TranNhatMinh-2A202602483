"""
Weather Agent - Connects to Remote MCP Server on Cloud Run
Successfully connects to custom MCP HTTP endpoints!

LLM: Nemotron on NVIDIA NIM, called through LiteLLM's OpenAI-compatible route.
"""
from dotenv import load_dotenv
from google.adk import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StreamableHTTPConnectionParams
from google.genai import types
import logging
import os

# `adk web` tự nạp .env; gọi thêm ở đây để import trực tiếp (verify_setup.py, script test) cũng có biến môi trường
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mặc định: server chạy local. Deploy lên Cloud Run thì đặt MCP_SERVER_URL trong .env
# (ví dụ: https://<service>.run.app/mcp). verify_setup.py đọc cùng biến này.
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8085/mcp")

# NVIDIA NIM có API tương thích OpenAI → dùng prefix "openai/" của LiteLLM + api_base của NIM
NIM_MODEL = os.getenv("NIM_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b")
NIM_BASE_URL = os.getenv("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")

model = LiteLlm(
    model=f"openai/{NIM_MODEL}",
    api_base=NIM_BASE_URL,
    api_key=os.getenv("NVIDIA_API_KEY"),
)

INSTRUCTION = (
    "You are a friendly weather assistant. Use the MCP tools to answer: "
    "get_current_weather for current conditions, get_forecast for multi-day forecasts "
    "(1-5 days), and health_check when asked whether the server is up. "
    "Always call a tool instead of guessing weather data. "
    "Answer in the SAME language as the user's latest message "
    "(Vietnamese question -> Vietnamese answer, English -> English); never switch to any other language. "
    "Keep it short and add practical advice (umbrella, sunscreen, light clothes, ...)."
)

logger.info(f"🌐 Initializing weather agent with remote MCP server")
logger.info(f"📡 MCP Server: {MCP_SERVER_URL}")
logger.info(f"🧠 Model: {NIM_MODEL} (NVIDIA NIM)")

try:
    # Create connection parameters for the remote MCP server
    connection_params = StreamableHTTPConnectionParams(
        url=MCP_SERVER_URL,
        timeout=30.0,  # Increased timeout for Cloud Run cold starts
    )

    # Create the MCP toolset - this will connect to the remote server
    logger.info("🔌 Connecting to MCP server...")
    weather_tools = McpToolset(
        connection_params=connection_params,
    )
    logger.info("✅ MCP toolset created successfully")

    # Create the agent with remote MCP tools
    root_agent = Agent(
        name="weather_agent",
        model=model,
        instruction=INSTRUCTION,
        tools=[weather_tools],
        # Nhiệt độ thấp giúp model bám sát dữ liệu tool và giữ đúng ngôn ngữ
        generate_content_config=types.GenerateContentConfig(temperature=0.3),
    )
    logger.info("✅ Weather agent initialized with remote MCP tools:")
    logger.info("   - get_current_weather(city)")
    logger.info("   - get_forecast(city, days)")
    logger.info("   - health_check()")
    logger.info("🎉 Remote MCP connection successful!")

except Exception as e:
    logger.error(f"❌ Failed to connect to remote MCP server: {e}")
    logger.error(f"   Server URL: {MCP_SERVER_URL}")
    import traceback
    traceback.print_exc()

    # Create a fallback agent without tools
    logger.warning("⚠️  Creating fallback agent without MCP tools")
    root_agent = Agent(
        name="weather_agent",
        model=model,
        instruction=INSTRUCTION,
        generate_content_config=types.GenerateContentConfig(temperature=0.3),
    )
