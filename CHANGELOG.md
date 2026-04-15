# Changelog

All notable changes to `react-seo-bridge` are documented in this file.

## 0.1.0 - 2026-04-15

Initial public release of the bridge workflow for React SPA SEO.

### Added

- Mode C audit CLI with JSON and Markdown reporting
- static analysis for routes, metadata patterns, bundle signals, and CWV heuristics
- Mode A inject workflow for Vercel, Cloudflare, nginx, and Express bridge generation
- FastAPI + Playwright prerender server with disk-backed snapshot cache
- maintained bot user-agent matcher module including major 2025 AI crawlers
- sitemap and robots generation from discovered audit routes
- Mode B scaffold workflow for building an LLM-ready Next.js App Router migration bundle
- component classification for client versus server component boundaries
- token-aware bundle chunking for large projects
- fixture-backed test coverage for audit, inject, prerender cache, and scaffold flows

### Positioning

- Dynamic rendering is presented as a bridge, not a permanent architecture target
- Next.js App Router migration is supported through context generation rather than direct code rewriting
- The repo is aimed at React teams that need crawlability clarity before a broader framework decision

### Verification

- full pytest suite passing locally
- CLI smoke checks for `audit`, `inject`, and `scaffold`
