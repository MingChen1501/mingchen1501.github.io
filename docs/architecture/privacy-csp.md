# Privacy posture and the deliberate no-CSP decision

Purpose: record the round-10 privacy/security audit outcome (#329) — what
third parties reader pages touch, why the site ships no
`Content-Security-Policy`, and what the owner-side alternative is. No code
change accompanies this record; the posture was already clean.

## Third-party inventory

Home page: zero third-party requests.

- System font stack, no webfont, no Google Fonts link anywhere. The footer
  social icons are inlined SVGs (`_includes/social.html`), not the former
  Font Awesome stylesheet over `cdn.jsdelivr.net` — see the comment at
  `_includes/head.html:64-73` (#254). The standalone `fullmonth/` page,
  which brought its own preconnect, was removed in #294.
- No analytics: `_includes/google-analytics.html:1` would load
  `www.googletagmanager.com`, but it only renders when `site.google_analytics`
  is set (`_includes/head.html:115`). That key is absent from `_config.yml`
  (grep `google_analytics` matches only the include and its guard), so the
  snippet never renders.

Production post pages: exactly one third party, Giscus.

- `_includes/comments.html:14` loads `https://giscus.app/client.js` with
  `data-loading="lazy"` (`_includes/comments.html:28`); the only other
  comments script is the first-party theme repaint
  (`_includes/comments.html:45`, `assets/js/giscus-theme.js`, #258), which
  makes no network request of its own. Non-comment pages fetch nothing
  (`comments.html:10` gates on the `giscus` provider).
- The lazy Giscus iframe embeds GitHub Discussions content, so a production
  post view passively exposes IP, user-agent, and page path to giscus.app /
  GitHub before any login click — relevant to the `about.md` correction
  below.

Share row: navigation-only, no SDKs.

- The X / Facebook / LinkedIn links are plain share-intent hyperlinks that
  work with JS disabled (`_includes/share.html:15-17`); no third-party
  script loads until the reader clicks one. Copy-link and native-share are
  first-party (`assets/js/share.js`, #244).

Re-verify with:

```sh
grep -rn "giscus.app" _includes/ _layouts/ _config.yml
grep -n "google_analytics" _config.yml _includes/head.html
grep -rni "fonts.googleapis\|fonts.gstatic\|cdn.jsdelivr\|cdnjs" _includes/ _layouts/ assets/css/ assets/js/
grep -rni "content-security-policy" _includes/ _layouts/
```

## Why no `<meta>` CSP

GitHub Pages offers no response headers, so only
`<meta http-equiv="Content-Security-Policy">` is available — and it is
self-defeating here:

1. `script-src 'unsafe-inline'` is forced. The theme bootstrap must run
   inline before first paint (`_includes/head.html:83`, #220 — a deferred
   script would flash the wrong theme), and the per-page jekyll-seo-tag
   block (`{%- seo -%}`, `_includes/head.html:5`) emits inline JSON-LD.
   The attainable policy therefore blesses exactly the inline code it
   should constrain — security theater.
2. `<meta>` CSP cannot set `frame-ancestors` (ignored in meta delivery)
   and has no useful reporting channel, so the two directives that would
   most constrain the Giscus iframe threat are unavailable.
3. A Giscus allowlist is brittle: `script-src`/`frame-src` entries for
   giscus.app plus GitHub origins weaken the policy to named third
   parties and break silently when upstream origins change.

Deliberate decision: ship no CSP meta tag on any built page until a real
response-header policy is possible. Revisit only if hosting gains header
support (see below) or the inline bootstrap / seo-tag constraint changes.

## Owner-side option: Cloudflare response headers (no repo change)

Pages are served over TLS through Cloudflare's edge network (see the
Privacy section of `about.md`). The site owner can set a real
`Content-Security-Policy` — including `frame-ancestors` and reporting —
as response headers at the Cloudflare edge. That is an owner-side
dashboard action; it requires and receives no change in this repository.

## Queued correction: `about.md` privacy boundary (NOT applied here)

`about.md:20-22` says comments "follow GitHub's privacy terms once you
interact with them". That boundary is wrong: as recorded above,
`client.js` plus the lazy iframe expose IP/UA/page-path to giscus.app /
GitHub passively in production before any login click.

The one-line correction (e.g. "loading a post page with comments fetches
Giscus (GitHub Discussions) resources, exposing your IP address,
user-agent, and page path to giscus.app/GitHub before you interact") is
deliberately NOT applied in the #329 PR: it would make that PR
reader-visible. Apply it on the next `about.md` touch instead.
