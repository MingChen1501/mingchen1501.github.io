---
layout: post
lang: en
ref: lessons-opencode-subscription-multiple-coding-agents
date: 2026-10-20 11:00 +0700
author: Ming Chen
title: "What I Learned Buying an OpenCode Subscription and Running Multiple Coding Agents"
tags: [ai-agent]
description: "Lessons from paying for OpenCode and running several coding agents at once: model rotation, review fallback, and cost discipline."
---

Running several coding agents at once on this blog taught me more about operations than about AI. Recently I decided to pay for an OpenCode subscription, and that decision forced me to think clearly about quota, model choice, and process discipline. Here is what I learned — honestly, without marketing language.

## Why pay at all: one shared quota

All AO sessions on this project share one OpenCode account, so the orchestrator and the workers draw from the same quota. A long worker turn can starve the coordination layer: the orchestrator needs quota to check state, spawn sessions, and track PRs, and a worker running on the same model can drain exactly that.

My setup: the **OpenCode Go plan at 10 USD per month**, using only cheap models — mainly **DeepSeek (`deepseek-v4.1-flash`)** and **Muse (`muse-spark-1.3-contributor`)** — and no premium or expensive models. [OWNER FACT NEEDED: purchase date and quota/allowance numbers of the plan.]

Paying did not remove limits; it just moved the bottleneck. The real lesson was that a paid plan without discipline runs out the same way a free tier does — only later.

## The agent workflow the subscription supports

The subscription exists to serve a strict workflow, verified against this repo's orchestration rules:

- **At most one task worker at a time**, plus one buffer worker reserved only for filing issues. One worker = one small task = one PR.
- **Roles are separate sessions**: issue-writer, dev, reviewer, fixer. A session never reviews its own PR.
- Merges are squash merges only, on green CI — and the human still presses the button.

Keeping the pool at one worker was originally about peak CPU on my machine, but it doubles as cost discipline: fewer parallel long turns means less quota burned per hour. [OWNER FACT NEEDED: whether a remote host was tried, which one, its cost, and the verdict — running agents somewhere other than my own machine remains an option.]

## Model rotation: the practice that actually works

Every worker and reviewer session runs on a model **different from the orchestrator's** (overrides via `ao spawn --model`). This separation rule exists because a worker on the same model as the orchestrator drains the quota coordination needs. Keep at least two free models available so rotation always has a target.

Rate-limit evidence looks like structured `provider.quota` / 429 / `FreeUsageLimitError` errors — or a worker going idle with uncommitted work and no PR. When that happens, the verified rotation recipe is:

1. Kill the stuck session (its worktree survives on disk with uncommitted files — nothing is lost).
2. Respawn a fresh worker on a **different** free model for the same task, carrying the files over.
3. Commit and open the PR from the new session. Never respawn on the model that just failed.

One correction worth making: no command changes a running session's model, and rotation is the orchestrator's job — worker prompts must not promise "auto-swap on rate limit." An earlier post of mine suggested the system swaps models automatically; the verified practice is kill-and-respawn, done explicitly.

## When the native reviewer fails: the manual review fallback

The native AO reviewer is broken/disabled for this project, so review happens in **dedicated AO worker sessions after the PR is up — never before**. [OWNER FACT NEEDED: dates the native reviewer was observed failing, if worth publishing.]

Verdicts are posted as GitHub **comments**, because GitHub blocks self-approval from the same account: an AO approval never counts as a GitHub approval and never authorizes merging. The worker-as-reviewer is not perfect, but it catches real defects — missing meta descriptions, tags without pages, edits spilling outside scope — and that is enough to stop me from shooting myself in the foot.

## What actually consumed quota, and what saved it

What burned quota fastest:

- Long worker turns on large, vague tasks.
- Workers running the same model as the orchestrator.
- Parallel sessions all pulling from the same account at once.

What saved it:

- Small one-PR tasks with a tight scope.
- Sticking to cheap models only — DeepSeek `deepseek-v4.1-flash` and Muse `muse-spark-1.3-contributor`.
- Static guard checks that report in seconds instead of long agentic loops.

[OWNER FACT NEEDED: actual quota numbers and spend beyond the 10 USD/month plan price, if worth publishing.] I make no claims here about model quality, value, or benchmarks — only about what my workflow consumed and what it saved.

## Verdict: when paying is worth it

Paying is worth it when you run agents often enough that coordination starvation — not raw model access — is your bottleneck: one shared account, an orchestrator that must stay responsive, and workers doing real daily work. The free tier is enough when you run occasional small tasks and can tolerate waiting through rate limits and manual model switches.

[OWNER FACT NEEDED: my current stance — staying on the paid plan or going back to free.]
