---
layout: post
lang: en
ref: back-to-linux-fundamentals
date: 2026-10-22 15:40 +0700
author: Ming Chen
title: "Going back to Linux fundamentals after years of vibe coding"
tags: [linux-tooling]
description: "Revisiting Linux fundamentals after years of practical work: 20 compact revision notes on filesystem, permissions, processes, and shell tools."
---

Most of my Linux knowledge was picked up by doing, not by studying. For years I glued things together with searches, copy-pasted commands, and more recently AI assistance, and that was usually enough to ship whatever sat in front of me. My day job never forced a deeper return to the fundamentals either: servers mostly worked, containers hid the rest, and anything unfamiliar could be worked around without truly understanding it.

Revisiting a flashcard set recently showed how much of the basics had slipped. I recognised every topic but could not always explain it cleanly without guessing, especially around permissions, signals, and the filesystem layout. Nothing here is a war story or a production outage tale; it is simply the gap between using Linux every day and being able to explain it. So these are my revision notes: the same twenty questions, answered compactly in my own words as a personal checkpoint, not as a tutorial and not as a study app.

## Filesystem layout

**Where do the main directories live?** `/bin` holds essential user commands, `/etc` holds system configuration, `/home` holds user home directories, `/var` holds variable data such as logs and mail, `/tmp` holds temporary files, `/usr` holds secondary user programs and libraries, and `/opt` holds optional add-on software. On most current distributions `/bin` is a symlink to `/usr/bin` after the usrmerge, so the split matters more for the standard than for daily navigation.

## Permissions and ownership

**What does `rwx` mean, and what is `rwxr-xr--` in numbers?** `r`, `w`, and `x` stand for read (4), write (2), and execute (1), repeated in three sets for owner, group, and others. `rwxr-xr--` therefore means the owner can do everything, the group can read and execute, and others can only read, which is 754.

**How do I read a `chmod` command?** Numeric mode sets all three sets at once, as in `chmod 754 file`, while symbolic mode adjusts one class at a time with `u`, `g`, `o`, or `a` combined with `+`, `-`, or `=`. `chmod g+w,o-r file` adds group write and removes other read while leaving everything else untouched.

**What does `chown` change?** `chown user file` changes the owner, `chown :group file` changes only the group, and `chown user:group file` changes both at once. Changing ownership normally requires root or `sudo`, which is why day-to-day fixes tend to be `chown` plus a `chmod` correction.

## Processes and services

**What is a process?** A process is a running program with its own memory and process ID (PID), started as a child of another process except for the first one. PID 1 is the init system, which is `systemd` on most current mainstream distributions.

**How do I list processes with `ps`?** `ps aux` uses BSD-style options to show every process with user, CPU, and memory columns, while `ps -ef` shows the same idea in POSIX style with full command lines. `ps -u user` filters by owner, and piping any of these into `grep` narrows the list to one program.

**What is `top` for?** `top` shows a live view of running processes with CPU and memory usage plus the load average, refreshed every few seconds. Inside it, `q` quits, `k` prompts for a PID to kill, and `M` sorts by memory usage.

**Which signals should I actually remember?** SIGTERM (15) asks a process to terminate cleanly, SIGKILL (9) forces it to stop without cleanup and cannot be caught, SIGHUP (1) historically meant hang-up and now commonly asks daemons to reload, and SIGINT (2) is what `Ctrl+C` sends. The safe habit is `kill PID` or `kill -15` first and `kill -9` only when the process refuses to exit.

**How do I manage a service with `systemctl`?** `start`, `stop`, `restart`, and `status` control or inspect a service right now, while `enable` and `disable` control whether it starts at boot. `journalctl -u name.service` then shows that service's logs, which is usually the next step after a failed restart.

## Shell, pipes, and text search

**How do I search text with `grep`?** `grep -r` searches recursively through directories, `-i` ignores case, `-n` prints line numbers, and `-v` inverts the match to show lines that do not contain the pattern. The pattern itself is a regular expression, so quoting it keeps the shell from expanding characters first.

**How do pipes and redirects fit together?** `|` sends one command's output into the next command's input, `>` writes output to a file by truncating it, `>>` appends instead, and `<` feeds a file as input. `2>` redirects error output, `&>` redirects output and errors together in Bash, and `2>&1` merges errors into the standard output stream so both travel through the same pipe or file.

**How do I find files with `find`?** `-name` matches by filename pattern, `-type f` limits results to regular files, `-mtime -7` limits to files modified in the last seven days, and `-size +100M` limits to files larger than 100 MB. `-delete` removes matches directly, so I always run the same command without it first to see what would be deleted.

## Storage and archives

**How do I pack and unpack with `tar`?** `tar -czf archive.tar.gz dir/` creates a gzip-compressed archive, `tar -xzf archive.tar.gz` extracts one, and `tar -tzf archive.tar.gz` lists the contents without extracting. Adding `v`, as in `-czvf`, only makes the operation verbose.

**What is the difference between `df` and `du`?** `df` reports free and used space per mounted filesystem, which answers "which disk is full", while `du` estimates space used by files and directories, which answers "which folder is big". Both accept `-h` for human-readable sizes, and `du -sh dir` gives a single total for one path.

## Remote access and environment

**How do I connect and set up SSH keys?** `ssh user@host` opens a remote shell, defaulting to port 22 unless the server or client config changes it. `ssh-keygen` creates a key pair, `ssh-copy-id user@host` installs the public key on the server, and entries in `~/.ssh/config` save per-host names, users, keys, and ports.

**How do environment variables work?** `env` lists the current variables, `echo $VAR` prints one value, and `export VAR=value` sets one for the current shell and its children. `~/.bashrc` is where interactive Bash shells pick up repeated settings, and the ones I touch most are `PATH`, `HOME`, `USER`, and `SHELL`.

## Scheduling, packages, logs, and links

**How do I read a `cron` entry?** `crontab -e` edits the current user's schedule and `crontab -l` lists it. Each line has five time fields — minute, hour, day of month, month, and day of week — followed by the command, with shorthands such as `@reboot`, `@daily`, and `@weekly` available for common cases.

**Which package manager do I use where?** Debian and Ubuntu use `apt`, Fedora and current Red Hat systems use `dnf` with `yum` kept as a compatibility alias, and all of them resolve dependencies automatically. `snap` and `flatpak` sit alongside these as distribution-independent formats with stronger application sandboxing.

**Where do I look when something breaks?** Plain text logs live under `/var/log`, with exact filenames varying by distribution — for example `syslog` and `auth.log` on Debian-family systems versus `messages` and `secure` on Red Hat-family ones. On `systemd` systems `journalctl` queries the journal instead, and `tail -f` follows a growing file in real time.

**What is the difference between a symlink and a hard link?** `ln -s target link` creates a symbolic link, a small pointer to another path that can cross filesystems but breaks when the target moves. `ln target link` creates a hard link, a second name for the same inode on the same filesystem that keeps working until every name is removed.

## What this changed

This round showed me which basics I can explain and which ones I only recognise. Going forward I am keeping three small habits:

- Re-reading permission and redirect forms before pasting them from memory.
- Checking `systemctl status` plus `journalctl -u` before assuming a config edit failed.
- Using `find` with a dry run first whenever `-delete` is involved.

These notes revise the [Linux Fundamentals flashcards from devops-daily](https://devops-daily.com/flashcards/linux-fundamentals); the answers above are rewritten in my own words.
