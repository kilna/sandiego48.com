SHELL := /usr/bin/env bash

.PHONY: build build-clean server server-slow

server: build
	hugo server

server-slow: build-clean
	hugo server --disableFastRender

build:
	hugo

build-clean:
	hugo --forceSyncStatic --cleanDestinationDir

