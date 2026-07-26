import os
import re
import feedparser
import requests
from google import genai

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

TOPICS = {
    "ai": {
        "webhook": os.environ.get("DISCORD_WEBHOOK_URL"),
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
    "game_deals": {
        "webhook": os.environ.get("GAME_DEALS_DISCORD_WEBHOOK_URL"),
        "feeds": [
            "https://store.steampowered.com/feeds/newreleases.xml",
            "https://store.steampowered.com/feeds/topsellers.xml",
            "https://www.gog.com/games/rss",
            "https://store.epicgames.com/en-US/free-games",
            "https://gg.deals/rss/",
            "https://www.cheapshark.com/rss/deals",
        ],
        "prompt": """Here are today's raw game deal/discount news items (titles, links, snippets).

{items}

Write a concise Discord-friendly digest:
- Group related stories together, drop duplicates/near-duplicates
- Focus on FREE games, significant discounts, and sales on Steam, Epic Games Store, and GOG
- Include original and sale prices if mentioned
- 1-2 sentences per story max, plain language
- Keep the source link for each story
- Use Discord markdown (bold headers with **, bullet points with -)
- Skip anything not related to game deals or discounts
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
    "gorivo": {
        "webhook": os.environ.get("GORIVO_DISCORD_WEBHOOK_URL"),
        "type": "scrape",
        "url": "https://cenoteka.rs/cene-goriva/",
        "prompt": """Here are the current fuel prices in Serbia from cenoteka.rs:

{items}

Write a short Discord-friendly update in Serbian:
- Show current prices for all fuel types
- Use Discord markdown (bold with **)
- Keep it under 500 characters
- Add source link: https://cenoteka.rs/cene-goriva/
""",
    },
    "kursevi": {
        "webhook": os.environ.get("KURSEVI_DISCORD_WEBHOOK_URL"),
        "type": "api",
        "prompt": """Here are the current official middle exchange rates from the National Bank of Serbia (NBS):

{items}

Write a short Discord-friendly update in Serbian:
- Show EUR, USD, CHF, GBP, CAD rates against RSD
- Use Discord markdown (bold with **)
- Keep it under 500 characters
- Mention it's the official NBS srednji kurs
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


def scrape_fuel_prices(url):
    resp = requests.get(url, timeout=30)
    text = resp.text

    fuel_prices = {}

    fuel_patterns = {
        "Benzin BMB 95": "BMB 95",
        "Evro Dizel": "Dizel",
        "Auto Gas - TNG": "LPG/TNG",
        "Benzin BMB 100": "BMB 100",
        "Evro Dizel \\(Premijum\\)": "Dizel+",
    }

    for fuel_name, label in fuel_patterns.items():
        pattern = fuel_name + r".*?(\d+[\.,]\d+)"
        match = re.search(pattern, text)
        if match:
            price = match.group(1).replace(",", ".")
            fuel_prices[label] = price + " RSD"

    result = []
    for label in ["BMB 95", "Dizel", "LPG/TNG", "BMB 100", "Dizel+"]:
        if label in fuel_prices:
            result.append(f"{label}: {fuel_prices[label]}")

    return "\n".join(result) if result else "Cene nisu dostupne"


def fetch_exchange_rates():
    resp = requests.get("https://kurs.resenje.org/api/v1/rates/today", timeout=30)
    data = resp.json()

    currencies = {
        "EUR": "Evro",
        "USD": "Američki dolar",
        "CHF": "Švajcarski franak",
        "GBP": "Britanska funta",
        "CAD": "Kanadski dolar",
    }

    rates = {}
    date = ""
    for item in data.get("rates", []):
        if item["code"] in currencies:
            rates[item["code"]] = item["exchange_middle"]
            date = item["date"]

    result = [f"Kurs RSD ({date}):\n"]
    for code, name in currencies.items():
        if code in rates:
            result.append(f"1 {code} = {rates[code]:.2f} RSD ({name})")

    result.append("\nIzvor: Narodna banka Srbije (kurs.resenje.org)")
    return "\n".join(result)


def summarize(items_text, prompt_template):
    if not items_text:
        return None

    prompt = prompt_template.format(items=items_text)

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
    run_gorivo_only = os.environ.get("RUN_GORIVO_ONLY") == "true"

    for topic, config in TOPICS.items():
        if run_gorivo_only and topic != "gorivo":
            continue
        if not run_gorivo_only and topic == "gorivo":
            continue

        webhook = config["webhook"]
        if not webhook:
            print(f"Skipping {topic}: no webhook configured")
            continue

        print(f"\n=== {topic.upper()} ===")

        if config.get("type") == "scrape":
            items_text = scrape_fuel_prices(config["url"])
        elif config.get("type") == "api":
            items_text = fetch_exchange_rates()
        else:
            items = fetch_all(config["feeds"])
            print(f"Fetched {len(items)} items")
            items_text = "\n---\n".join(items)

        digest = summarize(items_text, config["prompt"])
        print("---DIGEST---")
        print(digest.encode("utf-8", errors="replace").decode("utf-8"))

        post_to_discord(webhook, digest)
