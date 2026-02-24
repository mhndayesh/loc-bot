import threading

# Global LLM lock to prevent concurrent requests to providers that might crash (like LM Studio)
LLM_LOCK = threading.Lock()
