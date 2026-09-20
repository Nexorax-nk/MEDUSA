import asyncio
import sys
import os
import json
from mcp import ClientSession
from mcp.client.sse import sse_client
from groq import AsyncGroq
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
MODEL_NAME = "qwen/qwen3.8-27b"

def convert_mcp_tool_to_groq(mcp_tool):
    return {
        "type": "function",
        "function": {
            "name": mcp_tool.name,
            "description": mcp_tool.description,
            "parameters": mcp_tool.input_schema
        }
    }

async def run_automated_test():
    print("🧠 Starting Automated Multi-Agent Orchestrator Test...")
    await asyncio.sleep(2)
    try:
        async with sse_client("http://localhost:8000/sse") as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                print("✅ Connected to MEDUSA MCP Server.")
                mcp_tools = await session.list_tools()
                groq_tools = [convert_mcp_tool_to_groq(t) for t in mcp_tools.tools]
                
                user_input = "My father collapsed with a heart attack. Assign a triage priority, find a helper nearby, coordinate transport to Apollo Hospital, and generate a handoff."
                print(f"🎙️ Prompt: '{user_input}'\n")
                
                messages = [
                    {
                        "role": "system",
                        "content": "You are the MEDUSA Multi-Agent Supervisor. Use tools to orchestrate the emergency. Output final summary after calling tools."
                    },
                    {"role": "user", "content": user_input}
                ]
                
                print("🤖 Brain is analyzing...")
                while True:
                    response = await groq_client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=messages,
                        tools=groq_tools,
                        tool_choice="auto",
                        max_tokens=1000
                    )
                    
                    response_message = response.choices[0].message
                    tool_calls = response_message.tool_calls
                    
                    if tool_calls:
                        messages.append(response_message)
                        for tool_call in tool_calls:
                            function_name = tool_call.function.name
                            function_args = json.loads(tool_call.function.arguments)
                            print(f"  ⚡ Executing Tool: {function_name}({function_args})")
                            try:
                                tool_result = await session.call_tool(function_name, function_args)
                                result_text = tool_result.content[0].text
                                print(f"  ✅ Tool Result: {result_text}")
                            except Exception as e:
                                result_text = f"Error: {str(e)}"
                                print(f"  ❌ Tool Error: {result_text}")
                            
                            messages.append({
                                "tool_call_id": tool_call.id,
                                "role": "tool",
                                "name": function_name,
                                "content": result_text
                            })
                    else:
                        print(f"\n🚑 MEDUSA SUMMARY: {response_message.content}\n")
                        break
                        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(run_automated_test())
