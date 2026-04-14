# react-seo-bridge

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)
![Offline](https://img.shields.io/badge/runtime-offline-0F766E)
![Parser](https://img.shields.io/badge/parser-tree--sitter-111827)
![CLI](https://img.shields.io/badge/cli-typer-2563EB)
![Mode](https://img.shields.io/badge/mode-C%20Audit%20Only-F59E0B)

Static SEO audits for React single-page apps.

`react-seo-bridge` helps React teams understand why a client-rendered app is hard for Google, Bing, social crawlers, and AI crawlers to index before committing to a Next.js migration or a prerendering layer.

It runs fully offline, parses JavaScript and TypeScript with `tree-sitter`, and generates both machine-readable and human-readable reports.

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
- Writes `rsb-audit.json` and `rsb-audit.md`
- Exits non-zero when critical issues are found, which makes it CI-friendly

## Best Fit

| Good fit | Not the goal |
|---|---|
| React SPAs that need a crawlability reality check | Runtime browser automation or Lighthouse replacement |
| Teams comparing CSR vs SSR/SSG tradeoffs | Server-side rendering framework generation |
| Offline analysis in CI or local dev | Live Google Search Console data |

## Quick Start

### Install

```bash
pip install -e ".[dev]"
```

### Run an audit

```bash
rsb audit ./path/to/react-app
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
| `rsb version` | Print the installed version |

### `rsb audit` options

| Option | Description |
|---|---|
| `--output`, `-o` | Write reports to a custom directory |
| `--json-only` | Skip Markdown generation |
| `--no-output` | Print terminal summary only |

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Audit completed with no critical findings |
| `1` | Invalid project path or unsupported project |
| `2` | Audit completed and critical SEO issues were found |

## Example Output

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
| [`rsb/reporters/`](./rsb/reporters) | JSON and Markdown report generation |
| [`tests/`](./tests) | Fixtures and pytest coverage |

## Development

### Local workflow

```bash
python3 -m pip install -e ".[dev]"
pytest tests/ -v --cov=rsb
python3 -m rsb audit tests/fixtures/cra_basic --no-output
```

### Tech stack

- Python 3.11+
- Typer for the CLI
- Rich for terminal output
- Pydantic v2 for schemas
- Jinja2 for Markdown report rendering
- `tree-sitter 0.25.x` language wheels for parsing

## Project Status

`react-seo-bridge` is currently focused on **Mode C: Audit Only**.

Current state:

- offline static analysis is implemented
- JSON and Markdown audit reports are implemented
- fixture-based tests are implemented

Near-term improvements:

- richer route-to-component resolution for more routing styles
- broader metadata pattern coverage
- expanded fixture matrix for larger app shapes

## License

MIT
