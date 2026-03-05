# Phil Johnston Personal MCP Server

A Model Context Protocol (MCP) server providing access to Phil Johnston's personal website data including profile, resume, and blog posts.

## Features

- **Profile Resource**: Phil's bio, tagline, roles, and contact information
- **Resume Resource**: Career timeline, technical focus areas, and professional differentiators
- **Blog Resources**: All blog posts and individual post access by slug
- **Search Tool**: Full-text search across blog posts
- **Data Caching**: 5-minute TTL cache with automatic refresh
- **Fallback Loading**: GitHub + local file fallback for data sources

## Installation

```bash
npm install
```

## Building

```bash
npm run build
```

## Running

```bash
npm start
```

Or directly:

```bash
node dist/index.js
```

## Development

```bash
npm run dev
```

## Architecture

### Resources (phil://)

- `phil://profile` - Phil's profile information
- `phil://resume` - Phil's resume and career info
- `phil://blog` - All blog posts
- `phil://blog/{slug}` - Individual blog post by slug (templated resource)

### Tools

- `get_profile()` - Get Phil's profile as JSON
- `get_resume()` - Get Phil's resume as JSON
- `search_blog(query)` - Search blog posts by title, excerpt, or content
- `get_blog_post(slug)` - Get a specific blog post by slug

### Data Sources

The server fetches data from two sources in order of preference:

1. **GitHub**: `https://raw.githubusercontent.com/eusef/phils-personal-mcp/main/data/`
2. **Local Fallback**: `../data/` directory (for local development)

Supported data files:
- `profile.json`
- `resume.json`
- `blog.json`

### Caching

- **TTL**: 5 minutes
- **Refresh**: Automatic on tool calls and resource reads
- **Policy**: Graceful fallback to local files if GitHub is unreachable

## Protocol

Uses stdio transport for MCP communication. The server is designed to be spawned by MCP clients.

## TypeScript Configuration

- **Target**: ES2022
- **Module**: NodeNext (ESM)
- **Strict Mode**: Enabled
- **Node Version**: 18+

## Files

```
server/
├── package.json          # Dependencies and scripts
├── tsconfig.json         # TypeScript configuration
├── src/
│   └── index.ts          # Main server implementation
└── dist/
    ├── index.js          # Compiled executable
    ├── index.d.ts        # Type definitions
    └── index.js.map      # Source maps
```
