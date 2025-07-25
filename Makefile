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

.PHONY: build build-clean server server-slow server-verbose open-wait

build:
	hugo

build-clean:
	rm -rf public
	hugo --forceSyncStatic --cleanDestinationDir

server: build kill-server
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