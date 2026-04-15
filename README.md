# react-seo-bridge

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)
![Offline](https://img.shields.io/badge/runtime-offline-0F766E)
![Parser](https://img.shields.io/badge/parser-tree--sitter-111827)
![CLI](https://img.shields.io/badge/cli-typer-2563EB)
![Modes](https://img.shields.io/badge/modes-A%20Inject%20%7C%20B%20Scaffold%20%7C%20C%20Audit-16A34A)

SEO tooling for React single-page apps that need a bridge from CSR to something crawler-friendly.

`react-seo-bridge` helps React teams answer three practical questions:

- What is broken for crawlers right now?
- Can we deploy a temporary bot-safe prerender bridge without rewriting the app?
- If we do migrate to Next.js, how do we hand an LLM the right context to produce a usable first draft?

It runs with Python, parses JavaScript and TypeScript with `tree-sitter`, and now ships three connected workflows:

- `rsb audit` for offline SEO analysis
- `rsb inject` for dynamic rendering bridge config generation
- `rsb scaffold` for building an LLM-ready Next.js migration bundle

## Why This Exists

Modern React apps often look correct in the browser while still shipping a thin HTML shell to crawlers.

This project focuses on the questions teams usually need answered early:

- Is this app still pure CSR?
- Which routes are dynamic or lazy-loaded?
- Are title, description, Open Graph, and canonical tags being set at all?
- Are those tags only being injected client-side?
- Are there obvious crawlability or Core Web Vitals risks?

## Highlights

- Audits CRA, Vite, and custom Webpack React apps without Node.js
- Detects React Router v5 and v6 route definitions
- Flags dynamic routes that cannot be auto-sitemapped safely
- Detects Helmet, Helmet Async, direct `document.title`, Open Graph, and canonical patterns
- Estimates SEO and performance risk from static analysis only
- Generates Vercel, Cloudflare, nginx, and Express bot-routing bridge files
- Ships a FastAPI + Playwright prerender server with disk cache
- Builds a token-aware Next.js App Router migration bundle for Claude or GPT-style models
- Writes `rsb-audit.json`, `rsb-audit.md`, sitemap, robots, and scaffold bundle artifacts
- Exits non-zero when critical audit issues are found, which makes Mode C CI-friendly

## Best Fit

| Good fit | Not the goal |
|---|---|
| React SPAs that need a crawlability reality check | Runtime browser automation or Lighthouse replacement |
| Teams comparing CSR vs SSR/SSG tradeoffs | Server-side rendering framework generation |
| Offline analysis in CI or local dev | Live Google Search Console data |

## Modes

| Mode | Command | Purpose |
|---|---|---|
| Mode C: Audit | `rsb audit ./my-react-app` | Inspect crawlability, metadata, routing, and CWV risks |
| Mode A: Inject | `rsb inject ./my-react-app --target vercel ...` | Generate edge or server config that routes bots to a prerender service |
| Mode B: Scaffold | `rsb scaffold ./my-react-app` | Produce an LLM-ready migration bundle for Next.js App Router |

## Quick Start

### Install

```bash
pip install -e ".[dev]"
playwright install chromium
```

### Audit a React app

```bash
rsb audit ./path/to/react-app
```

### Generate dynamic rendering bridge files

```bash
rsb inject ./path/to/react-app \
  --target vercel \
  --prerender-url http://localhost:3000 \
  --base-url https://mysite.com
```

### Build an LLM migration bundle

```bash
rsb scaffold ./path/to/react-app
```

### Run tests

```bash
pytest tests/ -v --cov=rsb
```

## CLI

### Commands

| Command | What it does |
|---|---|
| `rsb audit <project_path>` | Run the Mode C static audit |
| `rsb inject <project_path>` | Generate Mode A dynamic rendering bridge files |
| `rsb serve` | Start the Mode A prerender server |
| `rsb scaffold <project_path>` | Build the Mode B migration context bundle |
| `rsb version` | Print the installed version |

### `rsb audit` options

| Option | Description |
|---|---|
| `--output`, `-o` | Write reports to a custom directory |
| `--json-only` | Skip Markdown generation |
| `--no-output` | Print terminal summary only |

### `rsb inject` options

| Option | Description |
|---|---|
| `--target`, `-t` | Deploy target: `vercel`, `cloudflare`, `nginx`, or `express` |
| `--prerender-url`, `-p` | Public URL of your prerender server |
| `--base-url`, `-b` | Production base URL used for sitemap and robots |
| `--output`, `-o` | Custom output directory for generated files |

### `rsb scaffold` options

| Option | Description |
|---|---|
| `--output`, `-o` | Custom output directory for scaffold bundle files |
| `--target`, `-t` | Migration target. Current value: `nextjs14` |
| `--no-audit` | Reuse an existing `rsb-audit.json` instead of running audit again |

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Audit completed with no critical findings |
| `1` | Invalid project path or unsupported project |
| `2` | Audit completed and critical SEO issues were found |

## Example Output

### `rsb audit`

```text
+------------------------------+
| react-seo-bridge - SEO Audit |
+---------- Mode C: Static Analysis ----------+

+------------ SEO Score ------------+
| 34/100                            |
+-----------------------------------+

Issues Found
CRITICAL  Client-Side Rendering detected - content invisible to crawlers on Wave 1  rendering
HIGH      Metadata managed via react-helmet on a CSR app - invisible to most bots  metadata
HIGH      1 dynamic route(s) cannot be auto-sitemapped                              routing
HIGH      No sitemap.xml found                                                      crawlability
MEDIUM    No canonical link tags detected                                           metadata
MEDIUM    Cumulative Layout Shift (CLS) risk: 1 image(s) without dimensions         cwv
LOW       No robots.txt found                                                       crawlability

Routes: 3 total (1 dynamic, 1 lazy)
Framework: cra | Rendering: csr

JSON report: /path/to/react-app/rsb-output/rsb-audit.json
Markdown report: /path/to/react-app/rsb-output/rsb-audit.md
```

### `rsb inject`

```text
react-seo-bridge - Inject Mode A
Target: vercel

Generated 4 file(s) in ./my-react-app/rsb-output/inject:
  - middleware.js
  - vercel.json
  - sitemap.xml
  - robots.txt

Next steps:
  1. Start the prerender server with rsb serve --port 3000
  2. Set RSB_PRERENDER_URL in your deploy platform
  3. Copy generated public files into your app
```

### `rsb scaffold`

```text
react-seo-bridge - Scaffold Mode B

Migration bundle ready!

  Files analysed:   42
  Routes found:     18
  Bundle chunks:    1
  Estimated tokens: 54,000

Bundle location:
  ./my-react-app/rsb-output/scaffold/rsb-scaffold-bundle.md
```

## Generated Reports

### `rsb-audit.json`

Structured output for automation, CI checks, dashboards, and downstream tooling.

### `rsb-audit.md`

A GitHub-friendly audit summary with:

- SEO score
- issue counts by severity
- detailed findings and recommendations
- discovered routes
- Core Web Vitals risk notes
- bundle analysis summary

### Inject output

Depending on target, `rsb inject` generates:

- `middleware.js` and `vercel.json`
- or `worker.js` and `wrangler.toml`
- or `rsb-nginx-snippet.conf`
- or `rsb-express-middleware.js`
- plus `sitemap.xml` and `robots.txt`

### Scaffold output

`rsb scaffold` writes:

- `rsb-output/scaffold/rsb-scaffold-bundle.md`
- or `rsb-scaffold-bundle-part1.md`, `part2.md`, and so on for larger projects

Paste that bundle into Claude or another large-context model to get a structured Next.js App Router migration draft.

## How It Works

1. [`project_scanner.py`](./rsb/analyser/project_scanner.py) validates the target project and discovers relevant source files.
2. [`ast_parser.py`](./rsb/analyser/ast_parser.py) parses JS, JSX, TS, and TSX with `tree-sitter`.
3. [`route_mapper.py`](./rsb/analyser/route_mapper.py) maps React Router routes, lazy-loaded components, and fetch patterns.
4. [`metadata_detector.py`](./rsb/analyser/metadata_detector.py) detects title, description, Open Graph, canonical, and Helmet usage.
5. [`bundle_analyser.py`](./rsb/analyser/bundle_analyser.py) infers framework, rendering mode, and SEO-relevant dependencies.
6. [`cwv_estimator.py`](./rsb/analyser/cwv_estimator.py) estimates static Core Web Vitals risks.
7. [`audit_report.py`](./rsb/reporters/audit_report.py) assembles issues, computes the SEO score, and writes JSON and Markdown reports.

## Repository Layout

| Path | Purpose |
|---|---|
| [`rsb/cli.py`](./rsb/cli.py) | Typer CLI entrypoint |
| [`rsb/schemas.py`](./rsb/schemas.py) | Shared Pydantic v2 models |
| [`rsb/analyser/`](./rsb/analyser) | Static analysis pipeline |
| [`rsb/prerender/`](./rsb/prerender) | FastAPI + Playwright prerender service |
| [`rsb/generators/`](./rsb/generators) | Deploy-target config generators |
| [`rsb/reporters/`](./rsb/reporters) | JSON and Markdown report generation |
| [`rsb/scaffold/`](./rsb/scaffold) | LLM migration bundle generation |
| [`templates/`](./templates) | Root Jinja templates for Mode A output files |
| [`tests/`](./tests) | Fixtures and pytest coverage |

## Development

### Local workflow

```bash
python3 -m pip install -e ".[dev]"
playwright install chromium
pytest tests/ -v --cov=rsb
python3 -m rsb audit tests/fixtures/cra_basic --no-output
python3 -m rsb inject tests/fixtures/cra_basic --target vercel --prerender-url http://localhost:3000 --base-url https://mysite.com
python3 -m rsb scaffold tests/fixtures/cra_basic
```

### Tech stack

- Python 3.11+
- Typer for the CLI
- Rich for terminal output
- Pydantic v2 for schemas
- Jinja2 for Markdown report rendering
- `tree-sitter 0.25.x` language wheels for parsing
- FastAPI and Uvicorn for the prerender server
- Playwright Chromium for HTML snapshot rendering

## Project Status

`react-seo-bridge` now has an end-to-end early bridge story:

- Mode C is implemented for offline SEO audit
- Mode A is implemented for dynamic rendering bridge generation
- Mode B is implemented for LLM-assisted migration scaffolding

Near-term improvements:

- richer route-to-component resolution for more routing styles
- broader metadata pattern coverage
- a maintained public crawler registry workflow
- more real-project fixtures and sample outputs

## Roadmap

| Mode | Status | Purpose |
|---|---|---|
| Mode C: Audit Only | Available now | Audit a React app offline and explain indexing risk before any migration work starts |
| Mode A: Dynamic Rendering Bridge | Available now | Generate edge and server bridge files plus a prerender service for bots |
| Mode B: Migration Scaffolder | Available now | Produce an LLM-ready Next.js migration bundle from the audited codebase |
| Future modes | Demand-driven | Expand based on real developer pull and operating pain points |

## Honest Positioning On Dynamic Rendering

Mode A is framed honestly: a bridge, not the destination.

Google Search Central's current guidance says dynamic rendering is a "workaround" and "not a recommended solution" because it adds operational complexity and resource overhead. The current Google documentation also recommends server-side rendering, static rendering, or hydration instead. The latest official Google page for this guidance was updated on **December 10, 2025**.

That said, dynamic rendering is not automatically cloaking. Google explicitly distinguishes valid dynamic rendering from cloaking as long as crawlers and users are served materially similar content.

References:

- [Dynamic rendering as a workaround - Google Search Central](https://developers.google.com/search/docs/crawling-indexing/javascript/dynamic-rendering)
- [Understand JavaScript SEO basics - Google Search Central](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics)

## Why Tree-sitter

`react-seo-bridge` uses `tree-sitter` instead of older JavaScript parsers because this project needs modern React syntax coverage without a Node.js runtime.

Why this matters:

- JSX, TSX, TypeScript, optional chaining, and newer ECMAScript syntax need to parse reliably
- static analysis should run offline in pure Python environments
- React teams should not need Babel or a local Node toolchain just to audit a codebase

For this use case, `tree-sitter-javascript` and `tree-sitter-typescript` are a better fit than older JS-only parsers.

## A Potentially Novel Open-source Contribution

One roadmap idea that could make this project genuinely useful beyond its own CLI is a maintained crawler registry:

- a versioned `bot-agents.json`
- released with the package
- updated publicly in GitHub pull requests
- usable by any rendering proxy, audit tool, or middleware that needs bot user-agent coverage

The problem today is simple: most teams maintain bot user-agent allowlists manually, and those lists go stale fast.

If this registry would be useful to you, that is strong signal that this project should grow beyond the current feature set.

## Interested In The Roadmap?

If you would use any of the following, please open an issue and say so:

- Mode A dynamic rendering bridge
- a maintained `bot-agents.json` crawler registry
- deeper migration planning beyond the current scaffold output

Suggested issue titles:

- `[interest] Mode A dynamic rendering bridge`
- `[interest] bot-agents.json registry`
- `[interest] migration planning workflow`

Or use the GitHub issue template included in this repo for roadmap-interest signals.

## First Release

The first public cut of this repo is intended to cover the full bridge workflow:

- inspect a React SPA with `rsb audit`
- generate crawler-routing bridge assets with `rsb inject`
- run a local prerender service with `rsb serve`
- produce a migration-ready context bundle with `rsb scaffold`

See [CHANGELOG.md](./CHANGELOG.md) for the release notes that map to the initial tagged version.

## License

MIT
