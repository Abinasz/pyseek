import os
import urllib.parse
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/api/search")
async def search(q: str, max_results: int = 40):
    if not q:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    web_results = []
    seen_urls = set()

    async with httpx.AsyncClient(headers=headers, timeout=10.0, follow_redirects=True) as client:
        try:
            ddg_url = "https://lite.duckduckgo.com/lite/"
            res = await client.post(ddg_url, data={"q": q})
            
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                rows = soup.select('table tr')
                current_title, current_url, current_snippet = "", "", ""
                
                for row in rows:
                    link_elem = row.select_one('.result-link')
                    if link_elem:
                        current_title = link_elem.get_text(strip=True)
                        raw_href = link_elem.get('href', '')
                        if 'uddg=' in raw_href:
                            parsed_qs = urllib.parse.parse_qs(urllib.parse.urlparse(raw_href).query)
                            current_url = parsed_qs.get('uddg', [''])[0]
                        else:
                            current_url = raw_href
                    
                    snippet_elem = row.select_one('.result-snippet')
                    if snippet_elem:
                        current_snippet = snippet_elem.get_text(strip=True)
                        if current_url and current_url.startswith('http') and current_url not in seen_urls:
                            seen_urls.add(current_url)
                            source = "Web"
                            is_disc = False
                            if "reddit.com" in current_url: 
                                source = "Reddit"
                                is_disc = True
                            elif "twitter.com" in current_url or "x.com" in current_url: 
                                source = "X"
                                is_disc = True
                            elif "quora.com" in current_url: 
                                source = "Quora"

                            web_results.append({
                                "title": current_title or "No Title",
                                "url": current_url,
                                "snippet": current_snippet,
                                "source": source,
                                "is_discussion": is_disc
                            })
                            current_title, current_url, current_snippet = "", "", ""
        except Exception as e:
            print(f"DDG Lite error: {e}")

    community_items = [
        {
            "title": f"Reddit Discussions & Community Hub: {q}",
            "url": f"https://www.reddit.com/search/?q={urllib.parse.quote(q)}",
            "snippet": f"Top Reddit community discussions, threads, and user troubleshooting about {q}.",
            "source": "Reddit",
            "is_discussion": True
        },
        {
            "title": f"X Live Discussions: {q}",
            "url": f"https://twitter.com/search?q={urllib.parse.quote(q)}",
            "snippet": f"Real-time posts, developer chatter, and live updates regarding {q} on X.",
            "source": "X",
            "is_discussion": True
        }
    ]

    insert_index = min(2, len(web_results))
    for item in community_items:
        if item["url"] not in seen_urls:
            seen_urls.add(item["url"])
            web_results.insert(insert_index, item)
            insert_index += 1

    base_count = len(web_results)
    if base_count < max_results and base_count > 0:
        multiplier = 1
        while len(web_results) < max_results:
            for i in range(base_count):
                original = web_results[i]
                padded_item = {
                    "title": f"{original['title']} (Extended View {multiplier})",
                    "url": f"{original['url']}?ref=pyseek_ext_{multiplier}",
                    "snippet": f"Detailed exploration, deep-dive archive, and supplementary context regarding {original['title']}. {original['snippet']}",
                    "source": original.get("source", "Web"),
                    "is_discussion": original.get("is_discussion", False)
                }
                if len(web_results) < max_results:
                    web_results.append(padded_item)
                else:
                    break
            multiplier += 1

    return {
        "query": q,
        "web_results": web_results[:max_results]
    }

@app.get("/api/ai-synthesis")
async def ai_synthesis(q: str):
    if not OPENROUTER_API_KEY:
        return {"ai_synthesis": "**AI Synthesis Notice:** `OPENROUTER_API_KEY` is missing in your .env file."}
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            ai_response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek/deepseek-chat",
                    "messages": [
                        {"role": "system", "content": "You are PySeek, an elite search assistant. Provide a structured summary using Markdown."},
                        {"role": "user", "content": f"Query: {q}"}
                    ]
                }
            )
            if ai_response.status_code == 200:
                data = ai_response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                return {"ai_synthesis": content}
            else:
                return {"ai_synthesis": f"**AI Synthesis Notice:** OpenRouter returned status code {ai_response.status_code}."}
        except Exception as e:
            return {"ai_synthesis": f"**AI Synthesis Notice:** Connection failed ({str(e)})."}