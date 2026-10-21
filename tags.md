---
layout: page
lang: en
ref: tags
title: Tags
permalink: /tags/
description: "Browse posts by topic, from backend production and AI agents to everyday life."
---

Posts are grouped by topic: curated pillars first, then more topics. Pick a topic to see its posts.

{% comment %}
  Data-driven index (#344): every tag with at least one published post
  renders — no hardcoded list. Pillars (`pillar: true`) come first by
  `order` (zero-padded so the string sort stays numeric); every other tag
  follows under "More topics" sorted by the localized label, never the raw
  key. Labels, slugs and descriptions resolve from `_data/tag_labels.yml`;
  unknown keys degrade to the canonical key with no description.
{% endcomment %}
{% assign index_pillar_keys = "" | split: "" %}
{% assign index_more_keys = "" | split: "" %}
{% assign index_pairs = site.tags | sort %}
{% for index_pair in index_pairs %}
{% assign index_key = index_pair[0] %}
{% assign index_entry = site.data.tag_labels[index_key] %}
{% assign index_label = index_entry.en | default: index_key %}
{% if index_entry.pillar == true %}
{% assign index_order = index_entry.order | default: 999 %}
{% assign index_pad = "000" | append: index_order | slice: -3, 3 %}
{% assign index_sort_key = index_pad | append: "|" | append: index_label | append: "|" | append: index_key %}
{% assign index_pillar_keys = index_pillar_keys | push: index_sort_key %}
{% else %}
{% assign index_sort_key = index_label | append: "|" | append: index_key %}
{% assign index_more_keys = index_more_keys | push: index_sort_key %}
{% endif %}
{% endfor %}
{% assign index_pillar_keys = index_pillar_keys | sort %}
{% assign index_more_keys = index_more_keys | sort %}
<ul class="tag-index">
{% for index_sort_key in index_pillar_keys %}
{% assign index_parts = index_sort_key | split: "|" %}
{% assign index_tag = index_parts[2] %}
{% assign index_posts = site.tags[index_tag] | sort: "date" | reverse %}
{% assign index_entry = site.data.tag_labels[index_tag] %}
{% assign index_label = index_entry.en | default: index_tag %}
{% assign index_slug = index_entry.slug_en | default: index_tag %}
{% assign index_desc = index_entry.description_en | default: "" %}
  <li>
    <a class="tag-chip" rel="tag" href="{{ '/tags/' | append: index_slug | append: '/' | relative_url }}">{{ index_label | escape }}</a>
    <span class="tag-index__count">{{ index_posts | size }} post{% if index_posts.size != 1 %}s{% endif %}</span>
    {%- if index_desc != "" -%}
    <span class="tag-index__desc">{{ index_desc | escape }}</span>
    {%- endif -%}
  </li>
{% endfor %}
</ul>
{% if index_more_keys.size > 0 %}
<h2 class="tag-index__subheading">More topics</h2>
<ul class="tag-index">
{% for index_sort_key in index_more_keys %}
{% assign index_parts = index_sort_key | split: "|" %}
{% assign index_tag = index_parts[1] %}
{% assign index_posts = site.tags[index_tag] | sort: "date" | reverse %}
{% assign index_entry = site.data.tag_labels[index_tag] %}
{% assign index_label = index_entry.en | default: index_tag %}
{% assign index_slug = index_entry.slug_en | default: index_tag %}
{% assign index_desc = index_entry.description_en | default: "" %}
  <li>
    <a class="tag-chip" rel="tag" href="{{ '/tags/' | append: index_slug | append: '/' | relative_url }}">{{ index_label | escape }}</a>
    <span class="tag-index__count">{{ index_posts | size }} post{% if index_posts.size != 1 %}s{% endif %}</span>
    {%- if index_desc != "" -%}
    <span class="tag-index__desc">{{ index_desc | escape }}</span>
    {%- endif -%}
  </li>
{% endfor %}
</ul>
{% endif %}
