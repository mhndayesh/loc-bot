import requests
from bs4 import BeautifulSoup

def fetch_webpage(url):
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup.get_text()
    else:
        return f'Failed to fetch. Status code: {response.status_code}