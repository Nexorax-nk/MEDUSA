import os
import sys
from dotenv import load_dotenv
from groq import Groq

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

def check_groq_access():
    print("🔍 Checking Groq API Credentials...")
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": "Respond with 'Groq is online!'" }],
            model="qwen/qwen3.8-27b",
            max_tokens=100
        )
        print(f"✅ Success! Response: {chat_completion.choices[0].message.content}")
    except Exception as e:
        print(f"\n❌ Error connecting to Groq:\n{e}")
        try:
            client = Groq(api_key=os.getenv("GROQ_API_KEY"))
            models = client.models.list()
            print("Available models:")
            for m in models.data:
                print(f" - {m.id}")
        except:
            pass

if __name__ == "__main__":
    check_groq_access()
