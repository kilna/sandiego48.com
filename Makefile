SHELL := /usr/bin/env bash

.PHONY: build build-clean server server-slow

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
