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

- **Hugo**: Static site generator (version defined in `.tool-versions.full`)
- **yq**: YAML processor (version defined in `.tool-plugins`)

## Cloudflare Pages Configuration

The project includes a `wrangler.toml` file for Cloudflare Pages deployment configuration. This file defines:

- Project name: `sandiego48-com`
- Build output directory: `public/`
- Environment configurations for production and preview

The `.envrc` file automatically reads the project name from `wrangler.toml` to set the appropriate environment variables.

## Makefile Targets

The Makefile provides several development targets:

- `make server` - Start development server
- `make build` - Build the site
- `make help` - Show all available targets
- `make deploy` - Deploy to Cloudflare Pages
- `make preview` - Deploy preview to Cloudflare Pages

See `make help` for a complete list of available targets.
