import feedparser

FEEDS = {
    "business": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-IN&gl=IN&ceid=IN:en",
    "trading": "https://news.google.com/rss/search?q=share+market+trading+stocks+to+buy+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
    "global": "https://news.google.com/rss/search?q=wall+street+global+markets+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
    "commodities": "https://news.google.com/rss/search?q=gold+crude+oil+price+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
    "market": "https://news.google.com/rss/search?q=stock+market+india+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
    "ipo": "https://news.google.com/rss/search?q=IPO+india+GMP+listing+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
    "india": "https://news.google.com/rss/search?q=nifty+sensex+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
    "forex": "https://news.google.com/rss/search?q=usd+inr+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
    "crypto": "https://www.coindesk.com/arc/outboundfeeds/rss/",
}

def get_news(category: str, limit: int = 10):
    feed = feedparser.parse(FEEDS[category])
    return [
        {
            "title": e.title,
            "link": e.link,
            "published": e.get("published"),
            "source": e.get("source", {}).get("title"),
        }
        for e in feed.entries[:limit]
    ]