import os
import feedparser
import requests
from google import genai

DISCORD_WEBHOOK = os.environ["DISCORD_WEBHOOK_URL"]
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

FEEDS = [
    "https://news.google.com/rss/search?q=AI+models+when:1d&hl=en-US&gl=US&ceid=US:en",
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://www.artificialintelligence-news.com/feed/",
]

MAX_PER_FEED = 6


def fetch_all():
    items = []
    for url in FEEDS:
        feed = feedparser.parse(url)
        for entry in feed.entries[:MAX_PER_FEED]:
            summary = getattr(entry, "summary", "")
            items.append(
                f"Title: {entry.title}\nLink: {entry.link}\nSnippet: {summary}\n"
            )
    return items


def summarize(items):
    if not items:
        return None

    raw_text = "\n---\n".join(items)
    prompt = f"""Here are today's raw AI/AI-model news items (titles, links, snippets).

{raw_text}

Write a concise Discord-friendly digest:
- Group related stories together, drop duplicates/near-duplicates
- 1-2 sentences per story max, plain language
- Keep the source link for each story
- Use Discord markdown (bold headers with **, bullet points with -)
- Skip anything not actually about AI/AI models (ignore unrelated results)
- Keep the whole thing under 1800 characters total
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return response.text


def post_to_discord(text):
    if not text:
        print("Nothing to post.")
        return
    if len(text) > 1900:
        text = text[:1900] + "\n...(truncated)"
    resp = requests.post(DISCORD_WEBHOOK, json={"content": text}, timeout=30)
    resp.raise_for_status()
    print("Posted to Discord successfully.")


if __name__ == "__main__":
    items = fetch_all()
    print(f"Fetched {len(items)} items")

    digest = summarize(items)
    print("---DIGEST---")
    print(digest)

    post_to_discord(digest)
