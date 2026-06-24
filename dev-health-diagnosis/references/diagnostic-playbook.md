# Dev Health Diagnostic Playbook

## Scope

Use this reference when diagnosing local development slowness for IDEs, coding agents, terminals, shell commands, Git, dev servers, package managers, ports, and project indexing.

The workflow is read-only by default. Fixes should be proposed, not applied, unless the user explicitly confirms.

## Probe Script Options

The bundled probe supports:

```bash
bash <skill-folder>/scripts/dev-health-probe.sh "$PWD"
bash <skill-folder>/scripts/dev-health-probe.sh "$PWD" --json
bash <skill-folder>/scripts/dev-health-probe.sh "$PWD" --no-home-config
bash <skill-folder>/scripts/dev-health-probe.sh "$PWD" --ports 3000,3001,5173,8787
```

Use `--json` when the output will be consumed by another tool or dashboard.

Use `--no-home-config` when privacy is more important than shell startup attribution. This skips reading `.zshrc`, `.zprofile`, `.bashrc`, and `.bash_profile`.

Use `--ports` when the project uses non-default ports, such as Astro, Remix, Cloudflare Workers, Rails, Django, or custom API servers.

## Diagnostic Decision Matrix

| Symptom | First Checks | Likely Cause | Safe Next Step |
| --- | --- | --- | --- |
| Agent command times out | normal vs clean shell timing | `.zshrc`, `.bashrc`, prompt, env manager | rerun with clean shell |
| New terminal opens slowly | shell startup timing | shell config or plugin | inspect config keywords |
| `git status` slow | time `git status --porcelain` | untracked files, large repo, prompt Git module | inspect `.gitignore`, prompt |
| Commit/push slow | list `.git/hooks` | pre-commit/pre-push hook | inspect hook script, do not delete |
| localhost unavailable | `lsof` port check, HTTP check | old process, wrong port, crashed server | identify PID and command |
| `npm install` slow | registry/proxy/lockfiles/postinstall | network or package scripts | inspect registry and scripts |
| IDE indexing slow | largest dirs/files, ignore files | generated folders indexed | add ignore/exclude suggestions |
| Save file slow | formatter/linter/tsserver processes | too many save hooks | inspect IDE tasks/extensions |
| Dev server HMR slow | project size, watcher scope | watching generated folders | exclude build/cache folders |

## Shell Startup Checks

Run:

```bash
time zsh -lc 'exit'
time zsh -f -lc 'exit'
time bash -lc 'exit'
time bash --noprofile --norc -lc 'exit'
```

Thresholds:

| Duration | Meaning |
| --- | --- |
| `<300ms` | Healthy |
| `300ms-1s` | Mildly slow |
| `1s-3s` | Slow |
| `>3s` | Critical |

Interpretation:

- Normal shell slow, clean shell fast: shell startup config is the likely bottleneck.
- Normal and clean shell both slow: look outside config, such as system pressure or security software.
- zsh slow only: inspect zsh config and prompt.
- bash slow only: inspect bash config.

Common slow shell config sources:

- Environment managers: `nvm`, `pyenv`, `conda`, `rbenv`, `asdf`.
- Directory hooks: `direnv`.
- Prompt themes: `starship`, `powerlevel10k`, `oh-my-zsh` themes.
- Network calls: `curl`, `wget`, `git fetch`, package update checks.
- Git prompt modules that call `git status` in large repos.

Recommended remediation order:

1. Reproduce with clean shell.
2. Temporarily disable half the config by commenting a copy, not editing blindly.
3. Move expensive tools to lazy loading.
4. Remove network calls from startup.
5. Set prompt module timeouts.

## Git Checks

Commands:

```bash
time git status --porcelain
find .git/hooks -maxdepth 1 -type f -perm -111 -print
du -sh .git
```

Look for:

- Executable hooks: `pre-commit`, `commit-msg`, `pre-push`, `post-checkout`, `post-merge`.
- Too many untracked files.
- Generated folders not ignored.
- Large `.git` directory.

Guidance:

- Do not delete hooks automatically.
- Explain what each hook does if readable.
- Suggest temporarily bypassing only when safe and user understands project policy.
- For prompt-related Git slowness, suggest disabling Git status prompt module or setting a timeout.

## Port and Dev Server Checks

Common ports:

- 3000: Next.js, React apps
- 3001: alternate app server
- 5173: Vite
- 8000: Python/Docs/API
- 8080: general web server

Also check user-provided ports. Cloudflare Workers often use 8787; Rails, Next.js, and React apps often use 3000; Django commonly uses 8000.

macOS/Linux:

```bash
lsof -iTCP:3000 -sTCP:LISTEN -n -P
lsof -iTCP:5173 -sTCP:LISTEN -n -P
```

HTTP health:

```bash
curl -I --max-time 3 http://localhost:3000
curl -I --max-time 3 http://localhost:5173
```

Interpretation:

- Port occupied by old process: the app may be starting on a different port or hitting stale output.
- Port open but HTTP fails: server may be hung or not HTTP.
- HTTP slow: inspect build output, server logs, watcher scope, CPU.

Do not kill processes without user confirmation. Killing a dev server is usually safe, but still ask because it can interrupt work.

## Project Size and Indexing Checks

Inspect top-level size:

```bash
du -sh ./* ./.??* 2>/dev/null | sort -h | tail -20
```

Look for:

- `node_modules`
- `.next`
- `dist`
- `build`
- `coverage`
- `.cache`
- `logs`
- `tmp`
- `.turbo`
- `.parcel-cache`
- large `.sqlite`, `.db`, `.mp4`, `.zip`, `.tar`, `.log`

IDE/Agent guidance:

- Generated folders should be in `.gitignore`.
- Cursor may need `.cursorignore`.
- Codex may need `.codexignore` or workspace exclusions depending on environment.
- VS Code can exclude folders through `files.exclude` and `search.exclude`.
- JetBrains can mark directories as excluded.
- Agents should avoid reading build outputs, dependency folders, caches, logs, and large binary assets unless directly relevant.

## Node and Package Manager Checks

Files:

- `package.json`
- `package-lock.json`
- `pnpm-lock.yaml`
- `yarn.lock`
- `bun.lockb`
- `.nvmrc`
- `.node-version`

Risk signals:

- Multiple lockfiles in one app.
- `postinstall`, `prepare`, or custom install scripts.
- Node version mismatch.
- Very large monorepo without workspace-aware commands.
- Slow registry/proxy.

Commands:

```bash
node -v
npm -v
pnpm -v
yarn -v
bun -v
npm config get registry
pnpm config get registry
```

Do not run install/build/test unless the user asks; those can modify files, download packages, or take a long time.

## Proxy and Network Checks

Check only variable names and non-sensitive hostnames when reporting:

```bash
env | grep -Ei '^(HTTP_PROXY|HTTPS_PROXY|ALL_PROXY|NO_PROXY|npm_config_registry)='
git config --get http.proxy
git config --get https.proxy
```

Be careful:

- Proxy URLs may contain credentials.
- Redact usernames, passwords, and tokens.
- Network commands may require internet access and can fail in sandboxed environments.

## Process Pressure Checks

Useful read-only checks:

```bash
ps aux | sort -nrk 3 | head -15
ps aux | sort -nrk 4 | head -15
pgrep -fl 'node|npm|pnpm|yarn|vite|next|tsserver|eslint|python|docker'
```

Interpretation:

- Many Node processes can mean leftover dev servers.
- `tsserver` and `eslint` can make IDEs feel slow.
- Docker Desktop can consume CPU/memory and disk.

Do not kill processes automatically.

## Remediation Patterns

Safe first steps:

1. Re-run the slow command in a clean shell.
2. Run the slow command outside the IDE/agent in a normal terminal.
3. Check if only one project is slow.
4. Check if only Git repositories are slow.
5. Check port occupancy before restarting servers.
6. Add ignore suggestions before changing configs.

Common fix suggestions:

- Lazy-load `nvm`, `pyenv`, `conda`, or `asdf`.
- Remove network calls from shell startup.
- Add generated folders to `.gitignore` and IDE/agent ignore files.
- Disable expensive prompt modules in large repos.
- Resolve mixed lockfiles.
- Stop old dev servers after confirmation.
- Set explicit dev server port.
- Avoid running heavy lint/typecheck on every save for large projects.

Unsafe or confirmation-required actions:

- Editing shell config files.
- Deleting Git hooks.
- Killing processes.
- Clearing caches.
- Removing `node_modules`.
- Changing global proxy or registry.
- Modifying package manager lockfiles.

## Reporting Examples

Shell config bottleneck:

```text
结论：更像是 shell 启动配置拖慢，不是 IDE 或智能体本身慢。

证据：zsh 普通启动 2.4s，zsh 干净启动 0.05s，配置命中 nvm/conda/starship。

大白话：每次智能体执行命令，都要先让 zsh 开门。现在 zsh 开门前做了太多检查，所以所有命令都像被拖慢。

下一步：先用干净 shell 复测慢命令。确认后再备份配置，把 nvm/conda 改成懒加载。
```

Port conflict:

```text
结论：dev server 可能没坏，是端口已经被旧进程占用。

证据：3000 端口已有 node 进程监听，当前项目启动可能切到了其他端口。

大白话：你以为打开的是新项目，其实浏览器可能连到旧服务。

下一步：确认这个 PID 是否可以停止，再重启 dev server。
```

Project indexing:

```text
结论：项目索引慢更像是大目录和生成文件被 IDE/智能体扫描。

证据：.next、dist、coverage、logs 目录体积较大，未发现对应 ignore 文件。

大白话：智能体像在读一本书，但它把草稿纸、复印件、缓存和垃圾桶也一起读了。

下一步：把生成目录加入 .gitignore 和对应 IDE/agent 的排除配置。
```
