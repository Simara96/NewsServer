import os
import feedparser
import requests
from google import genai

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

TOPICS = {
    "ai": {
        "webhook": os.environ["DISCORD_WEBHOOK_URL"],
        "feeds": [
            "https://news.google.com/rss/search?q=AI+models+when:1d&hl=en-US&gl=US&ceid=US:en",
            "https://techcrunch.com/category/artificial-intelligence/feed/",
            "https://www.artificialintelligence-news.com/feed/",
        ],
        "prompt": """Here are today's raw AI/AI-model news items (titles, links, snippets).

{items}

Write a concise Discord-friendly digest:
- Group related stories together, drop duplicates/near-duplicates
- 1-2 sentences per story max, plain language
- Keep the source link for each story
- Use Discord markdown (bold headers with **, bullet points with -)
- Skip anything not actually about AI/AI models (ignore unrelated results)
- Keep the whole thing under 1800 characters total
""",
    },
    "gaming": {
        "webhook": os.environ.get("GAMING_DISCORD_WEBHOOK_URL"),
        "feeds": [
            "https://news.google.com/rss/search?q=free+PC+games+when:1d&hl=en-US&gl=US&ceid=US:en",
            "https://www.pcgamer.com/rss/",
            "https://store.steampowered.com/feeds/news/",
        ],
        "prompt": """Here are today's raw free PC gaming news items (titles, links, snippets).

{items}

Write a concise Discord-friendly digest:
- Group related stories together, drop duplicates/near-duplicates
- Focus on FREE games, deals, giveaways, and free-to-play news
- 1-2 sentences per story max, plain language
- Keep the source link for each story
- Use Discord markdown (bold headers with **, bullet points with -)
- Skip anything not about free PC games or gaming deals
- Keep the whole thing under 1800 characters total
""",
    },
    "tech_srbija": {
        "webhook": os.environ.get("TECH_SRBija_DISCORD_WEBHOOK_URL"),
        "feeds": [
            "https://news.google.com/rss/search?q=tech+Srbija+when:1d&hl=sr&gl=RS&ceid=RS:sr",
            "https://www.startit.rs/feed/",
            "https://pcpress.rs/feed/",
            "https://www.benchmark.rs/feed",
        ],
        "prompt": """Here are today's raw tech news items from Serbia (titles, links, snippets).

{items}

Write a concise Discord-friendly digest in Serbian:
- Group related stories together, drop duplicates/near-duplicates
- Focus on Serbian tech scene, startups, IT industry, digital transformation
- 1-2 sentences per story max, plain language
- Keep the source link for each story
- Use Discord markdown (bold headers with **, bullet points with -)
- Skip anything not related to tech in Serbia
- Keep the whole thing under 1800 characters total
""",
    },
}

MAX_PER_FEED = 6


def fetch_all(feeds):
    items = []
    for url in feeds:
        feed = feedparser.parse(url)
        for entry in feed.entries[:MAX_PER_FEED]:
            summary = getattr(entry, "summary", "")
            items.append(
                f"Title: {entry.title}\nLink: {entry.link}\nSnippet: {summary}\n"
            )
    return items


def summarize(items, prompt_template):
    if not items:
        return None

    raw_text = "\n---\n".join(items)
    prompt = prompt_template.format(items=raw_text)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return response.text


def post_to_discord(webhook, text):
    if not text:
        print("Nothing to post.")
        return
    if len(text) > 1900:
        text = text[:1900] + "\n...(truncated)"
    resp = requests.post(webhook, json={"content": text}, timeout=30)
    resp.raise_for_status()
    print("Posted to Discord successfully.")


if __name__ == "__main__":
    for topic, config in TOPICS.items():
        webhook = config["webhook"]
        if not webhook:
            print(f"Skipping {topic}: no webhook configured")
            continue

        print(f"\n=== {topic.upper()} ===")
        items = fetch_all(config["feeds"])
        print(f"Fetched {len(items)} items")

        digest = summarize(items, config["prompt"])
        print("---DIGEST---")
        print(digest)

        post_to_discord(webhook, digest)
