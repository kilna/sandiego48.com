# Environment Configuration

This document describes the environment variables and configuration needed for local development.

## Required Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# Development server port (default: 1313)
SERVER_PORT=1313

# Cloudflare Pages configuration (automatically set from wrangler.toml)
# CLOUDFLARE_PAGES_PROJECT=sandiego48-com
# CLOUDFLARE_PAGES_DASHBOARD_URL=https://dash.cloudflare.com/pages/view/sandiego48-com

# AWS credentials for CDN uploads (if using CDN features)
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_DEFAULT_REGION=us-east-1

# Optional: Override Hugo base URL for local development
HUGO_BASEURL=http://localhost:1313
```

## Setup Instructions

1. **Copy environment template:**
   ```bash
   cp ENVIRONMENT.md .env
   # Edit .env with your actual values
   ```

2. **Install direnv (recommended):**
   ```bash
   # macOS
   brew install direnv
   
   # Add to your shell profile (~/.bashrc, ~/.zshrc, etc.)
   eval "$(direnv hook bash)"  # or zsh
   ```

3. **Allow direnv in this directory:**
   ```bash
   direnv allow
   ```

## Development Tools

This project uses asdf for tool version management. The following tools are managed:

- **Hugo**: Static site generator (version defined in `.tool-versions.cloudflare`)
- **yq**: YAML processor (version defined in `.tool-plugins`)

## Cloudflare Pages Configuration

The project includes a `wrangler.toml` file for Cloudflare Pages deployment configuration. This file defines:

- Project name: `sandiego48-com`
- Account ID: `046e8f301fab8b218d3f51110cc7034f`
- Build output directory: `public/`

Production deploys are GitHub Actions on push to `main`: Hugo builds the site, then Wrangler uploads `public/` to Pages. Do not use a Cloudflare deploy hook for this; the old hook URL is gone and the Action now fails if credentials are missing.

Required GitHub Actions secret:

- `CLOUDFLARE_API_TOKEN` — Cloudflare API token with **Account / Cloudflare Pages / Edit** (Workers template is fine)

Create a token at https://dash.cloudflare.com/046e8f301fab8b218d3f51110cc7034f/api-tokens and add it under the repo **Settings > Secrets and variables > Actions**. Local `wrangler` / `make preview` also need a valid token in the environment (`CLOUDFLARE_API_TOKEN`) or `wrangler login`.

The `.envrc` file reads the project name from `wrangler.toml` for local dashboard links.

## Makefile Targets

The Makefile provides several development targets:

- `make server` - Start development server
- `make build` - Build the site
- `make help` - Show all available targets
- `make deploy` - Deploy to Cloudflare Pages
- `make preview` - Deploy preview to Cloudflare Pages

See `make help` for a complete list of available targets.
