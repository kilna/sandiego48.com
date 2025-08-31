---
title: "{{ replace .Name "-" " " | title }}"
date: {{ .Date }}
draft: false
params:
  year: {{ now.Year }}
  team: ""
  logline: ""
  synopsis: ""
  order: 999
  genre: ""
  runtime: ""
  # Optional image fields
  # poster: "poster.jpg"
  # still: "still.jpg"
screening_groups:
  - ""  # e.g., "group-a", "group-b", "group-c", "group-d"
screening_events:
  - ""  # e.g., "2025-09-09-group-a-premieres", "2025-09-28-best-of-san-diego"
---

Film description goes here.
