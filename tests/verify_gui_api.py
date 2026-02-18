import requests
import json

BASE_URL = "http://localhost:7777"

def test_config_update():
    print("Testing /api/config update with embedding_model...")
    resp = requests.post(f"{BASE_URL}/api/config", json={
        "embedding_model": "test-model-123"
    })
    print(f"Status: {resp.status_code}, Body: {resp.json()}")
    
    # Verify persistence
    with open("config.json", "r") as f:
        conf = json.load(f)
        if conf.get("embedding_model") == "test-model-123":
            print("✅ config.json updated correctly")
        else:
            print("❌ config.json NOT updated correctly")

def test_embedding_provider():
    print("\nTesting /api/embedding_provider...")
    resp = requests.post(f"{BASE_URL}/api/embedding_provider", json={"provider": "ollama"})
    print(f"Status: {resp.status_code}, Body: {resp.json()}")
    
    # Verify persistence
    with open("config.json", "r") as f:
        conf = json.load(f)
        if conf.get("embedding_provider") == "ollama":
            print("✅ embedding_provider updated to ollama")
        else:
            print("❌ embedding_provider NOT updated correctly")

def test_fetch_embedding_models():
    print("\nTesting /api/embedding_models...")
    resp = requests.get(f"{BASE_URL}/api/embedding_models")
    print(f"Status: {resp.status_code}")
    data = resp.json()
    print(f"Models found: {len(data.get('models', []))}")
    if data.get("provider") == "ollama":
        print("✅ Fetched from ollama provider")
    else:
        print(f"❌ Expected ollama provider, got {data.get('provider')}")

if __name__ == "__main__":
    try:
        test_config_update()
        test_embedding_provider()
        test_fetch_embedding_models()
    except Exception as e:
        print(f"Test failed: {e}")
