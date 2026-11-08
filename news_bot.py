import os
import re
import html
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
        "type": "deals",
        "prompt": """Here are today's current game deals and discounts (titles, links, prices).

{items}

Write a concise Discord-friendly digest:
- Group related deals together, drop duplicates/near-duplicates
- Focus on FREE games and the biggest discounts on Steam, Epic Games Store, and GOG
- Always include the sale price, the original price, and the discount percentage
- 1-2 sentences per deal max, plain language
- Keep the source link for each deal
- Use Discord markdown (bold headers with **, bullet points with -)
- Skip anything that is not an actual discount or a free game
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
        # used when cenoteka.rs blocks the request (Cloudflare often blocks GitHub runners)
        "fallback_url": "https://nafta.hr/sr/cene-goriva-srbija/",
        "fallback_prompt": """Here are the current fuel prices in Serbia per gas station company from nafta.hr:

{items}

Write a short Discord-friendly update in Serbian:
- For each fuel type (Eurodizel, Eurodizel Premium, BMB 95, BMB 95 Premium, BMB 100, Autoplin/TNG) show the lowest price in RSD
- Mention until when the prices are valid
- Use Discord markdown (bold with **)
- Keep it under 500 characters
- Do not add any links
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

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}


def fetch_all(feeds):
    items = []
    seen = set()
    for url in feeds:
        feed = feedparser.parse(url)
        for entry in feed.entries[:MAX_PER_FEED]:
            link = getattr(entry, "link", "")
            if link in seen:
                continue
            seen.add(link)
            summary = getattr(entry, "summary", "")
            items.append(
                f"Title: {entry.title}\nLink: {link}\nSnippet: {summary}\n"
            )
    return items


def _discount_items(store, deals, limit):
    """Format a list of (discount_percent, title, link, price_line) tuples."""
    deals.sort(key=lambda d: (-d[0], d[1].lower()))
    items = []
    for pct, title, link, price in deals[:limit]:
        if pct >= 100:
            deal_line = f"Deal: FREE on {store} — {price}\n"
        else:
            deal_line = f"Deal: -{pct}% on {store} — {price}\n"
        items.append(f"Title: {title}\nLink: {link}\n{deal_line}")
    return items


def fetch_steam_deals(limit=10):
    # The old feeds (newreleases.xml / topsellers.xml) are Steam *news*, not
    # discounts, so they returned the same news page every run. The specials
    # section of featuredcategories has real discount_percent/price values.
    resp = requests.get(
        "https://store.steampowered.com/api/featuredcategories?cc=us&l=en",
        timeout=30,
        headers=HEADERS,
    )
    resp.raise_for_status()

    deals = []
    for item in resp.json().get("specials", {}).get("items", []):
        pct = item.get("discount_percent", 0)
        if not item.get("discounted") or pct <= 0:
            continue
        currency = item.get("currency", "USD")
        symbol = {"USD": "$", "EUR": "€", "GBP": "£"}.get(currency, "")
        final = item.get("final_price", 0) / 100
        original = item.get("original_price", 0) / 100
        price = f"{symbol}{final:.2f} (was {symbol}{original:.2f})"
        deals.append(
            (
                pct,
                item["name"],
                f"https://store.steampowered.com/app/{item['id']}/",
                price,
            )
        )
    return _discount_items("Steam", deals, limit)


def fetch_gog_deals(limit=8):
    resp = requests.get(
        "https://catalog.gog.com/v1/catalog?limit=20&order=desc:discount"
        "&productType=in:game&countryCode=US&locale=en-US&currencyCode=USD",
        timeout=30,
        headers=HEADERS,
    )
    resp.raise_for_status()

    deals = []
    for product in resp.json().get("products", []):
        price = product.get("price", {})
        try:
            pct = abs(int(price.get("discount", "0").strip("-%")))
        except ValueError:
            pct = 0
        if pct <= 0:
            continue
        price_line = f"{price.get('final')} (was {price.get('base')})"
        deals.append(
            (
                pct,
                product["title"],
                product["storeLink"],
                price_line,
            )
        )
    return _discount_items("GOG", deals, limit)


def fetch_cheapshark_deals(limit=8):
    resp = requests.get(
        "https://www.cheapshark.com/api/1.0/deals"
        "?storeID=1&onSale=1&pageSize=20&sortBy=Recent",
        timeout=30,
        headers=HEADERS,
    )
    resp.raise_for_status()

    deals = []
    for deal in resp.json():
        try:
            pct = int(float(deal.get("savings", 0)))
        except (TypeError, ValueError):
            pct = 0
        if pct <= 0:
            continue
        price_line = (
            f"${float(deal['salePrice']):.2f} "
            f"(was ${float(deal['normalPrice']):.2f})"
        )
        deals.append(
            (
                pct,
                deal["title"],
                f"https://www.cheapshark.com/redirect?dealID={deal['dealID']}",
                price_line,
            )
        )
    return _discount_items("Steam", deals, limit)


def fetch_epic_deals(limit=8):
    resp = requests.get(
        "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
        "?locale=en-US&country=US&allowCountries=US",
        timeout=30,
        headers=HEADERS,
    )
    resp.raise_for_status()

    deals = []
    for game in resp.json()["data"]["Catalog"]["searchStore"]["elements"]:
        offers = (game.get("promotions") or {}).get("promotionalOffers") or []
        if not offers:
            continue
        offer = offers[0]["promotionalOffers"][0]
        total = game.get("price", {}).get("totalPrice", {})
        original = total.get("originalPrice", 0)
        if original <= 0:
            continue
        final = total.get("discountPrice", 0)
        pct = round((original - final) / original * 100)
        if pct <= 0:
            continue
        fmt = total.get("fmtPrice", {})
        price_line = f"{fmt.get('discountPrice')} (was {fmt.get('originalPrice')})"
        if final == 0:
            price_line = f"was {fmt.get('originalPrice')}"
        page_slug = None
        for mapping in game.get("offerMappings") or []:
            if mapping.get("pageType") == "productHome":
                page_slug = mapping.get("pageSlug")
                break
        page_slug = page_slug or game.get("productSlug") or game.get("urlSlug")
        link = (
            f"https://store.epicgames.com/en-US/p/{page_slug}"
            if page_slug
            else "https://store.epicgames.com/en-US/free-games"
        )
        deals.append(
            (
                pct,
                game["title"],
                link,
                f"{price_line}, until {offer['endDate'][:10]}",
            )
        )
    return _discount_items("Epic Games", deals, limit)


def fetch_game_deals():
    """Collect real discounts from the stores and remove cross-source duplicates."""
    items = []
    seen_titles = set()
    sources = [
        ("Steam", fetch_steam_deals),
        ("GOG", fetch_gog_deals),
        ("Epic", fetch_epic_deals),
        ("CheapShark", fetch_cheapshark_deals),
    ]
    for name, fetch in sources:
        try:
            source_items = fetch()
        except Exception as e:
            print(f"Greška pri preuzimanju {name} dealova: {e}")
            continue
        for item in source_items:
            title = item.split("\n", 1)[0].removeprefix("Title: ").strip().casefold()
            if title in seen_titles:
                continue
            seen_titles.add(title)
            items.append(item)
    return items


def scrape_fuel_prices(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    }
    resp = requests.get(url, timeout=30, headers=headers)
    print(f"cenoteka.rs status: {resp.status_code}, {len(resp.text)} bytes")
    text = resp.text

    # cenoteka.rs no longer ships __NEXT_DATA__; each product card carries
    # data-name / data-price attributes with the cheapest price instead
    matches = re.findall(r'data-name="([^"]+)"[^>]*?data-price="([\d.]+)"', text)

    fuel_names = {
        "Benzin BMB 95": "BMB 95",
        "Evro Dizel": "Dizel",
        "Auto Gas - TNG": "LPG/TNG",
        "Benzin BMB 100": "BMB 100",
        "Evro Dizel (Premijum)": "Dizel+",
    }

    fuel_prices = {}
    for name, price in matches:
        name = html.unescape(name)
        if name in fuel_names and fuel_names[name] not in fuel_prices:
            cheapest = float(price)
            if cheapest == int(cheapest):
                cheapest = int(cheapest)
            fuel_prices[fuel_names[name]] = f"{cheapest} RSD"

    result = []
    for label in ["BMB 95", "Dizel", "LPG/TNG", "BMB 100", "Dizel+"]:
        if label in fuel_prices:
            result.append(f"{label}: {fuel_prices[label]}")

    return "\n".join(result) if result else "Cene nisu dostupne"


def scrape_nafta_prices(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    }
    resp = requests.get(url, timeout=30, headers=headers)
    print(f"nafta.hr status: {resp.status_code}, {len(resp.text)} bytes")

    # strip scripts/styles and tags, keep the price tables as plain text
    text = re.sub(r"(?s)<(script|style).*?</\1>", "", resp.text)
    text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text)))

    start = text.find("Datum ažuriranja")
    if start == -1 or "RSD" not in text[start:]:
        return None
    # the price tables end where the FAQ section starts
    faq = text.find("najčešća pitanja", start)
    block = text[start:faq] if faq != -1 else text[start:start + 3000]
    return block.strip()


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

        prompt = config["prompt"]
        if config.get("type") == "scrape":
            try:
                items_text = scrape_fuel_prices(config["url"])
            except Exception as e:
                print(f"Greška pri preuzimanju cena goriva: {e}")
                items_text = "Cene nisu dostupne"
            if "Cene nisu dostupne" in items_text:
                print("cenoteka.rs nije dostupna, koristim nafta.hr")
                try:
                    items_text = scrape_nafta_prices(config["fallback_url"])
                except Exception as e:
                    print(f"Greška pri preuzimanju sa nafta.hr: {e}")
                    items_text = None
                if not items_text:
                    print("Cene goriva nisu dostupne ni na nafta.hr, preskačem")
                    continue
                prompt = config["fallback_prompt"]
        elif config.get("type") == "api":
            items_text = fetch_exchange_rates()
        elif config.get("type") == "deals":
            items = fetch_game_deals()
            print(f"Fetched {len(items)} deal items")
            items_text = "\n---\n".join(items)
        else:
            items = fetch_all(config["feeds"])
            print(f"Fetched {len(items)} items")
            items_text = "\n---\n".join(items)

        digest = summarize(items_text, prompt)
        print("---DIGEST---")
        print(digest.encode("utf-8", errors="replace").decode("utf-8"))

        post_to_discord(webhook, digest)
