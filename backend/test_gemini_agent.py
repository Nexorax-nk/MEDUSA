import json
import httpx
import asyncio

async def test_trigger():
    print("Testing /api/trigger-emergency endpoint...")
    url = "http://localhost:8000/api/trigger-emergency"
    
    async with httpx.AsyncClient() as client:
        try:
            async with client.stream("POST", url, json={"prompt": "My father collapsed at home. Please arrange an ambulance, notify emergency contacts, and generate a handoff."}) as response:
                print(f"Status Code: {response.status_code}")
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        try:
                            data = json.loads(data_str)
                            if data['type'] == 'thought':
                                print(f"s THOUGHT: {data['content']}")
                            elif data['type'] == 'tool_call':
                                print(f"o TOOL CALL: {data['tool']} - Args: {data['args']}")
                            elif data['type'] == 'tool_result':
                                print(f"~ TOOL RESULT: {data['result'][:150]}")
                            elif data['type'] == 'final':
                                print(f"o. FINAL RESPONSE:\n{data['content']}")
                            elif data['type'] == 'error':
                                print(f"?O ERROR: {data['content']}")
                        except json.JSONDecodeError:
                            print(f"Raw: {line}")
        except Exception as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_trigger())
