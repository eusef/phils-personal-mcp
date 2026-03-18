#!/usr/bin/env python3
"""
Website scraper for philjohnstonii.com (Squarespace).
Scrapes profile and blog content with special handlers, auto-discovers all
other nav pages with a generic section-based scraper, and generates llms.txt
and llms-full.txt from the collected data.
Fork and customize for your own site and platform.
"""

import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
from urllib.parse import urljoin, urlparse

BASE_URL = "https://philjohnstonii.com"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "..", "data")

# Paths to skip during auto-discovery.
# "/" and "/blog" are handled by dedicated scrapers below.
# Add any page you want excluded from the scrape entirely (e.g. "/llms").
BLACKLISTED_PATHS = {"/", "/blog", "/llms"}

os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_timestamp():
    """Return current ISO timestamp."""
    return datetime.utcnow().isoformat() + "Z"


def fetch_page(url):
    """Fetch a page and return BeautifulSoup object."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.content, "html.parser")
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None


def discover_pages():
    """Discover all internal nav pages from the home page, excluding blacklisted paths."""
    soup = fetch_page(BASE_URL)
    if not soup:
        return []

    pages = []
    seen = set()
    for nav in soup.find_all("nav"):
        for link in nav.find_all("a"):
            href = link.get("href", "").strip()
            if not href.startswith("/") or href in seen or href in BLACKLISTED_PATHS:
                continue
            seen.add(href)
            pages.append(href)

    return pages


def scrape_page_generic(path):
    """
    Generically scrape any page into a list of heading+content sections.
    Works for any Squarespace (or similar) page without bespoke parsing.
    """
    url = urljoin(BASE_URL, path)
    soup = fetch_page(url)
    if not soup:
        return {}

    slug = path.strip("/").replace("/", "-")
    page = {
        "path": path,
        "url": url,
        "slug": slug,
        "title": None,
        "sections": [],
        "scraped_at": get_timestamp(),
        "last_updated": get_timestamp()
    }

    h1 = soup.find("h1")
    if h1:
        page["title"] = h1.get_text(strip=True)

    article = soup.find(["article", "main"]) or soup
    blocks = article.find_all(["h1", "h2", "h3", "h4", "p"])

    current_section = None
    for block in blocks:
        text = block.get_text(strip=True)
        if not text:
            continue
        if block.name in ["h1", "h2", "h3", "h4"]:
            if current_section:
                page["sections"].append(current_section)
            current_section = {"heading": text, "level": block.name, "content": []}
        elif current_section is not None:
            current_section["content"].append(text)
        else:
            page["sections"].append({"heading": None, "level": None, "content": [text]})

    if current_section:
        page["sections"].append(current_section)

    return page


def scrape_home():
    """Scrape home page for profile information."""
    url = urljoin(BASE_URL, "/")
    soup = fetch_page(url)

    if not soup:
        return {}

    profile = {
        "name": None,
        "tagline": None,
        "roles": [],
        "location": None,
        "website_url": BASE_URL,
        "contact_form_url": None,
        "scraped_at": get_timestamp(),
        "last_updated": get_timestamp()
    }

    h1 = soup.find("h1")
    if h1:
        profile["name"] = h1.get_text(strip=True)

    tagline = soup.find("h2")
    if tagline:
        profile["tagline"] = tagline.get_text(strip=True)

    for element in soup.find_all(["p", "div", "span"]):
        text = element.get_text(strip=True)
        if any(role in text for role in ["Developer Relations", "Photographer", "Tinkerer", "Developer", "Engineer"]):
            cleaned = text.replace("👨‍💻", "").replace("📸", "").replace("🔧", "").strip()
            if cleaned and cleaned not in profile["roles"]:
                profile["roles"].append(cleaned)

    for candidate in soup.find_all(["p", "span"]):
        text = candidate.get_text(strip=True).lower()
        if "based in" in text or "location" in text or any(city in text for city in ["san francisco", "california", "remote"]):
            profile["location"] = candidate.get_text(strip=True)
            break

    contact_link = soup.find("a", {"href": "/contact"})
    if contact_link:
        profile["contact_form_url"] = urljoin(BASE_URL, "/contact")
    else:
        for link in soup.find_all("a"):
            href = link.get("href", "").lower()
            text = link.get_text(strip=True).lower()
            if "contact" in href or "contact" in text:
                profile["contact_form_url"] = urljoin(BASE_URL, link.get("href", ""))
                break

    return profile


def scrape_blog_post(post_url):
    """Scrape individual blog post content."""
    soup = fetch_page(post_url)

    if not soup:
        return None

    post = {
        "url": post_url,
        "slug": post_url.split("/blog/")[-1].strip("/"),
        "title": None,
        "date": None,
        "excerpt": None,
        "full_content": None,
        "tags": []
    }

    title_elem = soup.find("h1")
    if title_elem:
        post["title"] = title_elem.get_text(strip=True)

    date_elem = soup.find(["time", "span"], {"class": ["date", "post-date", "published"]})
    if date_elem:
        post["date"] = date_elem.get_text(strip=True)
    else:
        for elem in soup.find_all(["span", "p"]):
            text = elem.get_text(strip=True)
            if any(month in text for month in ["January", "February", "March", "April", "May", "June",
                                                  "July", "August", "September", "October", "November", "December"]):
                post["date"] = text
                break

    article = soup.find(["article", "main"])
    if article:
        content_parts = []
        for p in article.find_all("p"):
            text = p.get_text(strip=True)
            if text:
                content_parts.append(text)
        if content_parts:
            post["full_content"] = " ".join(content_parts)

    tags = soup.find_all("a", {"class": ["tag", "post-tag"]})
    for tag in tags:
        tag_text = tag.get_text(strip=True)
        if tag_text and tag_text not in post["tags"]:
            post["tags"].append(tag_text)

    if not post["tags"]:
        for elem in soup.find_all(["span", "p"]):
            text = elem.get_text(strip=True)
            if text.startswith("#"):
                clean_tag = text.lstrip("#").strip()
                if clean_tag and clean_tag not in post["tags"]:
                    post["tags"].append(clean_tag)

    if not post["excerpt"] and post["full_content"]:
        post["excerpt"] = post["full_content"][:150] + "..."

    return post


def scrape_blog():
    """Scrape blog listing and individual posts."""
    url = urljoin(BASE_URL, "/blog")
    soup = fetch_page(url)

    if not soup:
        return {}

    blog = {
        "posts": [],
        "scraped_at": get_timestamp(),
        "last_updated": get_timestamp()
    }

    known_posts = [
        "/blog/phil-johnston-linkedin-leaving-linkedin-and-choosing-independence",
        "/blog/future-of-micro-niche-ai-tools",
        "/blog/encouraging-developers-to-share-their-stories",
        "/blog/micro-niche-vibe-coding"
    ]

    post_links = set()
    for link in soup.find_all("a"):
        href = link.get("href", "")
        if "/blog/" in href and href not in ["#", ""] and "/category/" not in href:
            full_url = urljoin(BASE_URL, href)
            if not full_url.rstrip("/").endswith("/blog"):
                post_links.add(full_url)

    for post_path in known_posts:
        post_links.add(urljoin(BASE_URL, post_path))

    for post_url in post_links:
        print(f"Scraping blog post: {post_url}")
        post = scrape_blog_post(post_url)
        if post:
            blog["posts"].append(post)

    for article in soup.find_all("article"):
        title = article.find(["h2", "h3"])
        excerpt = article.find("p")
        date = article.find(["time", "span"])

        if title and not any(p["title"] == title.get_text(strip=True) for p in blog["posts"]):
            post = {
                "title": title.get_text(strip=True),
                "date": date.get_text(strip=True) if date else None,
                "excerpt": excerpt.get_text(strip=True) if excerpt else None,
                "url": None,
                "slug": None,
                "full_content": None,
                "tags": []
            }
            link = article.find("a")
            if link and "/blog/" in link.get("href", ""):
                post["url"] = urljoin(BASE_URL, link.get("href"))
                post["slug"] = post["url"].split("/blog/")[-1].strip("/")
            blog["posts"].append(post)

    return blog


# ── llms.txt generation ────────────────────────────────────────────────────────

def _find_section(sections, keywords):
    """Find the first section whose heading contains any keyword (case-insensitive)."""
    for s in sections:
        heading = (s.get("heading") or "").lower()
        if any(kw.lower() in heading for kw in keywords):
            return s
    return None


def _merge_consulting_services(sections, page_title):
    """
    Normalise consulting sections into (services, track_record) where:
    - services: list of {name, price, description}
    - track_record: list of strings (bullet items without a price)

    Handles two Squarespace layout quirks:
    1. The h1 headline appears as the first section heading — skip it.
    2. Prices are sometimes their own <h4> section rather than paragraph
       content of the service section — merge them back.
    """
    services = []
    track_record = []
    current = None

    for s in sections:
        heading = s.get("heading") or ""
        content = s.get("content") or []

        # Skip the page headline (same text as page title)
        if heading == page_title:
            continue

        if "$" in heading:
            # Price-as-heading: attach to the preceding service
            if current is not None:
                current["price"] = heading
                if content and not current["description"]:
                    current["description"] = content[0]
        else:
            # Flush previous service
            if current is not None:
                if current.get("price"):
                    services.append(current)
                else:
                    track_record.append(current["name"])
            # Start new entry
            price = next((c for c in content if "$" in c), None)
            desc = next((c for c in content if "$" not in c and c), None)
            current = {"name": heading, "price": price, "description": desc}

    # Flush last entry
    if current is not None:
        if current.get("price"):
            services.append(current)
        else:
            track_record.append(current["name"])

    return services, track_record


def generate_llms_txt():
    """Generate llms.txt and llms-full.txt from all scraped JSON data."""

    def load_json(filename):
        filepath = os.path.join(OUTPUT_DIR, filename)
        if not os.path.exists(filepath):
            return {}
        with open(filepath) as f:
            return json.load(f)

    profile = load_json("profile.json")
    blog = load_json("blog.json")
    about = load_json("about-me.json")
    consulting = load_json("consulting.json")

    # All JSON files in data/ for the API endpoint list (exclude llms files)
    api_files = sorted(
        f for f in os.listdir(OUTPUT_DIR)
        if f.endswith(".json")
    )

    name = profile.get("name") or "Site Owner"
    website = profile.get("website_url") or BASE_URL
    roles = profile.get("roles") or []
    loc = profile.get("location") or ""
    contact = profile.get("contact_form_url") or ""
    tagline = profile.get("tagline") or ""
    posts = blog.get("posts") or []

    # ── llms.txt (concise) ────────────────────────────────────────────────────

    def build_concise():
        out = [f"# {name}", ""]

        if tagline:
            out += [f"> {tagline}", ""]

        # Profile
        out.append("## Profile")
        out.append("")
        if roles:
            out.append(f"Roles: {', '.join(roles)}")
        if loc:
            out.append(f"Location: {loc}")
        out.append(f"Website: {website}")
        if contact:
            out.append(f"Contact form: {contact}")
        out.append("")

        # Career
        career = _find_section(about.get("sections", []), ["career", "timeline"])
        if career and career.get("content"):
            out.append("## Career")
            out.append("")
            for item in career["content"]:
                out.append(f"- {item}")
            out.append("")

        # Technical Focus
        tech = _find_section(about.get("sections", []), ["technical", "tech stack"])
        if tech and tech.get("content"):
            out.append("## Technical Focus")
            out.append("")
            for item in tech["content"]:
                out.append(f"- {item}")
            out.append("")

        # What Sets Apart
        diff = _find_section(about.get("sections", []), ["sets", "apart", "differentiator"])
        if diff and diff.get("content"):
            out.append("## What Sets Me Apart")
            out.append("")
            for item in diff["content"]:
                out.append(item)
                out.append("")

        # Consulting
        if consulting.get("sections"):
            services, track_record = _merge_consulting_services(
                consulting["sections"], consulting.get("title", "")
            )
            if services or track_record:
                out.append("## Consulting")
                out.append("")
                if consulting.get("title"):
                    out += [consulting["title"], ""]
                for svc in services:
                    line = f"- {svc['name']}: {svc['price']}"
                    if svc.get("description"):
                        line += f". {svc['description']}"
                    out.append(line)
                if track_record:
                    out += ["", "Track record:"]
                    for tr in track_record:
                        out.append(f"- {tr}")
                out += ["", f"Booking: {urljoin(BASE_URL, '/consulting')}", ""]

        # Blog
        if posts:
            out.append("## Blog")
            out.append("")
            for post in posts:
                title = post.get("title") or "Untitled"
                date = post.get("date") or ""
                url = post.get("url") or ""
                line = f'- "{title}"'
                if date:
                    line += f" - {date}"
                if url:
                    line += f": {url}"
                out.append(line)
            out.append("")

        # Structured Data API
        out += ["## Structured Data API", "", "JSON endpoints (no auth required, updated daily):", ""]
        for fname in api_files:
            label = fname.replace("-", " ").replace(".json", "").title()
            out.append(f"- {label}: https://eusef.github.io/auto-llms-txt/api/{fname}")
        out.append("- Full content: https://eusef.github.io/auto-llms-txt/llms-full.txt")
        out += ["", "Source: https://github.com/eusef/auto-llms-txt", ""]

        return "\n".join(out)

    # ── llms-full.txt (verbose) ───────────────────────────────────────────────

    def build_full():
        out = [f"# {name} - Complete Profile", ""]

        if tagline:
            out += [f"> {tagline}", ""]
        out += ["---", ""]

        # Profile block
        out += ["## Profile", ""]
        out.append(f"Name: {name}")
        if tagline:
            out.append(f"Tagline: {tagline}")
        if roles:
            out.append(f"Roles: {', '.join(roles)}")
        if loc:
            out.append(f"Location: {loc}")
        out.append(f"Website: {website}")
        if contact:
            out.append(f"Contact: {contact}")
        out += ["", "---", ""]

        # About Me sections
        about_sections = about.get("sections") or []
        if about_sections:
            out += ["## Summary", ""]
            for s in about_sections:
                heading = s.get("heading") or ""
                content = s.get("content") or []
                if heading:
                    out += [f"### {heading}", ""]
                for c in content:
                    out.append(c)
                out.append("")
            out += ["---", ""]

        # Consulting full detail
        if consulting.get("sections"):
            services, track_record = _merge_consulting_services(
                consulting["sections"], consulting.get("title", "")
            )
            if services or track_record:
                out += ["## Consulting", ""]
                if consulting.get("title"):
                    out += [f"Headline: {consulting['title']}", ""]
                for svc in services:
                    out.append(f"### {svc['name']}")
                    out.append(f"Price: {svc['price']}")
                    if svc.get("description"):
                        out.append(f"Description: {svc['description']}")
                    out.append("")
                if track_record:
                    out += ["### Track Record", ""]
                    for tr in track_record:
                        out.append(f"- {tr}")
                    out.append("")
                out += [f"Booking: {urljoin(BASE_URL, '/consulting')}", "", "---", ""]

        # Blog full posts
        if posts:
            out += ["## Blog Posts", ""]
            for post in posts:
                title = post.get("title") or "Untitled"
                date = post.get("date") or ""
                url = post.get("url") or ""
                excerpt = post.get("excerpt") or ""
                tags = post.get("tags") or []
                out.append(f"### {title}")
                if date:
                    out.append(f"Published: {date}")
                if url:
                    out.append(f"URL: {url}")
                if excerpt:
                    out += ["", excerpt]
                if tags:
                    out.append(f"Tags: {', '.join(tags)}")
                out.append("")
            out += ["---", ""]

        # Structured Data API
        out += ["## Structured Data API", "",
                "All data is available as JSON at these public endpoints (no authentication required, updated daily):", ""]
        for fname in api_files:
            label = fname.replace("-", " ").replace(".json", "").title()
            out.append(f"- {label}: https://eusef.github.io/auto-llms-txt/api/{fname}")
        out += ["", "Source: https://github.com/eusef/auto-llms-txt", "", "---", "",
                f"Last updated: {get_timestamp()[:10]}", ""]

        return "\n".join(out)

    save_text("llms.txt", build_concise())
    save_text("llms-full.txt", build_full())


# ── I/O helpers ────────────────────────────────────────────────────────────────

def save_json(filename, data):
    """Save data to JSON file in output directory."""
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved: {filepath}")


def save_text(filename, content):
    """Save text content to output directory."""
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w") as f:
        f.write(content)
    print(f"Saved: {filepath}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    """Run the full scrape."""
    print(f"Starting scrape of {BASE_URL}")
    print(f"Timestamp: {get_timestamp()}")
    print()

    print("Scraping home page...")
    profile = scrape_home()
    save_json("profile.json", profile)
    print()

    print("Scraping blog...")
    blog = scrape_blog()
    save_json("blog.json", blog)
    print()

    print("Discovering pages...")
    pages = discover_pages()
    print(f"Found: {pages}")
    print()

    for path in pages:
        slug = path.strip("/").replace("/", "-")
        print(f"Scraping {path}...")
        page_data = scrape_page_generic(path)
        save_json(f"{slug}.json", page_data)

    print()
    print("Generating llms.txt and llms-full.txt...")
    generate_llms_txt()

    print()
    print("Scrape complete!")


if __name__ == "__main__":
    main()
