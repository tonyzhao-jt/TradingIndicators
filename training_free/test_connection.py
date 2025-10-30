import requests
import json

def test_qwen_connection():
    """测试Qwen模型连接"""
    
    endpoint = "http://202.45.128.234:5788/v1"
    model_name = "/nfs/whlu/models/Qwen3-Coder-30B-A3B-Instruct"
    api_key = "none"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # 简单的测试提示
    test_prompt = "Hello! Please write a simple Pine Script indicator that calculates a 20-period moving average."
    
    data = {
        "model": model_name,
        "messages": [{"role": "user", "content": test_prompt}],
        "temperature": 0.7,
        "max_tokens": 500
    }
    
    try:
        print("Testing connection to Qwen model...")
        print(f"Endpoint: {endpoint}")
        print(f"Model: {model_name}")
        
        response = requests.post(
            f"{endpoint}/chat/completions",
            headers=headers,
            json=data,
            timeout=60
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            generated_text = result["choices"][0]["message"]["content"]
            print("Connection successful!")
            print(f"Generated text length: {len(generated_text)} characters")
            print(f"First 200 characters of response:\n{generated_text[:200]}...")
            return True
        else:
            print(f"Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"Connection failed: {e}")
        return False

if __name__ == "__main__":
    test_qwen_connection()