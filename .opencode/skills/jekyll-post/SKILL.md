---
name: Jekyll Post
description: Create a new post for the site (dated file name, standard front matter, trial build). Use when adding a blog post.
---

# Write a new post

## Workflow

1. Get the post title + publish date (default today).
2. Create an ascii slug: lowercase, no diacritics, words joined with `-`. File name:
   `_posts/YYYY-MM-DD-<slug>.md`.
3. Read `references/front-matter.md`, then write front matter + Vietnamese body content.
   Front matter must include `tags: [one-of-4-pillars]` and `description`
   (~120-155 chars) per the 4-pillar taxonomy. If the tag has no page yet, add
   `tags/<tag>.md` + its `tags.md` entry too (the post page's tag chips link to
   `/tags/<tag>/`).
4. If the post adds images, place them under `assets/img/<post-slug>/` following
   the naming/size rules in the README "Image conventions" section and run
   `script/check-images` (each file <= 500KB, `assets/img/` total <= 6MB).
5. Run `bundle exec jekyll build --trace` to make sure the post renders.
6. Open the matching post file under `_site/` to check the title/date. Note the homepage
   has `show_excerpts: true`, so the opening paragraph appears on the homepage — keep
   the opening concise.

Do not commit the `_site/` directory (already in `.gitignore`).
