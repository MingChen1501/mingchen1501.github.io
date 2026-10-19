> [!WARNING]
> **The `master` branch is under active development towards a semver-major release with non-backwards-compatible changes.**
> 
> While you may use this theme in the current state either via the `jekyll-remote-theme` plugin or via a Gemfile, it is
> recommended to point to a particular git ref that does not break your site's existing render and gradually update to a
> newer git ref via a pull request after consulting this repository's commit-log and README.
>
> **Pointing directly to the `HEAD` commit of the `master` branch is risky and may contain changes that break your site.** 
>
> Example of pointing to a particular git ref via `jekyll-remote-theme` plugin:
> ```yaml
> # _config.yml
>
> remote_theme: "jekyll/minima@1e8a445"
> ```
> Example of pointing to a particular git ref via `Gemfile` (with `theme: minima` in `_config.yml`)
> ```ruby
> # Gemfile
>
> gem "minima", github: "jekyll/minima", ref: "1e8a445"
> ```

<br/><br/>

<div align="center">
  <p><em><strong>Disclaimer:</strong> The information here may vary depending on the version you're using.<br/>
  Please refer to the <code>README.md</code> bundled within the theme-gem for information specific to your version or by pointing
  your browser to the Git tag corresponding to your version. e.g. https://github.com/jekyll/minima/blob/v2.5.0/README.md.<br/>
  Running <code>bundle show minima</code> will provide you with the local path to your current theme version.</em></p>
  <img src="/readme_banner.svg"/>
  <p>It's Jekyll's default (and first) theme. It's what you get when you run <code>jekyll new</code>.</p>
  <p><a href="https://jekyll.github.io/minima/">Theme preview</a></p>
  <p><img src="/screenshot.png"/></p>
</div>

## Installation

Add this line to your Jekyll site's Gemfile:

```ruby
gem "minima"
```

And then execute:

    $ bundle


## Contents At-A-Glance

Minima has been scaffolded by the `jekyll new-theme` command and therefore has all the necessary files and directories to have a new Jekyll site up and running with zero-configuration.

### Layouts

Refers to files within the `_layouts` directory, that define the markup for your theme.

  - `base.html` &mdash; The base layout that lays the foundation for subsequent layouts. The derived layouts inject their
    contents into this file at the line that says ` {{ content }} ` and are linked to this file via
    [FrontMatter](https://jekyllrb.com/docs/frontmatter/) declaration `layout: base`.
  - `home.html` &mdash; The layout for your landing-page / home-page / index-page. [[More Info.](#home-layout)]
  - `page.html` &mdash; The layout for your documents that contain FrontMatter, but are not posts.
  - `post.html` &mdash; The layout for your posts.

#### Base Layout

From Minima v3 onwards, the base layout is named **`base.html`** instead of `default.html` to avoid confusing new users into
assuming that name holds special status.

Users migrating from older versions with customized `_layouts/default.html` are advised to rename their copy to
`_layouts/base.html`. Migrating users with additional customized layouts may either update front matter references to former
`default.html` layout or create a new `default.html` layout referencing the current `base.html`, whichever route being the
easiest:

```
---
# new `_layouts/default.html` for backwards-compatibility when multiple
# layouts have been customized.

layout: base
---

{{ content }}
```

#### Home Layout

`home.html` is a flexible HTML layout for the site's landing-page / home-page / index-page. <br/>

##### *Main Heading and Content-injection*

From Minima v2.2 onwards, the *home* layout will inject all content from your `index.md` / `index.html` **before** the **`Posts`** heading. This will allow you to include non-posts related content to be published on the landing page under a dedicated heading. *We recommended that you title this section with a Heading2 (`##`)*.

Usually the `site.title` itself would suffice as the implicit 'main-title' for a landing-page. But, if your landing-page would like a heading to be explicitly displayed, then simply define a `title` variable in the document's front matter and it will be rendered with an `<h1>` tag.

##### *Post Listing*

This section is optional from Minima v2.2 onwards.<br/>
It will be automatically included only when your site contains one or more valid posts or drafts (if the site is configured to `show_drafts`).

The title for this section is `Posts` by default and rendered with an `<h2>` tag. You can customize this heading by defining a `list_title` variable in the document's front matter.


### Includes

Refers to snippets of code within the `_includes` directory that can be inserted in multiple layouts (and another include-file as well) within the same theme-gem.

  - `comments.html` &mdash; Markup to render comments (via Disqus; active only when Jekyll environment is set to `production`).
  - `footer.html` &mdash; Defines the site's footer section.
  - `google-analytics.html` &mdash; Inserts Google Analytics module (active only in production environment).
  - `head.html` &mdash; Code-block that defines the `<head></head>` in *default* layout.
  - `custom-head.html` &mdash; Placeholder to allow users to add more metadata to `<head />`.
  - `header.html` &mdash; Defines the site's main header section that consists of the site's *title* and *navigation*.
  - `nav-items.html` &mdash; Contains the logic and markup to render individual link items for the site's navigation.
  - `social.html` &mdash; Renders social-media icons based on the `minima:social_links` data in the config file using
    the latest version of Font Awesome Free webfonts via remote CDN.
  - `sub-footer.html` &mdash; Placeholder to allow inserting markup (e.g. deferred scripts) before the `</body>` tag.


### Sass

Refers to `.scss` files within the `_sass` directory that define the theme's styles.

  - `minima/skins/classic.scss` &mdash; The "classic" skin of the theme. *Used by default.*
  - `minima/initialize.scss` &mdash; A component that defines the theme's *skin-agnostic* variable defaults and sass partials.
    It imports the following components (in the following order):
    - `minima/custom-variables.scss` &mdash; A hook that allows overriding variable defaults and mixins. (*Note: Cannot override styles*)
    - `minima/_base.scss` &mdash; Sass partial for resets and defines base styles for various HTML elements.
    - `minima/_layout.scss` &mdash; Sass partial that defines the visual style for various layouts.
    - `minima/custom-styles.scss` &mdash; A hook that allows overriding styles defined above. (*Note: Cannot override variables*)

Refer the [skins](#skins) section for more details.


### Assets

Refers to various asset files within the `assets` directory.

  - `assets/css/style.scss` &mdash; Imports sass files from within the `_sass` directory and gets processed into the theme's
    stylesheet: `assets/css/styles.css`.
  - `assets/minima-social-icons.html` &mdash; Imports enabled social-media icon graphic and gets processed into a composite SVG file.
    Refer [section on social networks](#social-networks) for its usage.


### Plugins

Minima comes with [`jekyll-seo-tag`](https://github.com/jekyll/jekyll-seo-tag) plugin preinstalled to make sure your website gets the most useful meta tags. See [usage](https://github.com/jekyll/jekyll-seo-tag#usage) to know how to set it up.


## Usage

Have the following line in your config file:

```yaml
theme: minima
```


### Customizing templates

To override the default structure and style of minima, simply create the concerned directory at the root of your site, copy the file you wish to customize to that directory, and then edit the file.
e.g., to override the [`_includes/head.html `](_includes/head.html) file to specify a custom style path, create an `_includes` directory, copy `_includes/head.html` from minima gem folder to `<yoursite>/_includes` and start editing that file.

The site's default CSS has now moved to a new place within the gem itself, [`assets/css/style.scss`](assets/css/style.scss).

In Minima 3.0, if you only need to customize the colors of the theme, refer to the subsequent section on skins. To have your
*CSS overrides* in sync with upstream changes released in future versions, you can collect all your overrides for the Sass
variables and mixins inside a sass file placed at `_sass/minima/custom-variables.scss` and all other overrides inside a sass file
placed at path `_sass/minima/custom-styles.scss`.

You need not maintain entire partial(s) at the site's source just to override a few styles. However, your stylesheet's primary
source (`assets/css/style.scss`) should contain the following:

  - Front matter dashes at the very beginning (can be empty).
  - Directive to import a skin.
  - Directive to import the base styles (automatically loads overrides when available).

Therefore, your `assets/css/style.scss` should contain the following at minimum:

```sass
---
---

@import
  "minima/skins/{{ site.minima.skin | default: 'classic' }}",
  "minima/initialize";
```

#### Skins

Minima 3.0 supports defining and switching between multiple color-palettes (or *skins*).

```
.
├── minima.scss
└── minima
    └── _syntax-highlighting.scss
```


A skin is a Sass file placed in the directory `_sass/minima/skins` and it defines the variable defaults related to the "color"
aspect of the theme. It also embeds the Sass rules related to syntax-highlighting since that is primarily related to color and
has to be adjusted in harmony with the current skin.

The default color palette for Minima is defined within `_sass/minima/skins/classic.scss`. To switch to another available skin,
simply declare it in the site's config file. For example, to activate `_sass/minima/skins/dark.scss` as the skin, the setting
would be:

```yaml
minima:
  skin: dark
```

As part of the migration to support skins, some existing Sass variables have been retired and some **have been redefined** as
summarized in the following table:

Minima 2.0      | Minima 3.0
--------------- | ----------
`$brand-color`  | `$link-base-color`
`$grey-*`       | `$brand-*`
`$orange-color` | *has been removed*

##### Available skins

Skin setting    | Description
--------------- | -----------
classic         | Default, light color scheme.
dark            | Dark variant of the classic skin.
auto            | *Adaptive skin* based on the default classic and dark skins.
solarized       | *Adaptive skin* for [solarized](https://github.com/solarized) color scheme skins.
solarized-light | Light variant of solarized color scheme.
solarized-dark  | Dark variant of solarized color scheme.

*:bulb: Adaptive skins switch between the "light" and "dark" variants based on the user's operating system setting or browser setting
(via CSS Media Query [prefers-color-scheme](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-color-scheme)).*

### Customize navigation links

This allows you to set which pages you want to appear in the navigation area and configure order of the links.

For instance, to only link to the `about` and the `portfolio` page, add the following to your `_config.yml`:

```yaml
minima:
  nav_pages:
    - about.md
    - portfolio.md
```
> [!WARNING]
> Please note that **`site.header_pages`** is **`site.minima.nav_pages`** in Minima 3.0


### Change default date format

You can change the default date format by specifying `site.minima.date_format`
in `_config.yml`.

```
# Minima date format
# refer to http://shopify.github.io/liquid/filters/date/ if you want to customize this
minima:
  date_format: "%b %-d, %Y"
```


### Extending the `<head />`

You can *add* custom metadata to the `<head />` of your layouts by creating a file `_includes/custom-head.html` in your source directory. For example, to add favicons:

1. Head over to [https://realfavicongenerator.net/](https://realfavicongenerator.net/) to add your own favicons.
2. [Customize](#customization) default `_includes/custom-head.html` in your source directory and insert the given code snippet.


### Enabling comments

Comments are rendered below posts using one provider selected by configuration. The recommended provider is
Giscus, which stores threads in GitHub Discussions. Disqus remains supported for existing configurations.

```yaml
comments:
  provider: giscus   # none | giscus | disqus
  dev: false         # render comments in non-production builds for testing

giscus:
  repo: MingChen1501/mingchen1501.github.io
  repo_id: ...
  category: Announcements
  category_id: ...
  mapping: pathname
  strict: "0"
  reactions_enabled: "1"
  emit_metadata: "0"
  input_position: bottom
  theme: preferred_color_scheme
  lang: vi
  loading: lazy
```

To enable Giscus step by step (owner clicks required — a worker session cannot
install a GitHub App via OAuth on your behalf):

1. Enable GitHub Discussions (already on for this repo — verified via the API:
   `has_discussions: true`). If you ever need to re-check, go to
   `https://github.com/MingChen1501/mingchen1501.github.io/settings` and look
   for the Discussions checkbox under Features.
2. Install the Giscus App:
   - Open <https://github.com/apps/giscus> and click **Install**.
   - Choose **Only select repositories** and pick
     `MingChen1501/mingchen1501.github.io`, then **Install**.
   - This step is still pending: the Giscus backend currently answers
     `403 {"error":"giscus is not installed on this repository"}` for this repo,
     so live threads will not load until the install completes.
3. Pick a discussion category. This repo uses the default `Announcements`
   category; creating a dedicated `Comments` category later is optional.
4. Get the IDs from <https://giscus.app>:
   - Enter `MingChen1501/mingchen1501.github.io` in the **Repository** field.
   - Tick the checklist until every item is green (public repo, Giscus App
     installed, Discussions enabled).
   - Under **Page ↔️ Discussions Mapping** keep `pathname` (matches
     `giscus.mapping` below); under **Discussion Category** pick
     `Announcements` (matches `giscus.category`).
   - Copy the generated `data-repo-id` value into `giscus.repo_id` and the
     `data-category-id` value into `giscus.category_id` in `_config.yml`.
   - Already-verified values for this repo (confirmed against the GitHub API,
     no change needed): `repo_id: R_kgDOHBJg8A`,
     `category_id: DIC_kwDOHBJg8M4DIbBW` (`Announcements`).
5. Rebuild/redeploy the site and open any post: the Giscus thread should load
   instead of the "Comments are temporarily unavailable." fallback.

Legacy Disqus configurations still work when `site.comments.provider` is unset and `site.disqus.shortname`
is present. You can also use the original configuration directly:

```yaml
url: "https://my_domain.com"
disqus:
  shortname: my_disqus_shortname
```

Comments only appear in production (`JEKYLL_ENV=production`) unless `comments.dev: true` is set.
Set `comments: false` in a post's front matter to disable comments for that post.

You can find out more about Disqus' shortnames [here](https://help.disqus.com/installation/whats-a-shortname).

### Author Metadata

From `Minima-3.0` onwards, `site.author` is expected to be a mapping of attributes instead of a simple scalar value:

```yaml
author:
  name: John Smith
  email: "john.smith@foobar.com"
```

To migrate existing metadata, update your config file and any reference to the object in your layouts and includes as summarized below:

Minima 2.x    | Minima 3.0
------------- | -------------------
`site.author` | `site.author.name`
`site.email`  | `site.author.email`


### Social networks

You can add links to the accounts you have on other sites, with respective icon as an SVG graphic, via the config file.
From `Minima-3.0` onwards, the social media data is sourced from config key `minima.social_links`. It is a list of key-value pairs, each entry
corresponding to a link rendered in the footer. For example, to render links to Jekyll GitHub repository and Twitter account (now X), one
should have:

```yaml
minima:
  social_links:
    - title: Jekyll repository at GitHub
      icon: github
      url: "https://github.com/jekyll/jekyll"
    - title: Jekyll at X (formerly Twitter)
      icon: x-twitter
      url: "https://x.com/jekyllrb"
```

where `title` corresponds to the link-title displayed when a visitor hovers mouse-pointer over url / icon and
`icon` refers to the Font Awesome icon id. e.g. `github` corresponds to `fa-github`.

Social platform icons are rendered using the latest version of Font Awesome Free webfonts sourced via remote CDN.
The full list of available social icons can be found at https://fontawesome.com/search?ic=brands

> [!NOTE]
> The link to your site's main syndication feed is always rendered as the last item of the social-links list.<br />
> You may opt to not have this link rendered at all by setting config **`minima.hide_site_feed_link`** to `true`:
> ```yaml
> minima:
>   hide_site_feed_link: true  # `false` or `null` by default
> ```

### Enabling Google Analytics

To enable Google Analytics, add the following lines to your Jekyll site:

```yaml
google_analytics: G-NNNNNNNNNN  // The former `UA-NNNNNNNN-N` format is no longer supported by Google
```

Google Analytics will only appear in production, i.e., `JEKYLL_ENV=production`.

### Enabling Excerpts on the Home Page

To display post-excerpts on the Home Page, simply set `show_excerpts` under top-level key `minima` to `true` in your
`_config.yml`:

```yaml
minima:
  show_excerpts: true
```


## Image conventions

Site images live under `assets/img/<post-slug>/` and are committed to git
(decision for #19: **compress-local by default** — no CDN or Git LFS unless a
future post proves a strong reason otherwise; this keeps the repo self-contained
on GitHub Pages and is the prerequisite for the hotlink cleanup in #18).

Rules for new posts:

- Location: `assets/img/<post-slug>/` matching the post filename slug.
- Naming: lowercase, hyphen-separated, no spaces, quotes, diacritics, or
  special characters (e.g. `desktop-fedora.jpg`, not `Screenshot From ....png`).
- Format: JPG (photos/screenshots) or WebP; PNG only for line-art needing
  lossless. Flatten alpha to white when converting to JPG.
- Size: resize so the long edge is at most **1600px**, JPEG quality ~75
  (progressive, optimized). Each file must be **<= 500KB** and the whole
  `assets/img/` folder must stay **<= 6MB**.

Budget policy (#33): the 6MB total is a hard CI gate. Per-post guidance:
  aim for a post's images to total **<= 500KB** (and no single post should add
  more than ~1MB without review). When the folder approaches 6MB, compress
  existing images harder or remove obsolete assets before raising the budget
  again; raising the cap requires a decision recorded in the tracking issue.
- Reference images with absolute site paths, e.g.
  `![Desktop](/assets/img/2026-01-01-Migrate-windows-11-to-fedora/desktop-fedora.jpg)`.

Compress locally before committing, for example with Pillow:

```sh
python3 - <<'PY'
from PIL import Image, ImageOps
im = ImageOps.exif_transpose(Image.open("input.jpg"))
im.thumbnail((1600, 1600), Image.LANCZOS)
if im.mode in ("RGBA", "LA"):
    bg = Image.new("RGB", im.size, (255, 255, 255))
    bg.paste(im, mask=im.split()[-1])
    im = bg
elif im.mode != "RGB":
    im = im.convert("RGB")
im.save("output.jpg", "JPEG", quality=75, optimize=True, progressive=True)
PY
```

Enforcement: `script/check-images` fails the build when any image exceeds
500KB, `assets/img` exceeds 6MB, a new image filename is not lowercase-hyphen
with a lowercase extension (legacy names were allowlisted; the allowlist is
empty since #171 converted the last of them), or an image's
long edge exceeds 1600px. Budget limits live in `script/image-budget.sh`
(single source of truth). It runs in `script/cibuild` and as the
"Check image sizes" step in `.github/workflows/ci.yaml`.

## External attachment images (temporary workaround, #195)

Dedicated object storage is unavailable due to billing, so article images
live as GitHub issue attachments and posts embed them by direct URL
(`https://github.com/user-attachments/assets/...`). This is explicitly
temporary: when Cloudflare R2, Amazon S3, or another dedicated store becomes
available and the owner approves it, the worker moves the files, rewrites
the post URLs, and removes the workaround.

Single source of truth: `_data/image_hosts.yml` (allowed hosts + path
prefixes). Repointing that one file repoints every check. Rules for new
article images:

- `https://` only — plain `http://` fails CI.
- Host and path must be allowlisted in `_data/image_hosts.yml`
  (today: `github.com` + `/user-attachments/assets/`).
- Non-empty alt text describing the photo.
- Explicit dimensions for CLS: kramdown
  `{: width="W" height="H" }` after a markdown image (values are the real
  pixel size of the attachment), or literal `width`/`height` attributes on
  raw-HTML `<img>` blocks, e.g.
  `![Fedora desktop after setup](https://github.com/user-attachments/assets/XXXX){: width="1600" height="900" }`.

Enforcement: `script/check-external-images` (the "Check external attachment
images" step in `.github/workflows/ci.yaml`) validates every external image
in `_posts/` and `_vi_posts/` fully offline — it never downloads the URLs,
so CI has no live-network dependency. `script/check-images` still covers
only local files: external bytes never count toward the 6MB `assets/img/`
budget. Lighthouse keeps measuring pages with external images (no origin is
blocked); attachment-hosted bytes carry a documented exemption from the
local budget instead of a byte threshold, because the site does not control
their compression.

Migration cleanup (owner-approved storage only): repoint
`_data/image_hosts.yml` to the new store, rewrite the post URLs, remove the
attachment-host allowlist entry if no longer needed, remove the Lighthouse
budget exemption, and update this section.

## Asset cache versioning (#61)

GitHub Pages (through Cloudflare) serves everything under `assets/**` with
`cache-control: max-age=14400` (four hours) from a **fixed URL**, while the HTML
is only `max-age=600`. A warm browser can therefore pair *new* HTML with an
*old* asset. That is exactly how the #58 list-page sidebar "disappeared" on the
live site: the pre-#58 stylesheet has no `.site-layout` grid, so the sidebar
painted as a full-width block below the whole post list for up to four hours
after the deploy.

Rules:

- Every fixed-URL asset linked from a template carries the build token that
  `_includes/head.html` assigns: `/assets/css/style.css?v={{ asset_version }}`
  and `/assets/img/favicon.ico?v={{ asset_version }}` (head), plus the
  deferred scripts in `_includes/sub-footer.html`
  (`lazy-load.js`, `nav-toggle.js`, `copy-code.js`, `lang-switch.js`). A new
  fixed-URL asset must do the same.
- The token is `site.time` (epoch seconds). It needs no plugin and works with
  GitHub Pages `--safe`, `bundle exec jekyll serve` and the E2E build, and it
  changes on every build — a superset of "the content changed", so a cached
  asset can never be served against newer HTML. Cost: the stylesheet is fetched
  once per deploy (~18KB) even when it did not change. A real content hash of
  the compiled CSS would need a Jekyll plugin, which GitHub Pages does not run
  in its `--safe` build.
- Images are **not** versioned: their URLs are content-addressed by convention
  (`assets/img/<post-slug>/<name>`). When an image's content changes, publish it
  under a **new filename** instead of rewriting the file in place, because
  `assets/img/**` carries the same four-hour `max-age`.
- Guard: `tests/e2e/test_stylesheet_cache_version.py` fails when the stylesheet
  link loses its token, when a template links an unversioned `/assets/` URL, or
  when a rebuild after a CSS change emits the same stylesheet URL.

Residual manual step for #61: after the fix is deployed, a visitor whose browser
already cached the old stylesheet may need one hard refresh (Ctrl+Shift+R); the
fix can only take effect from the next deploy onward.

## Clone size

This repository's git history intentionally retains large binary blobs
(~22MB of multi-MB assets, packed history ~33MB on-disk: a ~4.8MB screenshot
PNG, a ~2.4MB JPG, the removed Unity `Build/` artifacts (#186, still in
history), the `fullmonth/` avatar, post images, and PDF resumes). Image
compression work (#27) shrinks the working tree only; clone size is unchanged
by design.

Decision for #34: **keep history as-is** rather than run `git-filter-repo` /
BFG. Rewriting would break commit hashes, invalidate open pull requests, and
disrupt GitHub Pages deploys, while the real working-tree budget is already
enforced by `script/check-images`. Large binaries are marked as `binary` in
`.gitattributes` so Git never attempts text diffs or line-ending conversion.

Need a smaller checkout? Use a shallow clone:

```sh
git clone --depth 1 https://github.com/MingChen1501/mingchen1501.github.io.git
```

Full history can be fetched later with `git fetch --unshallow`.

## Writing a new post (mingchen.id.vn taxonomy)

> Site-specific section (not part of upstream Minima docs).

The blog is bilingual since #93: **English is the default** (`/`, `_posts/`),
**Vietnamese is the second option** (`/vi/`, the `site.vi_posts` collection).
Every post ships in both languages, linked by a shared `ref` in front matter
(the switcher and the hreflang alternates resolve through it); every post ships
a real translation in both languages since #97
(`tests/e2e/test_i18n.py` fails otherwise — no `fallback_vi` stubs remain, the
layout/include banner plumbing stays wired for any future untranslated post).
English-only going forward
is acceptable; Vietnamese-only is not. Old Vietnamese URLs keep working via
`redirect_from` stubs to `/vi/...`, so a new English slug must never reuse an
old Vietnamese slug. Phasing: PR A shipped the infrastructure with English stubs,
PR B the full translations, PR C the per-language SEO surface (sitemap/llms/feed).

New posts must pick tags from the 4 content pillars only
(`backend-production`, `ai-agent`, `linux-tooling`, `doi-song`, max 4 tags/post)
and always include a short translated `description` (~120–155 characters) so
`jekyll-seo-tag` renders a proper meta description. To feature posts in the
list sidebar's highlight block, add their slugs (file name without `.md`) to
that language's list (`en:` / `vi:`) in `_data/highlights.yml` (single source
of truth, #64) in the order you want them to appear. Copy this template
(`lang: vi` + `_vi_posts/` for the Vietnamese file):

```yaml
---
layout: post
lang: en
ref: my-post-key
author: Ming Chen
title: "Your post title"
tags: [linux-tooling]
description: "One short sentence (120-155 chars) summarising the post for SEO and social previews."
---
```

The [`/tags/`](/tags/) page is the index of those 4 pillars and is
linked from the header navigation via `minima.nav_pages` in `_config.yml`.
Each pillar also has its own page — `/tags/<tag>/`, e.g.
[`/tags/linux-tooling/`](/tags/linux-tooling/) — listing the posts with that
tag, plus its Vietnamese mirror `/vi/tags/<tag>/`. Those pages are front-matter
only (`tags/<tag>.md` + `vi/tags/<tag>.md` + `_layouts/tag.html`) because
GitHub Pages builds with `--safe`, where no archive/tagging plugin can run.
A new tag therefore needs **both** a `tags/<tag>.md` page and its entry in
`tags.md` (and the same pair under `vi/`); `tests/e2e/test_post_layout_markup.py`
fails if a published post uses a tag without a page in its language.
Tag display labels and URL slugs are localized per page language via
`_data/tag_labels.yml` (single source of truth, #129): post front matter
keeps the canonical key (e.g. `doi-song`), English pages render "Life" at
`/tags/life/` (the old `/tags/doi-song/` redirects there), Vietnamese pages
render "Đời sống" at `/vi/tags/doi-song/`. Technical tags keep the same slug
and English label in both languages.

Post pages render a secondary column with the post's tags and the other posts
sharing its first tag (`_layouts/post.html`, `_includes/post-tags.html`, styles
in `_sass/minima/custom-styles.scss`, an index over the `_sass/minima/custom/`
partials).

The list pages — the English home list (`/`, `/page2/…`, paginated by
`jekyll-paginate` over the English-only `site.posts`), the Vietnamese home
(`vi/index.html`, `vi/page2/index.html`, …) and the tag pages
(`/tags/<tag>/`, `/vi/tags/<tag>/`) — render
the same sidebar from one shared include, `_includes/site-sidebar.html`:

Pagination sources (#155, #176): `paginate:` in `_config.yml` is the single
value — `jekyll-paginate` reads it for the English stream, while the
Vietnamese home (explicit `vi/pageN/index.html` files with `vi_page_num`
front matter, because `jekyll-paginate` v1 supports a single stream only)
slices `site.vi_posts` and renders its pager in `_layouts/home.html` and its
`prev`/`next` links in `_includes/head.html` from the same `site.paginate`
(the `default: 5` fallback only covers configs without it, e.g. upstream
theme-dev).

- **Featured** / **Bài nổi bật** — the *highlighted* posts: the slugs listed in
  that language's list (`en:` / `vi:`) in `_data/highlights.yml` (single source
  of truth, #64), resolved against that language's post source in the file's
  order, at most five, each with its title, its publication date and its
  thumbnail when it has one. Unknown or unpublished slugs are skipped. When the
  list is empty or missing, the block falls back to the five newest posts of
  that language and its heading reads **Latest posts** / **Bài mới nhất**.
- **Topics** / **Chủ đề** — every tag as a row collapsed by default (`<details>`):
  the chip and its post count, and, once opened, at most three post links plus
  `View all` / `Xem tất cả` to that tag's page.

The column is the second column from 960px up and moves under the list on
phones. It is deliberately short (capped thumbnails, two-line titles, collapsed
tag rows) so that it needs no scrollbar of its own, and it is pinned
(`position: sticky`) only where it fits beside the list — desktop width *and* at
least 720px of viewport height. `tests/e2e/test_sidebar_layout.py` guards all of
that. Thumbnails reuse `post.image` or the first image of the post body — never
cropped, never upscaled, and no generated `thumb-*` files, because `assets/img/`
runs close to its 6MB budget (`script/check-images`).

## Contributing

Bug reports and pull requests are welcome on GitHub at
https://github.com/MingChen1501/mingchen1501.github.io. This project is
intended to be a safe, welcoming space for collaboration, and contributors are
expected to adhere to the [Contributor Covenant](http://contributor-covenant.org)
code of conduct.

## Development

Preview real content with `bundle exec jekyll serve` (uses `_config.yml`;
`bundle install` first if gems are missing) and open your browser at
`http://localhost:4000`. As you make modifications, your site will regenerate
and you should see the changes in the browser after a refresh. Other checks:

- `bundle exec jekyll build --trace` — verify the site builds.
- `python -m pytest tests/e2e -v` — end-to-end guards (first time:
  `pip install -r tests/e2e/requirements.txt`).
- `script/check-images` — image budget gate (each file <= 500KB,
  `assets/img/` total <= 6MB).

The `script/bootstrap`, `script/server`, `script/build`, and `script/cibuild`
helpers are upstream minima leftovers: they target the theme-dev sample site
(`_config_theme-dev.yml`, minima placeholder content), not the personal posts.
Never use `script/server` to preview personal posts (see `AGENTS.md`).

## License

The theme is available as open source under the terms of the [MIT License](http://opensource.org/licenses/MIT).
