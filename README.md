# Phil Johnston, II - Personal API

Turns my personal website ([philjohnstonii.com](https://philjohnstonii.com)) into a structured API that LLMs and agents can discover and query.

## How It Works

1. A GitHub Action scrapes my Squarespace site daily and commits structured JSON to `data/`
2. GitHub Pages serves those JSON files as a public API at `eusef.github.io/phils-personal-mcp/api/`
3. An `llms.txt` file on my website points agents to the API and includes my full profile inline
4. An optional MCP server in `server/` provides deeper integration for tools like Claude Desktop

## API Endpoints

No authentication required. Updated daily at 6 AM UTC.

| Endpoint | Description |
|---|---|
| [`/api/profile.json`](https://eusef.github.io/phils-personal-mcp/api/profile.json) | Bio, roles, location, contact |
| [`/api/resume.json`](https://eusef.github.io/phils-personal-mcp/api/resume.json) | Career timeline, skills, differentiators |
| [`/api/blog.json`](https://eusef.github.io/phils-personal-mcp/api/blog.json) | All blog posts with excerpts |
| [`/llms.txt`](https://eusef.github.io/phils-personal-mcp/llms.txt) | Standard llms.txt with full inline content |
| [`/llms-full.txt`](https://eusef.github.io/phils-personal-mcp/llms-full.txt) | Complete profile for direct LLM consumption |

## Project Structure

```
phils-personal-mcp/
├── data/                        # Scraped JSON (auto-updated by GitHub Action)
│   ├── profile.json
│   ├── resume.json
│   └── blog.json
├── scraper/
│   ├── scrape.py                # Python scraper for Squarespace site
│   └── requirements.txt
├── server/                      # Optional MCP server (stdio transport)
│   ├── src/index.ts
│   ├── package.json
│   └── tsconfig.json
├── docs/
│   └── index.html               # GitHub Pages landing page
├── .github/workflows/
│   └── scrape.yml               # Daily scrape + Pages deployment
├── llms.txt                     # For Squarespace + GitHub Pages
└── llms-full.txt                # Full content dump
```

## MCP Server (Optional)

For agent frameworks that support the [Model Context Protocol](https://modelcontextprotocol.io), a stdio-based server is available.

```bash
cd server
npm install
npm run build
```

### Claude Desktop Configuration

```json
{
  "mcpServers": {
    "phil-johnston": {
      "command": "node",
      "args": ["/path/to/phils-personal-mcp/server/dist/index.js"]
    }
  }
}
```

### Available Tools

| Tool | Description |
|---|---|
| `get_profile` | Bio, roles, and contact info |
| `get_resume` | Career timeline, technical skills, differentiators |
| `search_blog` | Search posts by keyword |
| `get_blog_post` | Get a specific post by slug |

## Setup

To deploy your own version:

1. Fork this repo
2. Enable GitHub Pages (Settings > Pages > Source: GitHub Actions)
3. Run the workflow manually (Actions > "Scrape Website & Deploy" > Run workflow)
4. Upload `llms.txt` to your website root
5. Verify at `https://<your-username>.github.io/<repo-name>/api/profile.json`

## Discovery Flow

```
Agent visits philjohnstonii.com/llms.txt
  → Gets full profile inline (enough for most queries)
  → Follows API links for structured JSON
  → Optionally installs MCP server for tool-based access
```

## License

MIT
