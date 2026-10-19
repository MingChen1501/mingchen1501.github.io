---
layout: page
lang: vi
ref: tags
title: Chủ đề
permalink: /vi/tags/
description: "Xem bài viết theo 4 chủ đề của blog: backend production, AI agent, Linux tooling và đời sống."
---

Bài viết được nhóm theo 4 chủ đề chính của blog. Chọn một chủ đề để xem các bài
viết cùng tag.

{% assign pillars = "backend-production,ai-agent,linux-tooling,doi-song" | split: "," %}
{%- comment -%}
  Nil-safe like the tag layout: the collection may be undefined in the
  upstream `_config_theme-dev.yml` CI build.
{%- endcomment -%}
{%- assign vi_tags_source = site.vi_posts -%}
{%- if vi_tags_source == nil -%}
  {%- assign vi_tags_source = "" | split: "" -%}
{%- endif -%}
<ul class="tag-index">
{% for pillar in pillars %}
{% assign pillar_posts = vi_tags_source | where_exp: "post", "post.tags contains pillar" | sort: "date" | reverse %}
{%- assign pillar_entry = site.data.tag_labels[pillar] -%}
{%- assign pillar_label = pillar_entry.vi | default: pillar -%}
{%- assign pillar_slug = pillar_entry.slug_vi | default: pillar -%}
  <li>
    <a class="tag-chip" rel="tag" href="{{ '/vi/tags/' | append: pillar_slug | append: '/' | relative_url }}">{{ pillar_label | escape }}</a>
    <span class="tag-index__count">{{ pillar_posts | size }} bài</span>
  </li>
{% endfor %}
</ul>
