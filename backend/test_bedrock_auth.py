import boto3
import json
import os
import sys
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

def check_bedrock_access():
    print("🔍 Checking AWS Credentials and Bedrock Access...")
    
    try:
        # 1. Check if boto3 can find credentials
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"✅ Authenticated as AWS Account: {identity['Account']}")
        print(f"✅ IAM ARN: {identity['Arn']}")
        
        # 2. Check if we have access to Meta Llama 3 or Amazon Titan
        print("\n🧠 Attempting to invoke Amazon Nova/Titan on Amazon Bedrock...")
        bedrock = boto3.client('bedrock-runtime', region_name='us-east-1') # Adjust region if needed
        
        # We will use the unified Converse API which works across models
        model_id = 'meta.llama3-8b-instruct-v1:0' 
        # fallback: 'meta.llama3-8b-instruct-v1:0'
        
        response = bedrock.converse(
            modelId=model_id,
            messages=[
                {
                    "role": "user",
                    "content": [{"text": "Respond with exactly the words: 'Bedrock is online!'"}]
                }
            ]
        )
        
        assistant_response = response['output']['message']['content'][0]['text']
        
        print(f"✅ Success! Claude responded: {assistant_response}")
        print("\n🎉 Your environment is perfectly configured for the Multi-Agent System!")
        
    except Exception as e:
        print(f"\n❌ Error connecting to AWS/Bedrock:\n{e}")
        print("\nPlease ensure you have:")
        print("1. Set up your AWS credentials (aws configure)")
        print("2. Requested Model Access for Claude 3 Haiku in the AWS Bedrock Console.")
        print("3. Specified the correct AWS Region where you have Bedrock access.")

if __name__ == "__main__":
    check_bedrock_access()
