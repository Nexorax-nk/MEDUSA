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

# Initialize Groq client
groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
# Using the model that we confirmed works
MODEL_NAME = "qwen/qwen3.8-27b"

def convert_mcp_tool_to_groq(mcp_tool):
    """Convert an MCP Tool schema to Groq/OpenAI function calling format."""
    # MCP tools have name, description, and inputSchema (JSON schema)
    return {
        "type": "function",
        "function": {
            "name": mcp_tool.name,
            "description": mcp_tool.description,
            "parameters": mcp_tool.input_schema
        }
    }

async def run_orchestrator():
    print("🧠 Starting MEDUSA Multi-Agent Orchestrator (Powered by Groq & MCP)...")
    
    # Connect to the local MCP Server
    try:
        async with sse_client("http://localhost:8000/sse") as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                print("✅ Connected to MEDUSA MCP Server.")
                
                # Retrieve all available tools from the server
                mcp_tools = await session.list_tools()
                groq_tools = [convert_mcp_tool_to_groq(t) for t in mcp_tools.tools]
                print(f"✅ Loaded {len(groq_tools)} capabilities into the Brain.")
                
                # Interactive Loop
                print("\n========================================================")
                print("🎙️ ORCHESTRATOR ONLINE. Type an emergency prompt (or 'exit').")
                print("========================================================\n")
                
                while True:
                    user_input = input("🗣️ You: ")
                    if user_input.lower() in ['exit', 'quit']:
                        break
                        
                    messages = [
                        {
                            "role": "system",
                            "content": (
                                "You are the MEDUSA Multi-Agent Supervisor. "
                                "You orchestrate medical emergencies by calling specialized tools. "
                                "Always use the tools provided to resolve kinships, create incidents, "
                                "assign triage priorities, dispatch helpers, coordinate transport, and generate handoffs. "
                                "Only answer based on the tool results. Think step by step."
                            )
                        },
                        {"role": "user", "content": user_input}
                    ]
                    
                    print(f"🤖 Brain is analyzing...")
                    
                    while True:
                        # 1. Ask Groq what to do
                        response = await groq_client.chat.completions.create(
                            model=MODEL_NAME,
                            messages=messages,
                            tools=groq_tools,
                            tool_choice="auto",
                            max_tokens=1000
                        )
                        
                        response_message = response.choices[0].message
                        
                        # 2. Check if Groq wants to call a tool
                        tool_calls = response_message.tool_calls
                        
                        if tool_calls:
                            # Append the assistant's message with tool_calls to history
                            messages.append(response_message)
                            
                            for tool_call in tool_calls:
                                function_name = tool_call.function.name
                                function_args = json.loads(tool_call.function.arguments)
                                
                                print(f"  ⚡ Executing Tool: {function_name}({function_args})")
                                
                                # 3. Execute the tool locally on the MCP server
                                try:
                                    tool_result = await session.call_tool(function_name, function_args)
                                    result_text = tool_result.content[0].text
                                    print(f"  ✅ Tool Result: {result_text}")
                                except Exception as e:
                                    result_text = f"Error executing tool: {str(e)}"
                                    print(f"  ❌ Tool Error: {result_text}")
                                
                                # 4. Append tool result to history
                                messages.append({
                                    "tool_call_id": tool_call.id,
                                    "role": "tool",
                                    "name": function_name,
                                    "content": result_text
                                })
                                
                            # The loop will continue, passing the tool results back to Groq
                        else:
                            # 5. Groq finished its thinking and provided a final text response
                            final_answer = response_message.content
                            print(f"\n🚑 MEDUSA: {final_answer}\n")
                            break # Break inner loop, wait for next user input
                            
    except Exception as e:
        print(f"❌ Orchestrator Error: {e}")
        print("Make sure the backend server (python server.py) is running on port 8000!")

if __name__ == "__main__":
    try:
        asyncio.run(run_orchestrator())
    except KeyboardInterrupt:
        print("\nExiting orchestrator.")
