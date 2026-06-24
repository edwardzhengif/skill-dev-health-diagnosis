# Dev Health Diagnosis

[中文](README.md) | [English](README.en.md)

A Codex skill for diagnosing local development slowdowns across IDEs, coding agents, shells, Git, ports, dev servers, package managers, project indexing, proxies, and developer processes.

It is designed for reports like:

- "Codex commands are timing out."
- "Cursor terminal is slow."
- "Claude Code / Gemini CLI hangs when running bash."
- "Trae / Antigravity / VS Code / JetBrains indexing feels slow."
- "`git status` is slow."
- "`npm run dev` starts slowly."
- "localhost is not opening."
- "A dev server port is already in use."

## What It Checks

- bash/zsh startup time
- shell config keyword hits without printing config contents
- Git status latency and executable Git hooks
- common or custom local ports
- top-level project size
- Node package manager state
- proxy environment variable names without values
- developer process summaries when process listing is available

## Safety

This skill is read-only by default.

It does not:

- edit `.zshrc`, `.bashrc`, or other shell config files
- delete Git hooks
- kill processes
- clear caches
- remove `node_modules`
- upload data
- print shell config contents
- print proxy values

## Install

Copy the skill folder into your Codex skills directory:

```bash
cp -R dev-health-diagnosis ~/.codex/skills/
```

Then start a new Codex session so the skill can be discovered.

## Use

Ask Codex:

```text
Use $dev-health-diagnosis to diagnose why my IDE, coding agent, shell commands, Git, or dev server feels slow.
```

## Optional Probe

Run the bundled read-only probe from a project directory:

```bash
bash ~/.codex/skills/dev-health-diagnosis/scripts/dev-health-probe.sh "$PWD"
```

Machine-readable output:

```bash
bash ~/.codex/skills/dev-health-diagnosis/scripts/dev-health-probe.sh "$PWD" --json
```

Privacy mode that skips home shell config inspection:

```bash
bash ~/.codex/skills/dev-health-diagnosis/scripts/dev-health-probe.sh "$PWD" --no-home-config
```

Custom ports:

```bash
bash ~/.codex/skills/dev-health-diagnosis/scripts/dev-health-probe.sh "$PWD" --ports 3000,5173,8787
```

## Output Philosophy

The skill should produce a diagnosis, not just logs:

- conclusion
- evidence
- plain-language explanation
- safe next step
- risk note

## License

MIT
