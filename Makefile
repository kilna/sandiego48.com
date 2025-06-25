SHELL := /usr/bin/env bash

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

.PHONY: build build-clean server server-slow server-verbose

server: build
	hugo server

server-slow: build-clean
	hugo server --disableFastRender

server-verbose: build-clean
	hugo server --disableFastRender --logLevel debug --printPathWarnings --printUnusedTemplates

build:
	hugo

build-clean:
	rm -rf public
	hugo --forceSyncStatic --cleanDestinationDir
