# Dev Health Diagnosis

[English](README.md) | [中文](README.zh-CN.md)

一个用于诊断本地开发环境卡顿的 Codex Skill。它覆盖 IDE、AI 编程智能体、shell、Git、端口、dev server、包管理器、项目索引、代理和开发相关进程。

它适合这些情况：

- “Codex 执行命令总是超时。”
- “Cursor 终端很慢。”
- “Claude Code / Gemini CLI 运行 bash 时卡住。”
- “Trae / Antigravity / VS Code / JetBrains 索引很慢。”
- “`git status` 很慢。”
- “`npm run dev` 启动很慢。”
- “localhost 打不开。”
- “dev server 端口被占用。”

## 它会检查什么

- bash/zsh 启动耗时
- shell 配置里的可疑关键词，但不会打印配置内容
- Git status 耗时和可执行 Git hooks
- 常见端口或自定义端口
- 项目顶层目录体积
- Node 包管理器状态
- 代理环境变量名称，但不会打印变量值
- 在系统允许时输出开发相关进程摘要

## 安全性

这个 skill 默认只读。

它不会：

- 修改 `.zshrc`、`.bashrc` 或其他 shell 配置
- 删除 Git hooks
- kill 进程
- 清理缓存
- 删除 `node_modules`
- 上传数据
- 打印 shell 配置内容
- 打印代理变量值

## 安装

把 skill 文件夹复制到 Codex skills 目录：

```bash
cp -R dev-health-diagnosis ~/.codex/skills/
```

然后开启一个新的 Codex 会话，让 Codex 重新发现这个 skill。

## 使用

可以这样问 Codex：

```text
Use $dev-health-diagnosis to diagnose why my IDE, coding agent, shell commands, Git, or dev server feels slow.
```

中文也可以这样说：

```text
使用 $dev-health-diagnosis 帮我诊断为什么 IDE、智能体、shell 命令、Git 或 dev server 很慢。
```

## 可选诊断脚本

在项目目录里运行内置只读诊断脚本：

```bash
bash ~/.codex/skills/dev-health-diagnosis/scripts/dev-health-probe.sh "$PWD"
```

输出机器可读 JSON：

```bash
bash ~/.codex/skills/dev-health-diagnosis/scripts/dev-health-probe.sh "$PWD" --json
```

隐私模式：跳过 home 目录里的 shell 配置检查：

```bash
bash ~/.codex/skills/dev-health-diagnosis/scripts/dev-health-probe.sh "$PWD" --no-home-config
```

自定义端口：

```bash
bash ~/.codex/skills/dev-health-diagnosis/scripts/dev-health-probe.sh "$PWD" --ports 3000,5173,8787
```

## 输出原则

这个 skill 应该输出诊断结论，而不是只贴日志。

它应该包含：

- 结论
- 证据
- 大白话解释
- 安全的下一步
- 风险提示

## License

MIT
