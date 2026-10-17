---
layout: page
title: Tags
permalink: /tags/
---

Bài viết được nhóm theo 4 chủ đề chính của blog. Chọn một chủ đề để xem các bài
viết cùng tag.

{% assign pillars = "backend-production,ai-agent,linux-tooling,doi-song" | split: "," %}
<ul class="tag-index">
{% for pillar in pillars %}
{% assign pillar_posts = site.tags[pillar] | sort: "date" | reverse %}
  <li>
    <a class="tag-chip" rel="tag" href="{{ '/tags/' | append: pillar | append: '/' | relative_url }}">{{ pillar }}</a>
    <span class="tag-index__count">{{ pillar_posts | size }} bài</span>
  </li>
{% endfor %}
</ul>
