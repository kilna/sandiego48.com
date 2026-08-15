---
title: "{{ replace .Name "-" " " | title }}"
layout: news
type: news
summary: >
  Brief announcement copy.
date: {{ .Date }}
publishDate: {{ .Date }}
draft: false
params:
  kind: announcement
  kind_label: Announcement
  featured: false
  button:
    text: "Learn More"
    url: "/"
    icon: "info"
    emoji: "➡️"
---

