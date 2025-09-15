SHELL := /usr/bin/env bash
#PARAMS := --disableFastRender --logLevel debug --printPathWarnings --printUnusedTemplates
PARAMS := --disableFastRender

# Set HUGO_BASEURL based on where we are building...
ifeq ($(CF_PAGES),true)
ifeq ($(CF_PAGES_BRANCH),main)
export HUGO_BASEURL=https://sandiego48.com
else
export HUGO_BASEURL=https://$(CF_PAGES_BRANCH).sandiego48.com
endif
else
-include .env # This is used for local development...
endif

.PHONY: build build-clean server server-slow server-verbose open-wait copy-images cdn cdn-force cdn-download cdn-thumbnails update-cdn-counts

copy-images:
	./scripts/copy-images.sh

build: copy-images
	hugo

build-clean:
	rm -rf public
	hugo --forceSyncStatic --cleanDestinationDir

server: copy-images kill-server
	hugo server $(PARAMS) | tee >($(MAKE) open-wait) 2>&1

server-clean: build-clean kill-server
	hugo server $(PARAMS) | tee >($(MAKE) open-wait) 2>&1

kill-server:
	pkill -f "hugo server" || true

open-wait:
	awk '/at http/ {gsub(/.* at | \(.*/, ""); system("open " $$0); fflush(); while((getline) > 0) print}'

open:
	open http://localhost:1313

icons:
	./scripts/icons.sh

migrate-directories:
	python3 scripts/migrate-directories.py content/films

cleanup-redirects:
	rm -rf layouts/films/the-*
	@echo "Redirect files cleaned up"

move-images:
	python3 scripts/move-images.py

cdn: cdn-thumbnails update-cdn-counts cdn-upload

cdn-force: cdn-thumbnails-force update-cdn-counts cdn-upload

cdn-upload:
	export $$(cat .env | xargs) && \
	  aws s3 sync cdn/ s3://sandiego48-com/ --delete \
		  --exclude ".*"

cdn-download:
	export $$(cat .env | xargs) && \
	   aws s3 sync s3://sandiego48-com/ cdn/

cdn-thumbnails:
	./scripts/cdn-thumbnails.sh

cdn-thumbnails-force:
	./scripts/cdn-thumbnails.sh --force

update-cdn-counts:
	./scripts/update-cdn-counts.sh
