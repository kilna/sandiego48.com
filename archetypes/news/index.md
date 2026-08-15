---
title: "{{ replace .Name "-" " " | title }}"
layout: news
type: news
summary: >
  Short summary for the news item.
date: {{ .Date }}
publishDate: {{ .Date }}
draft: false
params:
  kind: article
  kind_label: Article
  featured: false
  source_name:
  source_url:
  external_url:
---

Write the article body here.
