#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ReadResourceRequestSchema,
  ListResourcesRequestSchema,
  ListResourceTemplatesRequestSchema,
  Tool,
  Resource,
  ResourceTemplate,
} from "@modelcontextprotocol/sdk/types.js";

// TypeScript interfaces for data shapes
interface ProfileData {
  name: string;
  tagline: string;
  roles: string[];
  location: string;
  website_url: string;
  contact_form_url: string;
  scraped_at: string;
  last_updated: string;
}

interface CareerEntry {
  year: string;
  role: string;
  company: string;
}

interface Differentiator {
  title: string;
  description: string;
}

interface ResumeData {
  summary: string;
  career_timeline: CareerEntry[];
  technical_focus: string[];
  differentiators: Differentiator[];
  scraped_at: string;
  last_updated: string;
}

interface BlogPost {
  title: string;
  date: string;
  url: string;
  slug: string;
  excerpt: string;
  full_content: string | null;
  tags: string[];
}

interface BlogData {
  posts: BlogPost[];
  scraped_at: string;
  last_updated: string;
}

interface CachedData {
  profile: ProfileData | null;
  resume: ResumeData | null;
  blog: BlogData | null;
  timestamp: number;
}

const CACHE_TTL = 5 * 60 * 1000; // 5 minutes in milliseconds
const DATA_DIR = "../data";
const GITHUB_RAW_BASE = "https://raw.githubusercontent.com/eusef/phils-personal-mcp/main/data";

let cache: CachedData = {
  profile: null,
  resume: null,
  blog: null,
  timestamp: 0,
};

async function fetchJSON(url: string): Promise<unknown> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch ${url}: ${response.status}`);
  }
  return response.json();
}

async function loadLocalJSON(filename: string): Promise<unknown> {
  const fs = await import("fs/promises");
  const path = await import("path");
  const { fileURLToPath } = await import("url");
  const __dirname = path.dirname(fileURLToPath(import.meta.url));
  const filePath = path.resolve(__dirname, DATA_DIR, filename);
  const content = await fs.readFile(filePath, "utf-8");
  return JSON.parse(content);
}

async function loadData(
  filename: string,
  githubUrl: string
): Promise<unknown> {
  try {
    // Try GitHub first
    return await fetchJSON(githubUrl);
  } catch (error) {
    console.error(`Failed to fetch from GitHub: ${error}. Trying local fallback.`);
    try {
      return await loadLocalJSON(filename);
    } catch (localError) {
      throw new Error(
        `Failed to load ${filename} from both GitHub and local: ${error}, ${localError}`
      );
    }
  }
}

async function ensureDataLoaded(): Promise<void> {
  const now = Date.now();
  if (cache.timestamp && now - cache.timestamp < CACHE_TTL) {
    return; // Cache is still valid
  }

  try {
    cache.profile = (await loadData(
      "profile.json",
      `${GITHUB_RAW_BASE}/profile.json`
    )) as ProfileData;
    cache.resume = (await loadData(
      "resume.json",
      `${GITHUB_RAW_BASE}/resume.json`
    )) as ResumeData;
    cache.blog = (await loadData(
      "blog.json",
      `${GITHUB_RAW_BASE}/blog.json`
    )) as BlogData;
    cache.timestamp = now;
  } catch (error) {
    console.error(`Error loading data: ${error}`);
    throw error;
  }
}

function searchBlogPosts(query: string): BlogPost[] {
  if (!cache.blog) {
    return [];
  }

  const lowerQuery = query.toLowerCase();
  return cache.blog.posts.filter(
    (post) =>
      post.title.toLowerCase().includes(lowerQuery) ||
      post.excerpt.toLowerCase().includes(lowerQuery) ||
      (post.full_content &&
        post.full_content.toLowerCase().includes(lowerQuery))
  );
}

function getBlogPostBySlug(slug: string): BlogPost | null {
  if (!cache.blog) {
    return null;
  }
  return cache.blog.posts.find((post) => post.slug === slug) || null;
}

// Create MCP server
const server = new Server({
  name: "phil-johnston-mcp",
  version: "1.0.0",
});

// Register list tools handler
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "get_profile",
        description: "Get Phil Johnston's profile information including bio, tagline, roles, and contact details",
        inputSchema: {
          type: "object",
          properties: {},
          required: [],
        },
      } as Tool,
      {
        name: "get_resume",
        description: "Get Phil Johnston's resume including career timeline, technical focus, and professional differentiators",
        inputSchema: {
          type: "object",
          properties: {},
          required: [],
        },
      } as Tool,
      {
        name: "search_blog",
        description: "Search blog posts by title, excerpt, or content",
        inputSchema: {
          type: "object",
          properties: {
            query: {
              type: "string",
              description: "Search query to find blog posts",
            },
          },
          required: ["query"],
        },
      } as Tool,
      {
        name: "get_blog_post",
        description: "Get a specific blog post by slug",
        inputSchema: {
          type: "object",
          properties: {
            slug: {
              type: "string",
              description: "The slug of the blog post to retrieve",
            },
          },
          required: ["slug"],
        },
      } as Tool,
    ],
  };
});

// Register call tool handler
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  await ensureDataLoaded();

  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "get_profile": {
        if (!cache.profile) {
          return {
            content: [
              {
                type: "text",
                text: "Error: Profile data not loaded",
              },
            ],
            isError: true,
          };
        }
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(cache.profile, null, 2),
            },
          ],
        };
      }

      case "get_resume": {
        if (!cache.resume) {
          return {
            content: [
              {
                type: "text",
                text: "Error: Resume data not loaded",
              },
            ],
            isError: true,
          };
        }
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(cache.resume, null, 2),
            },
          ],
        };
      }

      case "search_blog": {
        const query = (args as Record<string, unknown>).query as string;
        if (!query) {
          return {
            content: [
              {
                type: "text",
                text: "Error: query parameter is required",
              },
            ],
            isError: true,
          };
        }
        const results = searchBlogPosts(query);
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(results, null, 2),
            },
          ],
        };
      }

      case "get_blog_post": {
        const slug = (args as Record<string, unknown>).slug as string;
        if (!slug) {
          return {
            content: [
              {
                type: "text",
                text: "Error: slug parameter is required",
              },
            ],
            isError: true,
          };
        }
        const post = getBlogPostBySlug(slug);
        if (!post) {
          return {
            content: [
              {
                type: "text",
                text: `Error: Blog post with slug "${slug}" not found`,
              },
            ],
            isError: true,
          };
        }
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(post, null, 2),
            },
          ],
        };
      }

      default:
        return {
          content: [
            {
              type: "text",
              text: `Error: Unknown tool "${name}"`,
            },
          ],
          isError: true,
        };
    }
  } catch (error) {
    return {
      content: [
        {
          type: "text",
          text: `Error executing tool: ${error instanceof Error ? error.message : String(error)}`,
        },
      ],
      isError: true,
    };
  }
});

// Register list resource templates handler
server.setRequestHandler(ListResourceTemplatesRequestSchema, async () => {
  return {
    resourceTemplates: [
      {
        uriTemplate: "phil://blog/{slug}",
        name: "Blog Post",
        description: "Access individual blog posts by slug",
        mimeType: "application/json",
      } as ResourceTemplate,
    ],
  };
});

// Register list resources handler
server.setRequestHandler(ListResourcesRequestSchema, async () => {
  await ensureDataLoaded();

  const resources: Resource[] = [
    {
      uri: "phil://profile",
      name: "Phil's Profile",
      description: "Phil Johnston's bio, tagline, roles, and contact information",
      mimeType: "application/json",
    },
    {
      uri: "phil://resume",
      name: "Phil's Resume",
      description: "Phil Johnston's career timeline, technical focus, and professional differentiators",
      mimeType: "application/json",
    },
    {
      uri: "phil://blog",
      name: "Phil's Blog",
      description: "All blog posts from Phil Johnston's website",
      mimeType: "application/json",
    },
  ];

  // Add individual blog posts
  if (cache.blog) {
    for (const post of cache.blog.posts) {
      resources.push({
        uri: `phil://blog/${post.slug}`,
        name: post.title,
        description: post.excerpt,
        mimeType: "application/json",
      });
    }
  }

  return { resources };
});

// Register read resource handler
server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
  await ensureDataLoaded();

  const { uri } = request.params;

  try {
    if (uri === "phil://profile") {
      if (!cache.profile) {
        throw new Error("Profile data not loaded");
      }
      return {
        contents: [
          {
            uri,
            mimeType: "application/json",
            text: JSON.stringify(cache.profile, null, 2),
          },
        ],
      };
    }

    if (uri === "phil://resume") {
      if (!cache.resume) {
        throw new Error("Resume data not loaded");
      }
      return {
        contents: [
          {
            uri,
            mimeType: "application/json",
            text: JSON.stringify(cache.resume, null, 2),
          },
        ],
      };
    }

    if (uri === "phil://blog") {
      if (!cache.blog) {
        throw new Error("Blog data not loaded");
      }
      return {
        contents: [
          {
            uri,
            mimeType: "application/json",
            text: JSON.stringify(cache.blog, null, 2),
          },
        ],
      };
    }

    // Handle individual blog posts: phil://blog/{slug}
    const blogSlugMatch = uri.match(/^phil:\/\/blog\/(.+)$/);
    if (blogSlugMatch) {
      const slug = blogSlugMatch[1];
      const post = getBlogPostBySlug(slug);
      if (!post) {
        throw new Error(`Blog post with slug "${slug}" not found`);
      }
      return {
        contents: [
          {
            uri,
            mimeType: "application/json",
            text: JSON.stringify(post, null, 2),
          },
        ],
      };
    }

    throw new Error(`Unknown resource: ${uri}`);
  } catch (error) {
    throw new Error(
      `Error reading resource: ${error instanceof Error ? error.message : String(error)}`
    );
  }
});

// Start the server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("phil-johnston-mcp server started");
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
