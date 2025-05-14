#!/usr/bin/env bash

rm -rf public/
hugo server --forceSyncStatic --cleanDestinationDir --disableFastRender

