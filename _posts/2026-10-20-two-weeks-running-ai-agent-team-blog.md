---
layout: post
lang: en
ref: hai-tuan-van-hanh-blog-cung-ai-agent-team
author: Ming Chen
title: "Two weeks of running an AI agent team on my personal blog"
tags: [ai-agent]
description: "How I ran my Jekyll blog with a team of AI coding agents for two weeks: issue-driven work, review loops, and bilingual shipping."
---

For the last two weeks, nearly every change on this blog came out of orchestrated AI agent sessions, not out of my editor. This site is a Jekyll minima fork deployed with GitHub Pages from `master` — a small, boring, well-understood stack. That turned out to be the perfect place to find out what an agent team is actually good at.

## Every change starts as an issue

The single biggest process change: nothing gets built without a GitHub issue first. Each issue carries the context, the scope, what is explicitly out of scope, acceptance criteria, and exactly one risk label (`risk-low`, `risk-medium`, `risk-high`, or `risk-very-high`). No label, no work.

This sounds bureaucratic. In practice it is the opposite — it is what lets me hand a task to an agent session and walk away. The issue is the spec, the worker session implements it, and the PR closes the loop. Vague asks produce vague diffs; the template forces the ask to be sharp before any code exists.

## The review loop is the real product

Every PR goes through dedicated review sessions whose verdicts land as GitHub comments. Self-approval is blocked on this repo, so a review thread is not decoration — it gates the merge. Merges are squash-only, and only on green CI plus review.

The loop catches real things. At least once, review feedback went back into the code before merge (the comments E2E work carries a fix commit that exists only because a reviewer asked for it). That is the whole point: agents write the first draft fast, reviewers make it shippable, and the history shows which is which.

## CI does the boring verification

The E2E suite lives under `tests/e2e/` and currently holds 42 test files. It runs in two speeds: fast browser-free static guards (front matter, taxonomy, redirects, markup contracts) plus a Playwright browser matrix. The recent stretch added an axe-core accessibility smoke test, visual-regression baselines with screenshots, a Firefox plus WebKit browser matrix on top of Chromium, a site-wide internal link crawl with sitemap and feed validation, and a Giscus embed test that runs against a production-mode build.

There is also Lighthouse CI on every PR to `master`. An agent can generate a lot of code quickly; the gates decide whether any of it ships.

## What two weeks actually produced

Numbers below were re-verified from git history and the merged-PR list at draft time (October 20, 2026) — anything I could not verify did not make it into this post:

- **Merge velocity.** PRs #160 through #217 all merged across October 19–20: content fixes, i18n work, refactors, and the test batch above. The run stretches back further (the bilingual and sidebar groundwork merged earlier), but that two-day window alone is the densest shipping this blog has ever seen.
- **Bilingual shipping.** The site is fully English/Vietnamese: a compact pill language switcher, hreflang alternates in the sitemap and page heads, and localized post chrome (Tags/Comments headings, footer copy, alt text). At draft time there are 7 English posts under `_posts/` against 6 Vietnamese under `_vi_posts/` — translations trail the originals by design, and each home page states its own total instead of pretending they match.
- **The UX audit and its fix train.** A read-only audit of the live site scored navigation 6.6, mobile/accessibility 6.5, and reading/performance 6.0 out of 10. It was split into thirteen one-fix issues (#139–#151, twelve `risk-low` and one `risk-medium`), each closed by its own small PR: tap-target sizes, accessible names for footer links, a single H1 on portfolio pages, pluralized post counts, reading-position-preserving language switch, and the rest.
- **Clean-code refactors.** Shared partials replaced copy-paste: one tag-label partial for chips, tag pages, and the sidebar; one shared ref-resolution partial behind the alternates, switcher, and notice; the CSS split into scoped partials; one single source for the per-page pagination count.
- **The article workflow itself.** This very post traveled the same pipeline: an article issue template plus label, an intake scan that picks article issues up, a writer role and skill, a chat-draft flow for starting from rough notes, and CI support for externally attached images.

## What the agents still get wrong

Honestly, and sticking to what I observed: agents happily generate diffs that look finished but are not — the audit's defect list (nested interactive elements, a doubled H1, bare URLs, terse alt text) is what "looks done" looks like without verification. They also scope-creep: left alone, a session will fix three things when the issue asked for one, which is why the one-article-per-PR and one-fix-per-PR rules exist. And none of the process works if the acceptance criteria are sloppy — garbage in, garbage merged.

Everything above was caught by something structural (the audit, the review loop, the tests), not by luck. That is the honest version of the story: the agents are fast, the scaffolding is what makes them safe.

## Verdict

This setup suits small, well-specified, reversible work on a stack with good guardrails — exactly what a personal Jekyll blog is. The agents do the volume; issues, reviews, and CI do the judgment.

What I still decide by hand: anything `risk-high`, the product direction of the site, and whether a merged-looking diff is actually good. After two weeks, my job moved from writing code to writing issues and reading diffs. For this blog, that turns out to be a pretty good trade.
