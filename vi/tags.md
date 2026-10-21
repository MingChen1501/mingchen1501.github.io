---
layout: page
lang: vi
ref: tags
title: Chủ đề
permalink: /vi/tags/
description: "Xem bài viết theo chủ đề: các chủ đề chính trước, sau đó là các chủ đề khác."
---

Bài viết được nhóm theo chủ đề: các chủ đề chính hiện trước, sau đó là các chủ đề khác. Chọn một chủ đề để xem các bài viết cùng tag.

{% comment %}
  Nil-safe like the tag layout: the collection may be undefined in the
  upstream `_config_theme-dev.yml` CI build.
{% endcomment %}
{% assign vi_tags_source = site.vi_posts %}
{% if vi_tags_source == nil %}
{% assign vi_tags_source = "" | split: "" %}
{% endif %}
{% comment %}
  Data-driven index (#344): every tag with at least one published post
  renders — no hardcoded list. Pillars (`pillar: true`) come first by
  `order` (zero-padded so the string sort stays numeric); every other tag
  follows under "Chủ đề khác" sorted by the localized label, never the raw
  key. Labels, slugs and descriptions resolve from `_data/tag_labels.yml`;
  unknown keys degrade to the canonical key with no description.
{% endcomment %}
{% assign vi_tag_names = vi_tags_source | map: "tags" | join: "," | split: "," | uniq | sort %}
{% assign index_pillar_keys = "" | split: "" %}
{% assign index_more_keys = "" | split: "" %}
{% for index_key in vi_tag_names %}
{% assign index_entry = site.data.tag_labels[index_key] %}
{% assign index_label = index_entry.vi | default: index_key %}
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
{% assign index_posts = vi_tags_source | where_exp: "post", "post.tags contains index_tag" | sort: "date" | reverse %}
{% comment %}
  No singular/plural branch needed (#149): Vietnamese nouns do not
  inflect, so "1 bài" and "N bài" below are both correct.
{% endcomment %}
{% assign index_entry = site.data.tag_labels[index_tag] %}
{% assign index_label = index_entry.vi | default: index_tag %}
{% assign index_slug = index_entry.slug_vi | default: index_tag %}
{% assign index_desc = index_entry.description_vi | default: "" %}
  <li>
    <a class="tag-chip" rel="tag" href="{{ '/vi/tags/' | append: index_slug | append: '/' | relative_url }}">{{ index_label | escape }}</a>
    <span class="tag-index__count">{{ index_posts | size }} bài</span>
    {%- if index_desc != "" -%}
    <span class="tag-index__desc">{{ index_desc | escape }}</span>
    {%- endif -%}
  </li>
{% endfor %}
</ul>
{% if index_more_keys.size > 0 %}
<h2 class="tag-index__subheading">Chủ đề khác</h2>
<ul class="tag-index">
{% for index_sort_key in index_more_keys %}
{% assign index_parts = index_sort_key | split: "|" %}
{% assign index_tag = index_parts[1] %}
{% assign index_posts = vi_tags_source | where_exp: "post", "post.tags contains index_tag" | sort: "date" | reverse %}
{% assign index_entry = site.data.tag_labels[index_tag] %}
{% assign index_label = index_entry.vi | default: index_tag %}
{% assign index_slug = index_entry.slug_vi | default: index_tag %}
{% assign index_desc = index_entry.description_vi | default: "" %}
  <li>
    <a class="tag-chip" rel="tag" href="{{ '/vi/tags/' | append: index_slug | append: '/' | relative_url }}">{{ index_label | escape }}</a>
    <span class="tag-index__count">{{ index_posts | size }} bài</span>
    {%- if index_desc != "" -%}
    <span class="tag-index__desc">{{ index_desc | escape }}</span>
    {%- endif -%}
  </li>
{% endfor %}
</ul>
{% endif %}
