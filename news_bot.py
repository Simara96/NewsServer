import os
import feedparser
import requests
from google import genai

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

TOPICS = {
    "ai": {
        "webhook": os.environ["DISCORD_WEBHOOK_URL"],
        "feeds": [
            "https://news.google.com/rss/search?q=new+AI+model+release+when:1d&hl=en-US&gl=US&ceid=US:en",
            "https://news.google.com/rss/search?q=GPT+Claude+Gemini+Llama+new+model+when:1d&hl=en-US&gl=US&ceid=US:en",
            "https://techcrunch.com/category/artificial-intelligence/feed/",
            "https://huggingface.co/blog/feed.xml",
        ],
        "prompt": """Here are today's raw AI model news items (titles, links, snippets).

{items}

Write a concise Discord-friendly digest:
- Group related stories together, drop duplicates/near-duplicates
- Focus on NEW AI model releases, announcements, and benchmarks from major companies (OpenAI, Anthropic, Google, Meta, Mistral, etc.)
- Include details like model name, company, and key capabilities if mentioned
- 1-2 sentences per story max, plain language
- Keep the source link for each story
- Use Discord markdown (bold headers with **, bullet points with -)
- Skip general AI opinion pieces, ethics debates, or non-model news
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
            "https://news.google.com/rss/search?q=popusti+tehnika+Srbija+when:1d&hl=sr&gl=RS&ceid=RS:sr",
            "https://news.google.com/rss/search?q=akcije+telefoni+laptopovi+Srbija+when:1d&hl=sr&gl=RS&ceid=RS:sr",
            "https://www.tehnomanija.rs/feed",
            "https://www.gigatron.rs/feed",
            "https://www.tehnomedia.rs/feed",
            "https://www.winwin.rs/feed",
            "https://www.kupujemprodajem.com/rss",
            "https://www.benchmark.rs/feed",
        ],
        "prompt": """Here are today's raw tech deal/discount news items from Serbia (titles, links, snippets).

{items}

Write a concise Discord-friendly digest in Serbian:
- Group related stories together, drop duplicates/near-duplicates
- Focus on tech deals, discounts, phone/laptop/hardware sales and offers in Serbia
- 1-2 sentences per story max, plain language
- Keep the source link for each story
- Use Discord markdown (bold headers with **, bullet points with -)
- Skip anything not related to tech deals or hardware discounts in Serbia
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
