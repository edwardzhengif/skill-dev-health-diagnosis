---
name: dev-health-diagnosis
description: Diagnose local development slowdowns and failures across macOS/Linux IDEs, coding agents, terminals, shell startup, hooks, Git, ports, dev servers, Node package managers, project indexing, proxies, and file-system bloat. Use when users mention Codex, Cursor, Claude Code, Trae, Gemini, Antigravity, VS Code, JetBrains, bash/zsh timeouts, slow commands, slow git status, slow npm/pnpm/yarn/bun, localhost not opening, port conflicts, dev server hangs, IDE indexing slowness, or wanting a safe local development health check.
---

# Dev Health Diagnosis

## Purpose

Diagnose why a local development environment feels slow or broken. Focus on the shared underlying chain used by IDEs and coding agents: shell startup, hooks, Git, ports, dev servers, package managers, project size, proxies, file watchers, and local processes.

Do not assume the IDE or agent is the root cause. First prove whether the slowdown comes from shell/config, command body, Git, project files, network/proxy, dev server, or system load.

## Safety Rules

- Stay read-only unless the user explicitly asks for a fix.
- Never delete hooks, edit shell configs, kill processes, or clear caches without separate confirmation.
- Treat shell config files as sensitive. When summarizing `.zshrc`, `.bashrc`, `.zprofile`, or `.bash_profile`, report keywords and line numbers, not full lines that may contain secrets.
- Prefer bounded probes. Avoid recursive scans of the whole home directory.
- If a command requires elevated privileges or could be destructive, stop and ask.

## Workflow

### 1. Classify the symptom

Map the user report to one or more buckets:

- **Shell startup**: new terminal slow, `bash`/`zsh` timeout, agent command startup slow.
- **Command body**: one command slow but clean shell startup is fast.
- **Git**: `git status`, prompt, commit, push, checkout, pre-commit slow.
- **Dev server**: localhost unavailable, HMR slow, repeated compile/restart.
- **Ports/processes**: port already in use, old server responding.
- **Node/package manager**: install/dev/build slow, mixed lockfiles, postinstall.
- **Project indexing**: IDE/agent slow after opening a project, huge generated folders.
- **Proxy/network**: install, git clone, API calls, AI tools hang.
- **System pressure**: CPU, memory, disk, Docker, many node/python processes.

### 2. Run the smallest safe checks first

If shell access is available, run the bundled read-only probe:

```bash
bash <skill-folder>/scripts/dev-health-probe.sh "$PWD"
```

Resolve `<skill-folder>` to the installed skill directory. If the script path is unknown, find the skill folder first and pass the current project path:

```bash
bash <skill-folder>/scripts/dev-health-probe.sh "$PWD"
```

If the script is unavailable, manually run the checks in `references/diagnostic-playbook.md`.

Probe options:

```bash
# Machine-readable output for tools or dashboards
bash <skill-folder>/scripts/dev-health-probe.sh "$PWD" --json

# Maximum privacy mode: do not inspect home shell config files
bash <skill-folder>/scripts/dev-health-probe.sh "$PWD" --no-home-config

# Check custom dev server ports
bash <skill-folder>/scripts/dev-health-probe.sh "$PWD" --ports 3000,3001,5173,8787
```

Use `--no-home-config` when the user is concerned about privacy or when you only need project-level checks. The probe never prints shell config contents or proxy values; it only reports keyword hits and variable names.

### 3. Compare normal shell vs clean shell

This is the highest-value test for agent/IDE command slowness:

```bash
time zsh -lc 'exit'
time zsh -f -lc 'exit'
time bash -lc 'exit'
time bash --noprofile --norc -lc 'exit'
```

Interpretation:

- Normal shell slow, clean shell fast: shell config, hook, prompt, env manager, or plugin is likely.
- Both slow: look at system pressure, disk, permissions, security software, or command body.
- Only zsh slow: inspect `.zshrc`, `.zprofile`, prompt/theme/plugins.
- Only bash slow: inspect `.bashrc`, `.bash_profile`.

Use thresholds:

- `<300ms`: healthy
- `300ms-1s`: mildly slow
- `1s-3s`: slow
- `>3s`: critical for coding agents that spawn many shells

### 4. Inspect likely slow sources

Load `references/diagnostic-playbook.md` when you need detailed command variants, thresholds, or remediation patterns.

Check these areas in order:

1. Shell config keywords: `nvm`, `pyenv`, `conda`, `asdf`, `direnv`, `starship`, `oh-my-zsh`, `powerlevel10k`, `brew shellenv`, `git status`, `git fetch`, `curl`, `wget`.
2. Git hooks: `.git/hooks/pre-commit`, `commit-msg`, `pre-push`, `post-checkout`, `post-merge`.
3. Git repository health: `git status` latency, untracked file count, `.git` size.
4. Ports: 3000, 3001, 5173, 8000, 8080, and ports mentioned by the user.
5. Project bloat: `node_modules`, `.next`, `dist`, `build`, `coverage`, `.cache`, `logs`, `tmp`, large binaries, SQLite files.
6. Node/package manager state: mixed lockfiles, `postinstall`, mismatched Node version.
7. Network/proxy: `HTTP_PROXY`, `HTTPS_PROXY`, npm/pnpm registry, git proxy.
8. Process pressure: many `node`, `python`, `tsserver`, `eslint`, Docker, or lingering dev servers.

### 5. Produce a diagnosis, not just logs

Every answer should include:

- **Conclusion**: the most likely root cause.
- **Evidence**: command timings or specific findings.
- **Plain-language explanation**: explain what it means for a beginner.
- **Safe next step**: what to test or change next.
- **Risk note**: if a fix touches config, hooks, ports, caches, or processes.

Good conclusion format:

```text
结论：更像是 shell 启动配置拖慢，不是 Claude Code/Codex/Cursor 本身慢。

证据：
- zsh 普通启动 2.4s
- zsh 干净启动 0.05s
- .zshrc 命中 nvm、conda、starship

大白话：
智能体每次执行命令都要先叫 zsh 起床。zsh 自己先卡 2 秒，所以所有命令看起来都慢。

下一步：
先用干净 shell 复测慢命令，再考虑把 nvm/conda 改成懒加载。不要直接删除配置。
```

## Tool/IDE Specific Notes

- **Codex / Claude Code / Gemini CLI**: shell startup latency and command timeouts are often the first suspect.
- **Cursor / Trae / Antigravity / VS Code / JetBrains**: also inspect indexing, excluded folders, extension processes, TypeScript server, ESLint, and formatter-on-save.
- **Any IDE or agent**: generated folders and huge files should be excluded from indexing and agent context.

## Reporting Template

Use this structure for final responses:

```text
【结论】
一句话说明最可能的原因。

【证据】
列出关键耗时、命中项、端口/项目/Git 发现。

【大白话解释】
用生活类比说明为什么这会拖慢 IDE/智能体/终端。

【安全处理顺序】
1. 先复测
2. 再临时绕过
3. 最后备份后修改

【不建议直接做的事】
说明不要直接删 hook、删配置、kill 进程或清缓存的原因。
```

## When to Use References

- Read `references/diagnostic-playbook.md` for detailed checks, thresholds, command alternatives, and remediation guidance.
- Use `scripts/dev-health-probe.sh` for a fast read-only snapshot when shell access is available.
- Prefer `--json` when another tool, dashboard, or later analysis step will consume the result.
