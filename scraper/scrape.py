#!/usr/bin/env python3
"""
Scraper for Phil Johnston's personal website (philjohnstonii.com)
Scrapes profile, resume, and blog content to JSON files.
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

# Ensure output directory exists
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

    # Look for H1 with name
    h1 = soup.find("h1")
    if h1:
        profile["name"] = h1.get_text(strip=True)

    # Look for tagline/subtitle (common in Squarespace)
    tagline = soup.find("h2")
    if tagline:
        profile["tagline"] = tagline.get_text(strip=True)

    # Extract roles - look for common patterns
    # Roles are typically listed with emoji prefixes like "👨‍💻 Developer Relations"
    for element in soup.find_all(["p", "div", "span"]):
        text = element.get_text(strip=True)
        # Look for role-like text (contains common developer/creator roles)
        if any(role in text for role in ["Developer Relations", "Photographer", "Tinkerer", "Developer", "Engineer"]):
            # Clean up emoji and extract role
            cleaned = text.replace("👨‍💻", "").replace("📸", "").replace("🔧", "").strip()
            if cleaned and cleaned not in profile["roles"]:
                profile["roles"].append(cleaned)

    # Look for location info
    location_candidates = soup.find_all(["p", "span"])
    for candidate in location_candidates:
        text = candidate.get_text(strip=True).lower()
        if "based in" in text or "location" in text or any(city in text for city in ["san francisco", "california", "remote"]):
            profile["location"] = candidate.get_text(strip=True)
            break

    # Look for contact form link
    contact_link = soup.find("a", {"href": "/contact"})
    if contact_link:
        profile["contact_form_url"] = urljoin(BASE_URL, "/contact")
    else:
        # Try common contact form variations
        for link in soup.find_all("a"):
            href = link.get("href", "").lower()
            text = link.get_text(strip=True).lower()
            if "contact" in href or "contact" in text:
                profile["contact_form_url"] = urljoin(BASE_URL, link.get("href", ""))
                break

    return profile


def scrape_resume():
    """Scrape /about-me page for resume information."""
    url = urljoin(BASE_URL, "/about-me")
    soup = fetch_page(url)

    if not soup:
        return {}

    resume = {
        "summary": None,
        "career_timeline": [],
        "technical_focus": [],
        "differentiators": [],
        "scraped_at": get_timestamp(),
        "last_updated": get_timestamp()
    }

    # Extract summary (first few paragraphs)
    paragraphs = soup.find_all("p")
    if paragraphs:
        summary_parts = []
        for p in paragraphs[:3]:  # First 3 paragraphs as summary
            text = p.get_text(strip=True)
            if text and len(text) > 20:  # Skip short placeholders
                summary_parts.append(text)
        if summary_parts:
            resume["summary"] = " ".join(summary_parts)

    # Extract Career Timeline section
    career_section = None
    for heading in soup.find_all(["h2", "h3", "h4"]):
        if "career" in heading.get_text(strip=True).lower() and "timeline" in heading.get_text(strip=True).lower():
            career_section = heading
            break

    if career_section:
        current = career_section.find_next()
        while current and current.name not in ["h2", "h3", "h4"]:
            if current.name in ["p", "div"]:
                text = current.get_text(strip=True)
                # Look for year patterns like "2020-2022" or "2020 - 2022"
                if any(char.isdigit() for char in text) and text:
                    resume["career_timeline"].append(text)
            current = current.find_next()

    # Extract Technical Focus section (bullet list)
    tech_section = None
    for heading in soup.find_all(["h2", "h3", "h4"]):
        if "technical focus" in heading.get_text(strip=True).lower() or "tech stack" in heading.get_text(strip=True).lower():
            tech_section = heading
            break

    if tech_section:
        current = tech_section.find_next()
        while current and current.name not in ["h2", "h3", "h4"]:
            if current.name == "ul":
                for li in current.find_all("li"):
                    text = li.get_text(strip=True)
                    if text:
                        resume["technical_focus"].append(text)
                break
            elif current.name in ["li"]:
                text = current.get_text(strip=True)
                if text:
                    resume["technical_focus"].append(text)
            current = current.find_next()

    # Extract "What Sets Me Apart" section (differentiators)
    diff_section = None
    for heading in soup.find_all(["h2", "h3", "h4"]):
        heading_text = heading.get_text(strip=True).lower()
        if any(phrase in heading_text for phrase in ["what sets", "differentiators", "apart", "unique"]):
            diff_section = heading
            break

    if diff_section:
        current = diff_section.find_next()
        while current and current.name not in ["h2", "h3", "h4"]:
            if current.name in ["p", "div"]:
                text = current.get_text(strip=True)
                if text and len(text) > 15:
                    resume["differentiators"].append(text)
            current = current.find_next()

    return resume


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

    # Extract title
    title_elem = soup.find("h1")
    if title_elem:
        post["title"] = title_elem.get_text(strip=True)

    # Extract date (look for common date patterns)
    date_elem = soup.find(["time", "span"], {"class": ["date", "post-date", "published"]})
    if date_elem:
        post["date"] = date_elem.get_text(strip=True)
    else:
        # Look for date in meta or other elements
        for elem in soup.find_all(["span", "p"]):
            text = elem.get_text(strip=True)
            if any(month in text for month in ["January", "February", "March", "April", "May", "June",
                                                  "July", "August", "September", "October", "November", "December"]):
                post["date"] = text
                break

    # Extract full content (main article body)
    article = soup.find(["article", "main"])
    if article:
        content_parts = []
        for p in article.find_all("p"):
            text = p.get_text(strip=True)
            if text:
                content_parts.append(text)
        if content_parts:
            post["full_content"] = " ".join(content_parts)

    # Extract tags (look for common tag patterns)
    tags = soup.find_all("a", {"class": ["tag", "post-tag"]})
    for tag in tags:
        tag_text = tag.get_text(strip=True)
        if tag_text and tag_text not in post["tags"]:
            post["tags"].append(tag_text)

    # If no tags found, look in post content for hashtags or tag-like content
    if not post["tags"]:
        for elem in soup.find_all(["span", "p"]):
            text = elem.get_text(strip=True)
            if text.startswith("#"):
                clean_tag = text.lstrip("#").strip()
                if clean_tag and clean_tag not in post["tags"]:
                    post["tags"].append(clean_tag)

    # Set excerpt if not found (use first 150 chars of full content)
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

    # Known blog post URLs to scrape
    known_posts = [
        "/blog/phil-johnston-linkedin-leaving-linkedin-and-choosing-independence",
        "/blog/future-of-micro-niche-ai-tools",
        "/blog/encouraging-developers-to-share-their-stories",
        "/blog/micro-niche-vibe-coding"
    ]

    # First, try to find blog post links on the listing page
    post_links = set()
    for link in soup.find_all("a"):
        href = link.get("href", "")
        if "/blog/" in href and href not in ["#", ""] and "/category/" not in href:
            full_url = urljoin(BASE_URL, href)
            # Skip the blog listing page itself
            if not full_url.rstrip("/").endswith("/blog"):
                post_links.add(full_url)

    # Add known posts if not already found
    for post_path in known_posts:
        full_url = urljoin(BASE_URL, post_path)
        post_links.add(full_url)

    # Scrape each blog post
    for post_url in post_links:
        print(f"Scraping blog post: {post_url}")
        post = scrape_blog_post(post_url)
        if post:
            blog["posts"].append(post)

    # Also extract excerpt from blog listing if available
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

            # Try to find URL in article
            link = article.find("a")
            if link and "/blog/" in link.get("href", ""):
                post["url"] = urljoin(BASE_URL, link.get("href"))
                post["slug"] = post["url"].split("/blog/")[-1].strip("/")

            blog["posts"].append(post)

    return blog


def save_json(filename, data):
    """Save data to JSON file in output directory."""
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved: {filepath}")


def main():
    """Run the full scrape."""
    print(f"Starting scrape of {BASE_URL}")
    print(f"Timestamp: {get_timestamp()}")
    print()

    print("Scraping home page...")
    profile = scrape_home()
    save_json("profile.json", profile)
    print()

    print("Scraping resume page...")
    resume = scrape_resume()
    save_json("resume.json", resume)
    print()

    print("Scraping blog...")
    blog = scrape_blog()
    save_json("blog.json", blog)
    print()

    print("Scrape complete!")


if __name__ == "__main__":
    main()
