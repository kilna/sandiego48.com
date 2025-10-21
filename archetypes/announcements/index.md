---
title: "{{ replace .Name "-" " " | title }}"
layout: announcements
type: announcements
summary: >
  Body text for the announcement. Keep it concise and avoid links.
  This will appear on the home page, citymessage, and announcement page.
date: {{ .Date }}
publishDate: {{ .Date }}
draft: false
params:
  # Set featured: true to show on home page and citymessage
  featured: true
  # Optional image (displayed centered above the title)
  image: announcement.png
  # Action button
  button:
    text: "Learn More"
    url: "/"
    icon: "info"
    emoji: "➡️"
---

