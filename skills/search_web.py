
"""
search_web: Search the web via DuckDuckGo HTML (no API key needed).
"""
import sys
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser

class DDGParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.results = []
        self.in_result = False
        self.current_link = ""
        self.current_title = ""
        self.recording = False

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            d = dict(attrs)
            if "result__a" in d.get("class", ""):
                self.in_result = True
                self.current_link = d.get("href", "")
                self.recording = True

    def handle_endtag(self, tag):
        if tag == "a" and self.in_result:
            self.in_result = False
            self.recording = False
            if self.current_link and self.current_title:
                self.results.append(f"{self.current_title} ({self.current_link})")
                self.current_title = ""

    def handle_data(self, data):
        if self.recording:
            self.current_title += data.strip()

def run(query):
    try:
        url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
        
        parser = DDGParser()
        parser.feed(html)
        
        if not parser.results:
            return "No results found."
            
        return "\n".join(parser.results[:5])
    except Exception as e:
        return f"Error searching web: {e}"

if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(run(" ".join(sys.argv[1:])))
    else:
        print("Usage: python search_web.py <query>")
