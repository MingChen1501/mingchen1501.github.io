---
layout: page
title: Tags
permalink: /tags/
---

Bài viết được nhóm theo 4 chủ đề chính của blog: `backend-production`, `ai-agent`, `linux-tooling`, `doi-song`.

{% assign pillars = "backend-production,ai-agent,linux-tooling,doi-song" | split: "," %}
{% for pillar in pillars %}
{% assign pillar_posts = site.tags[pillar] | sort: "date" | reverse %}
## {{ pillar }} ({{ pillar_posts | size }} bài)

<ul>
{% for post in pillar_posts %}
  <li>
    <a href="{{ post.url | relative_url }}">{{ post.title | escape }}</a>
    — {{ post.date | date: "%d-%m-%Y" }}
  </li>
{% endfor %}
</ul>
{% endfor %}
