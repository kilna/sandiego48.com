# Cloudflare Pages Deployment Guide

## Redirects Configuration

This site uses a `static/_redirects` file that is compatible with Cloudflare Pages. The redirects will automatically work when you deploy to Cloudflare Pages.

## How It Works

1. **Build Process**: When Hugo builds the site, the `static/_redirects` file gets copied to the `public/` directory
2. **Deployment**: Cloudflare Pages reads the `_redirects` file from the root of your built site
3. **Automatic Redirects**: Old URLs are automatically redirected to new ones

## Current Redirects

The following redirects are configured:

| Old URL | New URL | Status |
|----------|---------|---------|
| `/films/the-2880-minute-movie-makers-i-plead-the-fifth` | `/films/2880-minute-movie-makers-i-plead-the-fifth` | 301 |
| `/films/the-filmigos-fire-in-my-heart` | `/films/filmigos-fire-in-my-heart` | 301 |
| `/films/the-k-concern-tango-of-the-unseen` | `/films/k-concern-tango-of-the-unseen` | 301 |
| `/films/the-super-pas-dystopian-cowboys` | `/films/super-pas-dystopian-cowboys` | 301 |
| `/films/the-underdogs-crimson-hour` | `/films/underdogs-crimson-hour` | 301 |

## Deployment Steps

1. **Build the site**: `hugo --buildDrafts --buildFuture --minify`
2. **Deploy to Cloudflare Pages**: The `public/` directory contains everything needed
3. **Verify redirects**: Test old URLs to ensure they redirect properly

## Testing Redirects

After deployment, you can test the redirects by visiting the old URLs. They should automatically redirect to the new URLs with a 301 status code.

## Troubleshooting

If redirects don't work:

1. **Check file location**: Ensure `_redirects` is in the root of your built site (`public/` directory)
2. **File format**: Ensure the format is `from_path to_path status_code` (space-separated)
3. **Cloudflare Pages settings**: Ensure your Pages project is configured to use the `public/` directory as the build output

## Additional Notes

- The `_redirects` file is automatically copied to `public/` during Hugo build
- Cloudflare Pages processes this file automatically
- 301 redirects are permanent and good for SEO
- Old URLs will continue to work indefinitely
