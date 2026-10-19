---
layout: page
lang: en
ref: tags
title: Tags
permalink: /tags/
description: "Browse posts by the blog's 4 topics: backend production, AI agents, Linux tooling and everyday life."
---

Posts are grouped under the blog's 4 main topics. Pick a topic to see its posts.

{% assign pillars = "backend-production,ai-agent,linux-tooling,doi-song" | split: "," %}
<ul class="tag-index">
{% for pillar in pillars %}
{% assign pillar_posts = site.tags[pillar] | sort: "date" | reverse %}
{%- assign pillar_entry = site.data.tag_labels[pillar] -%}
{%- assign pillar_label = pillar_entry.en | default: pillar -%}
{%- assign pillar_slug = pillar_entry.slug_en | default: pillar -%}
{%- assign pillar_desc = pillar_entry.description_en | default: "" -%}
  <li>
    <a class="tag-chip" rel="tag" href="{{ '/tags/' | append: pillar_slug | append: '/' | relative_url }}">{{ pillar_label | escape }}</a>
    <span class="tag-index__count">{{ pillar_posts | size }} posts</span>
    {%- if pillar_desc != "" -%}
    <span class="tag-index__desc">{{ pillar_desc | escape }}</span>
    {%- endif -%}
  </li>
{% endfor %}
</ul>
