---
layout: post
lang: en
ref: agent-orchestration-opencode-free
author: Ming Chen
title: "Orchestration in Production: Blogging from the Beach with Free OpenCode"
tags: [ai-agent]
image: /assets/img/2026-10-14-setup-ai-coding-agent-orchestration/orchestration-og.jpg
description: "Putting AI coding-agent orchestration to real use with free OpenCode: the orchestrator picks up the work, I just press merge — even from the beach."
---

>Last time I [just tried setting up orchestration for AI coding agents](/2026/10/14/setting-up-ai-coding-agent-orchestration.html). This time I put it to real use — and something happened I didn't expect: I'm writing this post from the beach, and all I have to do is press merge.

## This time it's not a "trial" anymore

- Last time was just setup plus a few small tasks to get a feel for it. This time I'm running it on real work for this very site: writing posts, fixing layouts, cleaning up tests.
- Instead of typing a prompt into every session, I describe the work once and let the system split it up and run it.
- And most importantly: I no longer have to sit at my desk all day 😄

## One orchestrator, a few workers

- The core architecture is still orchestrator + workers. The orchestrator is the "brain" session: it knows the task list, what's running, what's stuck, what's done.
- Workers are child sessions, each owning one job: one issue, one CI fix, one round of review comments.
- I keep the worker pool small: 2 workers running in parallel, with one slot reserved for urgent work. Opening more than that, I couldn't keep up with reading anyway — and free-tier resources are limited.

## Cron wakes it up on schedule

- My favorite part: the orchestrator gets woken up on a cron schedule. Each time it wakes, it checks what remains in the queue, which sessions are running, which died halfway.
- New work comes in, it spawns a worker on its own, assigns the task, and tracks it until there's a PR.
- Meaning I don't have to "stand watch". I hand off the work and go do something else — or go out — while the system keeps running.

## The issue -> PR -> reviewer -> merge flow

- My standard flow: every job is an issue -> worker creates a branch, codes, runs verification, opens a PR -> a reviewer reads it -> I'm the last one to press merge.
- The step I guard most strictly is the last one: merging is still done by a human hand. The orchestrator must not merge, and neither may an agent. That's my trust boundary.
- I had to replace the reviewer. The tool's native reviewer was broken, so I use a worker session as the reviewer instead: it reads the diff at the top of the PR, writes comments on each spot that needs fixing, and reports back to the session doing the work.
- Honestly, the worker-as-reviewer isn't as "solid" as I'd like, but it still catches real defects: missing meta descriptions, tags without pages, edits spilling outside the scope. That's enough for me not to shoot myself in the foot.

## Free models and getting switched mid-run

- I run on free models, so hitting quota or rate limits is normal, not exceptional.
- The system automatically switches to a different free model when the current one gets limited. The session doesn't die, it just swaps "brains" and keeps going.
- That works fine for me: the models don't answer perfectly consistently, but each worker owns one small, clearly-defined job so it doesn't drift much.
- In exchange, don't expect it to be as fast as the paid tier. Trading speed for zero cost is my deal.

## Artifacts and reports are where handoffs happen

- One small detail that saved me many times: workers don't hand off through memory, but through reports and artifacts.
- Reports have clear states: checkpoint, needs decision, stuck, done — one glance tells you where things stand, no need to ask again.
- Things that don't belong in a PR — notes, draft documents — go into a separate artifact directory, never into the repo. The repo stays clean, and I still have something to read.

## The biggest win: the beach + a phone

- This is the part I really want to tell. Because the flow is clear and the last step is just a merge, I can leave my desk.
- Sitting on the beach, I open my phone, see what the orchestrator reports as done, read the PR, press merge. Work in the queue keeps getting picked up.
- I don't code from the phone — I only review results. That's a big difference: no typing, just decisions.
- It genuinely feels like "out playing while the work still moves", not "out playing while worrying about work" 🏖️

## If you want to try it, a few warnings first

- Free-tier rate limits are real. There will be times you wait, times you switch models, times a whole session barely inches forward.
- Sessions often die midway. They don't fail loudly, they just go quiet. You have to watch and restart them — don't just press run and go to sleep.
- You're still the one who merges, still the one who decides. Orchestration doesn't decide for you, it just removes the manual labor.
- Most importantly: the agent runs with your user privileges. It can read your files, run your commands, push to your repos. Think ahead about what permissions it gets, which directory it works in, and what it must absolutely never touch.
- If you're just starting, my advice is to start small: one repo, one kind of task, one reviewer. Don't turn everything on at once.

To sum up: last time I "tried" it, this time I "apply" it. Setting up orchestration doesn't turn AI into an autonomous engineer, but it does one thing I love: I can leave my desk while the work keeps inching forward — and I'm still the one pressing the final button.
