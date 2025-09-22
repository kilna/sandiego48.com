SHELL := /usr/bin/env bash

# Set HUGO_BASEURL based on where we are building...
ifeq ($(CF_PAGES),true)
ifeq ($(CF_PAGES_BRANCH),main)
export HUGO_BASEURL=https://sandiego48.com
else
export HUGO_BASEURL=https://$(CF_PAGES_BRANCH).sandiego48.com
endif
else
export HUGO_BASEURL=http://localhost:$(SERVER_PORT)
-include .env # This is used for local development...
endif

.PHONY: build build-clean server server-cdn server-slow server-verbose open-wait copy-images cdn cdn-force cdn-download gallery-thumbs gallery-update-counts gallery-audit tool-plugins setup-dev-cdn cleanup-dev-cdn push deploy preview dash help

copy-images: install-tools
	./scripts/copy-images.sh

build: copy-images cleanup-dev-cdn
	hugo

build-clean: copy-images cleanup-dev-cdn
	rm -rf public
	hugo --forceSyncStatic --cleanDestinationDir

initialize-cloudflare:
	cat .tool-versions.cloudflare | \
	  wrangler pages secret put ASDF_DEFAULT_TOOL_VERSIONS_FILENAME \
	    --project-name $$CLOUDFLARE_PAGES_PROJECT

install-tools:
	@echo "CF_PAGES is: $(CF_PAGES)"
	@echo "Running install-tools..."
ifeq ($(CF_PAGES),true)
	./scripts/tool-plugins.sh
	cat .tool-versions >> .tool-versions.cloudflare
	asdf install
endif

setup-dev-cdn:
	@if [ ! -L static/cdn ]; then \
		ln -sf ../cdn static/cdn; \
	fi

cleanup-dev-cdn:
	@if [ -L static/cdn ]; then \
		rm static/cdn; \
	fi

server: copy-images setup-dev-cdn kill-server
	hugo server --disableFastRender --port $$SERVER_PORT | ./scripts/open-server.sh

server-cdn: copy-images setup-dev-cdn kill-server
	HUGO_FORCE_PRODUCTION_CDN=true hugo server --disableFastRender --port $$SERVER_PORT | ./scripts/open-server.sh

server-clean: build-clean kill-server
	hugo server --disableFastRender --port $$SERVER_PORT | ./scripts/open-server.sh

server-slow: copy-images setup-dev-cdn kill-server
	hugo server --disableFastRender --port $$SERVER_PORT | ./scripts/open-server.sh

server-verbose: copy-images setup-dev-cdn kill-server
	hugo server --disableFastRender --port $$SERVER_PORT --logLevel debug --printPathWarnings --printUnusedTemplates | ./scripts/open-server.sh

kill-server:
	lsof -ti:$$SERVER_PORT | xargs kill -9 2>/dev/null || true

open:
	open http://localhost:$$SERVER_PORT

icons: tool-plugins
	./scripts/icons.sh

cdn: gallery-thumbs gallery-update-counts cdn-upload

cdn-force: gallery-thumbs-force gallery-update-counts cdn-upload

cdn-upload: gallery-audit
	export $$(cat .env | xargs) && \
	  aws s3 sync cdn/ s3://sandiego48-com/ --delete \
		  --exclude ".*"

cdn-download:
	export $$(cat .env | xargs) && \
	   aws s3 sync s3://sandiego48-com/ cdn/

gallery-thumbs: tool-plugins
	./scripts/gallery-thumbs.sh

gallery-thumbs-force: tool-plugins
	./scripts/gallery-thumbs.sh --force

gallery-update-counts: tool-plugins
	./scripts/gallery-update-counts.sh

gallery-audit: tool-plugins
	./scripts/gallery-audit.sh

preview: build-clean
	script -q /dev/null \
	  bash -c "wrangler pages deploy ./public --commit-dirty=true" \
		| ./scripts/open-preview.sh

dash:
	@echo "Opening Cloudflare Pages dashboard at $$CLOUDFLARE_PAGES_DASHBOARD_URL"
	open $$CLOUDFLARE_PAGES_DASHBOARD_URL

help:
	@echo "Available targets:"
	@echo "  build         - Build the site"
	@echo "  build-clean   - Clean build with force sync"
	@echo "  server        - Start development server"
	@echo "  server-cdn    - Start server with production CDN"
	@echo "  server-clean  - Start server with clean build"
	@echo "  server-slow   - Start server with fast render disabled"
	@echo "  server-verbose- Start server with debug logging"
	@echo "  deploy        - Build and deploy via git (requires clean working copy)"
	@echo "  preview       - Deploy to Cloudflare Pages preview and open in browser"
	@echo "  push          - Commit and push to origin"
	@echo "  cdn           - Upload to CDN (includes gallery processing)"
	@echo "  cdn-force     - Force CDN upload with gallery regeneration"
	@echo "  cdn-download  - Download from CDN"
	@echo "  gallery-thumbs- Generate gallery thumbnails"
	@echo "  gallery-audit - Audit gallery images"
	@echo "  icons         - Download/refresh SVG icons from icons.yaml"
	@echo "  help          - Show this help message"
