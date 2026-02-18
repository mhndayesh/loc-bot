"""browser: Simple web page text fetcher."""
import sys
import requests
import time
import re

def browse_web(url):
    print(f"STATUS: Starting fetch for {url}...")
    if not url.startswith("http"):
        url = "https://" + url
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    try:
        print("STATUS: Sending HTTP GET request...")
        response = requests.get(url, headers=headers, timeout=15)
        print(f"STATUS: Received response code {response.status_code}")
        
        if response.status_code == 200:
            content = response.text
            # Check for common bot detection text
            if "captcha" in content.lower() or "robot check" in content.lower():
                 return "STATUS: BLOCKED (CAPTCHA detected). The site suspects we are a bot."
            
            # Simple text extraction
            # Remove scripts and styles
            content = re.sub(r'<script.*?>.*?</script>', '', content, flags=re.DOTALL)
            content = re.sub(r'<style.*?>.*?</style>', '', content, flags=re.DOTALL)
            # Remove tags
            text = re.sub('<[^<]+?>', ' ', content)
            # Clean whitespace
            text = ' '.join(text.split())
            
            title_match = re.search(r'<title>(.*?)</title>', response.text, re.IGNORECASE)
            title = title_match.group(1) if title_match else 'No Title'
            
            preview = text[:2000]
            return f"SUCCESS:\nTitle: {title}\n\nContent Preview:\n{preview}..."
        elif response.status_code in (403, 503):
            return f"STATUS: BLOCKED (HTTP {response.status_code}). Site rejected the request."
        else:
            return f"Error: Status {response.status_code}"
            
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python browser.py <url>")
    else:
        print(browse_web(sys.argv[1]))
