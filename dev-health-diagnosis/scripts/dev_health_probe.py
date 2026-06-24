#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path


SHELL_KEYWORDS = re.compile(
    r"nvm|pyenv|conda|rbenv|asdf|direnv|starship|powerlevel10k|oh-my-zsh|brew shellenv|git status|git fetch|curl|wget|npm|pnpm|yarn|bun",
    re.IGNORECASE,
)

DEFAULT_PORTS = [3000, 3001, 5173, 8000, 8080]
DEV_PROCESS_RE = re.compile(r"node|npm|pnpm|yarn|vite|next|tsserver|eslint|python|docker", re.IGNORECASE)
PROXY_ENV_RE = re.compile(r"^(HTTP_PROXY|HTTPS_PROXY|ALL_PROXY|NO_PROXY|npm_config_registry)$", re.IGNORECASE)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def run_timed(label: str, cmd: list[str], timeout: float = 10.0) -> dict:
    start = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
            check=False,
        )
        status = proc.returncode
        timed_out = False
    except subprocess.TimeoutExpired:
        status = None
        timed_out = True
    except FileNotFoundError:
        status = None
        timed_out = False

    duration_ms = int((time.perf_counter() - start) * 1000)
    return {
        "label": label,
        "command": cmd[:2],
        "duration_ms": duration_ms,
        "status": status,
        "timed_out": timed_out,
    }


def human_path(path: Path) -> str:
    home = Path.home()
    try:
        return "~/" + str(path.expanduser().resolve().relative_to(home))
    except Exception:
        return str(path)


def shell_startup() -> list[dict]:
    results = []
    if command_exists("zsh"):
        results.append(run_timed("zsh normal", ["zsh", "-lc", "exit"]))
        results.append(run_timed("zsh clean", ["zsh", "-f", "-lc", "exit"]))
    else:
        results.append({"label": "zsh", "available": False})

    if command_exists("bash"):
        results.append(run_timed("bash normal", ["bash", "-lc", "exit"]))
        results.append(run_timed("bash clean", ["bash", "--noprofile", "--norc", "-lc", "exit"]))
    else:
        results.append({"label": "bash", "available": False})
    return results


def shell_config_hits(skip_home_config: bool) -> list[dict]:
    if skip_home_config:
        return []

    hits = []
    for name in [".zshrc", ".zprofile", ".bashrc", ".bash_profile"]:
        path = Path.home() / name
        if not path.is_file():
            continue
        file_hits = []
        try:
            with path.open("r", encoding="utf-8", errors="replace") as handle:
                for idx, line in enumerate(handle, start=1):
                    if SHELL_KEYWORDS.search(line):
                        file_hits.append({"line": idx, "kind": "keyword_hit"})
        except OSError:
            file_hits.append({"line": None, "kind": "unreadable"})
        hits.append({"file": human_path(path), "hits": file_hits})
    return hits


def dir_size_human(path: Path) -> str | None:
    if not path.exists():
        return None
    if command_exists("du"):
        try:
            out = subprocess.check_output(["du", "-sh", str(path)], stderr=subprocess.DEVNULL, text=True)
            return out.split()[0]
        except Exception:
            return None
    return None


def git_info(project: Path) -> dict:
    git_dir = project / ".git"
    if not git_dir.exists():
        return {"present": False}

    hooks = []
    hooks_dir = git_dir / "hooks"
    if hooks_dir.is_dir():
        for item in sorted(hooks_dir.iterdir()):
            try:
                mode = item.stat().st_mode
            except OSError:
                continue
            if item.is_file() and (mode & stat.S_IXUSR):
                hooks.append(item.name)

    status = None
    if command_exists("git"):
        status = run_timed("git status --porcelain", ["git", "-C", str(project), "status", "--porcelain"])

    return {
        "present": True,
        "status": status,
        "executable_hooks": hooks,
        "git_size": dir_size_human(git_dir),
    }


def parse_ports(raw: str | None) -> list[int]:
    if not raw:
        return DEFAULT_PORTS
    ports = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            value = int(part)
        except ValueError:
            continue
        if 1 <= value <= 65535:
            ports.append(value)
    return ports or DEFAULT_PORTS


def port_info(ports: list[int]) -> list[dict]:
    results = []
    for port in ports:
        record = {"port": port, "status": "unknown", "process": None}
        if not command_exists("lsof"):
            record["status"] = "lsof_unavailable"
            results.append(record)
            continue
        try:
            out = subprocess.check_output(
                ["lsof", f"-iTCP:{port}", "-sTCP:LISTEN", "-n", "-P"],
                stderr=subprocess.DEVNULL,
                text=True,
            )
            lines = [line for line in out.splitlines() if line.strip()]
            if len(lines) > 1:
                cols = lines[1].split()
                record["status"] = "occupied"
                record["process"] = {
                    "command": cols[0] if len(cols) > 0 else None,
                    "pid": cols[1] if len(cols) > 1 else None,
                }
            else:
                record["status"] = "free"
        except subprocess.CalledProcessError:
            record["status"] = "free"
        except Exception:
            record["status"] = "unavailable"
        results.append(record)
    return results


def top_level_sizes(project: Path) -> list[dict]:
    if not project.is_dir() or not command_exists("du"):
        return []
    entries = []
    try:
        children = list(project.iterdir())
    except OSError:
        return []
    for child in children:
        if child.name in {".", ".."}:
            continue
        try:
            out = subprocess.check_output(["du", "-sh", str(child)], stderr=subprocess.DEVNULL, text=True)
            size = out.split()[0]
            entries.append({"path": child.name, "size": size})
        except Exception:
            continue
    return entries[-20:]


def node_state(project: Path) -> dict:
    package_json = project / "package.json"
    state = {"package_json": package_json.is_file(), "lockfiles": [], "versions": {}}
    for lock in ["package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lockb"]:
        if (project / lock).is_file():
            state["lockfiles"].append(lock)
    for tool in ["node", "npm", "pnpm", "yarn", "bun"]:
        if command_exists(tool):
            try:
                out = subprocess.check_output([tool, "-v"], stderr=subprocess.DEVNULL, text=True, timeout=3)
                state["versions"][tool] = out.strip()
            except Exception:
                state["versions"][tool] = "unavailable"
    return state


def proxy_env_names() -> list[str]:
    names = []
    for key in os.environ:
        if PROXY_ENV_RE.match(key):
            names.append(key)
    return sorted(names)


def developer_processes() -> list[dict]:
    if not command_exists("ps"):
        return []
    commands = [
        ["ps", "-axo", "pid=,pcpu=,pmem=,comm="],
        ["ps", "-Ao", "pid,pcpu,pmem,comm"],
    ]
    out = None
    for cmd in commands:
        try:
            out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True, timeout=3)
            break
        except Exception:
            continue
    if out is None:
        return []
    rows = []
    for line in out.splitlines():
        if not DEV_PROCESS_RE.search(line):
            continue
        cols = line.split(None, 3)
        if len(cols) < 4:
            continue
        rows.append({"pid": cols[0], "cpu": cols[1], "mem": cols[2], "command": Path(cols[3]).name})
        if len(rows) >= 20:
            break
    return rows


def collect(args: argparse.Namespace) -> dict:
    project = Path(args.project).expanduser().resolve()
    return {
        "tool": "dev-health-probe",
        "generated_at": now_iso(),
        "mode": "read-only",
        "project": str(project),
        "options": {
            "no_home_config": args.no_home_config,
            "ports": args.ports_list,
        },
        "shell_startup": shell_startup(),
        "shell_config_hits": shell_config_hits(args.no_home_config),
        "git": git_info(project),
        "ports": port_info(args.ports_list),
        "project_top_level_sizes": top_level_sizes(project),
        "node": node_state(project),
        "proxy_env_names": proxy_env_names(),
        "developer_processes": developer_processes(),
        "notes": [
            "This probe is read-only.",
            "Proxy values and shell config contents are redacted by design.",
            "Keyword hits are leads, not proof.",
        ],
    }


def print_section(title: str) -> None:
    print(f"\n## {title}")


def print_text(data: dict) -> None:
    print("# Dev Health Probe")
    print(f"Project: {data['project']}")
    print(f"Generated: {data['generated_at']}")
    print("Mode: read-only")

    print_section("Shell Startup")
    for item in data["shell_startup"]:
        if item.get("available") is False:
            print(f"{item['label']}: not found")
            continue
        suffix = " timed_out=true" if item.get("timed_out") else ""
        print(f"{item['label']}: {item['duration_ms']}ms status={item['status']}{suffix}")

    print_section("Shell Config Keyword Hits")
    if data["options"]["no_home_config"]:
        print("skipped by --no-home-config")
    elif not data["shell_config_hits"]:
        print("no config files or keyword hits found")
    else:
        for file_record in data["shell_config_hits"]:
            print(file_record["file"])
            if not file_record["hits"]:
                print("  no keyword hits")
            for hit in file_record["hits"]:
                if hit["line"] is None:
                    print("  unreadable")
                else:
                    print(f"  line {hit['line']}: {hit['kind']}")

    print_section("Git")
    git = data["git"]
    if not git["present"]:
        print("No .git directory at project root.")
    else:
        if git["status"]:
            status = git["status"]
            suffix = " timed_out=true" if status.get("timed_out") else ""
            print(f"git status --porcelain: {status['duration_ms']}ms status={status['status']}{suffix}")
        print("Executable hooks:")
        if git["executable_hooks"]:
            for hook in git["executable_hooks"]:
                print(f"  {hook}")
        else:
            print("  none")
        print(f".git size: {git['git_size'] or 'unknown'}")

    print_section("Ports")
    for item in data["ports"]:
        process = item.get("process")
        if process:
            print(f"port {item['port']}: {item['status']} {process.get('command')} pid={process.get('pid')}")
        else:
            print(f"port {item['port']}: {item['status']}")

    print_section("Project Size Top Level")
    if data["project_top_level_sizes"]:
        for item in data["project_top_level_sizes"]:
            print(f"{item['size']}\t{item['path']}")
    else:
        print("unavailable")

    print_section("Node Package State")
    node = data["node"]
    print(f"package.json: {'present' if node['package_json'] else 'not found at project root'}")
    for lock in node["lockfiles"]:
        print(f"{lock}: present")
    for tool, version in node["versions"].items():
        print(f"{tool}: {version}")

    print_section("Proxy Environment Names")
    if data["proxy_env_names"]:
        for name in data["proxy_env_names"]:
            print(f"{name}=REDACTED")
    else:
        print("none")

    print_section("Developer Processes")
    if data["developer_processes"]:
        for item in data["developer_processes"]:
            print(f"{item['pid']} cpu={item['cpu']} mem={item['mem']} command={item['command']}")
    else:
        print("process summary unavailable")

    print_section("Notes")
    for note in data["notes"]:
        print(note)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only local development health probe.")
    parser.add_argument("project", nargs="?", default=".", help="Project path to inspect.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument("--no-home-config", action="store_true", help="Do not read shell config files in $HOME.")
    parser.add_argument("--ports", default=None, help="Comma-separated ports to check. Default: 3000,3001,5173,8000,8080.")
    args = parser.parse_args()
    args.ports_list = parse_ports(args.ports)

    data = collect(args)
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print_text(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
