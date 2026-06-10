#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Onboarder Analyzer — глубокий локальный анализ кодовой базы.

Использование:
    python3 analyzer.py /path/to/repo [--output result.json]

Работает полностью офлайн. Нужен только Python 3.8+.
Git — опционально (для экспертов по модулям и истории изменений).
Результат — JSON в stdout (или в файл через --output).
"""

import json
import os
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict

MAX_FILE_BYTES = 512 * 1024
MAX_FILES_TO_SCAN = 20000

IGNORE_DIRS = {
    ".git", "node_modules", "vendor", "dist", "build", "out", "target",
    "__pycache__", ".venv", "venv", "env", ".idea", ".vscode", "coverage",
    ".next", ".nuxt", ".cache", "tmp", "logs",
}

LANG_BY_EXT = {
    ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript",
    ".py": "Python", ".rb": "Ruby", ".go": "Go", ".rs": "Rust",
    ".java": "Java", ".kt": "Kotlin", ".php": "PHP", ".cs": "C#",
    ".c": "C", ".h": "C", ".cpp": "C++", ".hpp": "C++",
    ".vue": "Vue", ".svelte": "Svelte", ".swift": "Swift",
    ".scss": "SCSS", ".css": "CSS", ".html": "HTML", ".sql": "SQL",
    ".sh": "Shell", ".yml": "YAML", ".yaml": "YAML", ".prisma": "Prisma",
}

STACK_MARKERS = [
    ("package.json", "Node.js"),
    ("tsconfig.json", "TypeScript"),
    ("requirements.txt", "Python (pip)"),
    ("pyproject.toml", "Python (pyproject)"),
    ("manage.py", "Django"),
    ("Gemfile", "Ruby (Bundler)"),
    ("config/routes.rb", "Ruby on Rails"),
    ("go.mod", "Go"),
    ("Cargo.toml", "Rust"),
    ("pom.xml", "Java (Maven)"),
    ("build.gradle", "Gradle"),
    ("build.gradle.kts", "Gradle"),
    ("composer.json", "PHP (Composer)"),
    ("Dockerfile", "Docker"),
    ("docker-compose.yml", "Docker Compose"),
    ("docker-compose.yaml", "Docker Compose"),
    (".gitlab-ci.yml", "GitLab CI"),
    ("Makefile", "Make"),
    ("prisma/schema.prisma", "Prisma"),
]

# (название, regex по имени файла, regex по коду, группа метода | None, группа пути)
API_PATTERNS = [
    ("Express", r"\.(js|ts|mjs)$",
     re.compile(r"(?:app|router|api)\.(get|post|put|delete|patch)\(\s*[\"'`]([^\"'`]+)"), 1, 2),
    ("Flask", r"\.py$",
     re.compile(r"@\w+\.route\(\s*[\"']([^\"']+)[\"']"), None, 1),
    ("FastAPI", r"\.py$",
     re.compile(r"@(?:app|router)\.(get|post|put|delete|patch)\(\s*[\"']([^\"']+)"), 1, 2),
    ("Django", r"urls\.py$",
     re.compile(r"\bpath\(\s*[\"']([^\"']+)[\"']"), None, 1),
    ("Spring", r"\.(java|kt)$",
     re.compile(r"@(Get|Post|Put|Delete|Patch)Mapping\(\s*(?:value\s*=\s*)?[\"']([^\"']+)"), 1, 2),
    ("Go router", r"\.go$",
     re.compile(r"\.(GET|POST|PUT|DELETE|PATCH)\(\s*\"([^\"]+)\""), 1, 2),
    ("Go net/http", r"\.go$",
     re.compile(r"HandleFunc\(\s*\"([^\"]+)\""), None, 1),
    ("Rails", r"routes\.rb$",
     re.compile(r"^\s*(get|post|put|delete|patch)\s+[\"']([^\"']+)", re.M), 1, 2),
]

DB_PATTERNS = [
    ("Django model", r"\.py$", re.compile(r"class\s+(\w+)\(.*models\.Model")),
    ("SQLAlchemy model", r"\.py$", re.compile(r"class\s+(\w+)\(.*(?:DeclarativeBase|Base|db\.Model)")),
    ("ActiveRecord model", r"app/models/.*\.rb$",
     re.compile(r"class\s+(\w+)\s*<\s*(?:ApplicationRecord|ActiveRecord::Base)")),
    ("Mongoose model", r"\.(js|ts)$", re.compile(r"mongoose\.model\(\s*[\"'](\w+)")),
    ("Prisma model", r"\.prisma$", re.compile(r"^model\s+(\w+)\s*\{", re.M)),
    ("SQL table", r"\.sql$",
     re.compile(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[\"'`]?(\w+)", re.I)),
]

MIGRATION_HINTS = ("migrations/", "db/migrate/", "alembic/")


def run_git(repo, args):
    """Запускает git и возвращает stdout либо пустую строку.

    Кодировка задана явно: git отдаёт UTF-8, а на Windows локаль по
    умолчанию (например cp1251) ломает декодирование имён коммитеров.
    """
    try:
        out = subprocess.run(
            ["git", "-C", repo] + args,
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=30,
        )
        if out.returncode == 0 and out.stdout is not None:
            return out.stdout
    except (OSError, subprocess.TimeoutExpired):
        pass
    return ""


def read_text(path):
    try:
        if os.path.getsize(path) > MAX_FILE_BYTES:
            return None
        with open(path, encoding="utf-8", errors="ignore") as fh:
            return fh.read()
    except OSError:
        return None


def walk_files(repo):
    files = []
    for root, dirs, names in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
        for name in names:
            rel = os.path.relpath(os.path.join(root, name), repo)
            files.append(rel.replace(os.sep, "/"))
            if len(files) >= MAX_FILES_TO_SCAN:
                return files
    return files


def scan_code(repo, files):
    """Один проход по исходникам: строки кода, карта API, модели БД."""
    lang_lines = Counter()
    api, models = [], []
    for rel in files:
        lang = LANG_BY_EXT.get(os.path.splitext(rel)[1].lower())
        if not lang:
            continue
        text = read_text(os.path.join(repo, rel))
        if text is None:
            continue
        lang_lines[lang] += text.count("\n") + 1
        for name, fpat, rx, mg, pg in API_PATTERNS:
            if len(api) >= 300 or not re.search(fpat, rel):
                continue
            for m in rx.finditer(text):
                method = m.group(mg).upper() if mg else "ANY"
                api.append({"framework": name, "method": method,
                            "path": m.group(pg), "file": rel})
        for kind, fpat, rx in DB_PATTERNS:
            if len(models) >= 300 or not re.search(fpat, rel):
                continue
            for m in rx.finditer(text):
                models.append({"kind": kind, "name": m.group(1), "file": rel})
    return lang_lines, api, models


def detect_stack(repo):
    stack, seen = [], set()
    for marker, label in STACK_MARKERS:
        if label not in seen and os.path.exists(os.path.join(repo, marker)):
            stack.append({"label": label, "marker": marker})
            seen.add(label)
    return stack


def detect_modules(repo, files):
    mod_files = Counter()
    mod_langs = defaultdict(Counter)
    for rel in files:
        mod = rel.split("/", 1)[0] if "/" in rel else "(корень)"
        mod_files[mod] += 1
        lang = LANG_BY_EXT.get(os.path.splitext(rel)[1].lower())
        if lang:
            mod_langs[mod][lang] += 1
    modules = []
    for mod, count in mod_files.most_common(12):
        top_lang = mod_langs[mod].most_common(1)
        experts = []
        if mod != "(корень)":
            out = run_git(repo, ["log", "--no-merges", "--pretty=%an",
                                 "-n", "300", "--", mod])
            for name, commits in Counter(
                    n for n in out.splitlines() if n.strip()).most_common(3):
                experts.append({"name": name, "commits": commits})
        modules.append({
            "name": mod,
            "files": count,
            "language": top_lang[0][0] if top_lang else "—",
            "experts": experts,
        })
    return modules


def detect_key_files(repo, files):
    """Самые часто меняемые файлы (churn); фолбэк — крупнейшие исходники."""
    fset = set(files)
    out = run_git(repo, ["log", "--no-merges", "--name-only",
                         "--pretty=format:", "-n", "1000"])
    counter = Counter(line.strip() for line in out.splitlines() if line.strip())
    ranked = [(p, n) for p, n in counter.most_common(50) if p in fset]
    if ranked:
        return [{"path": p, "changes": n} for p, n in ranked[:10]]
    sizes = []
    for rel in files:
        if os.path.splitext(rel)[1].lower() in LANG_BY_EXT:
            try:
                sizes.append((rel, os.path.getsize(os.path.join(repo, rel))))
            except OSError:
                pass
    sizes.sort(key=lambda x: -x[1])
    return [{"path": p, "changes": 0} for p, _ in sizes[:10]]


def detect_contributors(repo):
    out = run_git(repo, ["log", "--no-merges", "--pretty=%an", "-n", "2000"])
    return [{"name": name, "commits": commits}
            for name, commits in Counter(
                n for n in out.splitlines() if n.strip()).most_common(5)]


def detect_commands(repo, files):
    cmds = {"setup": [], "run": [], "test": [], "deploy": [], "other": []}
    fset = set(files)

    def add(cat, cmd, source):
        if all(c["cmd"] != cmd for c in cmds[cat]):
            cmds[cat].append({"cmd": cmd, "source": source})

    if "package.json" in fset:
        add("setup", "npm install", "package.json")
        try:
            pkg = json.loads(read_text(os.path.join(repo, "package.json")) or "{}")
        except json.JSONDecodeError:
            pkg = {}
        for name in (pkg.get("scripts") or {}):
            cmd, low = "npm run " + name, name.lower()
            if "test" in low or "lint" in low:
                add("test", cmd, "package.json")
            elif low in ("start", "serve") or "dev" in low:
                add("run", cmd, "package.json")
            elif "deploy" in low or "release" in low or "publish" in low:
                add("deploy", cmd, "package.json")
            else:
                add("other", cmd, "package.json")
    if "requirements.txt" in fset:
        add("setup", "pip install -r requirements.txt", "requirements.txt")
    if "pyproject.toml" in fset:
        add("setup", "pip install -e .", "pyproject.toml")
    if "manage.py" in fset:
        add("run", "python manage.py runserver", "manage.py")
        add("test", "python manage.py test", "manage.py")
    if "Gemfile" in fset:
        add("setup", "bundle install", "Gemfile")
    if "go.mod" in fset:
        add("setup", "go mod download", "go.mod")
        add("run", "go run .", "go.mod")
        add("test", "go test ./...", "go.mod")
    if "Cargo.toml" in fset:
        add("run", "cargo run", "Cargo.toml")
        add("test", "cargo test", "Cargo.toml")
    if "docker-compose.yml" in fset or "docker-compose.yaml" in fset:
        add("run", "docker compose up -d", "docker-compose")
    if "Makefile" in fset:
        text = read_text(os.path.join(repo, "Makefile")) or ""
        for m in re.finditer(r"^([A-Za-z0-9_.-]+):", text, re.M):
            target = m.group(1)
            if target.startswith("."):
                continue
            cmd, low = "make " + target, target.lower()
            if "test" in low or "lint" in low:
                add("test", cmd, "Makefile")
            elif low in ("run", "start", "serve", "up", "dev"):
                add("run", cmd, "Makefile")
            elif "deploy" in low or "release" in low:
                add("deploy", cmd, "Makefile")
            elif low in ("install", "setup", "deps", "bootstrap"):
                add("setup", cmd, "Makefile")
            else:
                add("other", cmd, "Makefile")
    if ".gitlab-ci.yml" in fset:
        text = read_text(os.path.join(repo, ".gitlab-ci.yml")) or ""
        reserved = {"stages", "variables", "include", "default", "workflow",
                    "image", "services", "before_script", "after_script", "cache"}
        for m in re.finditer(r"^([A-Za-z0-9_-]+):", text, re.M):
            job = m.group(1)
            if job in reserved or job.startswith("."):
                continue
            low, label = job.lower(), "CI job: " + job
            if "deploy" in low or "release" in low or low == "pages":
                add("deploy", label, ".gitlab-ci.yml")
            elif "test" in low or "lint" in low:
                add("test", label, ".gitlab-ci.yml")
            else:
                add("other", label, ".gitlab-ci.yml")
    for key in cmds:
        cmds[key] = cmds[key][:15]
    return cmds


def build_checklist(result):
    items = [
        "Склонируйте репозиторий и откройте его в редакторе",
        "Прочитайте README.md и этот отчёт Onboarder",
    ]
    for c in result["commands"]["setup"][:2]:
        items.append("Установите зависимости: `%s`" % c["cmd"])
    for c in result["commands"]["run"][:1]:
        items.append("Запустите проект локально: `%s`" % c["cmd"])
    for c in result["commands"]["test"][:1]:
        items.append("Прогоните тесты: `%s`" % c["cmd"])
    if result["modules"]:
        items.append("Изучите крупнейший модуль `%s`" % result["modules"][0]["name"])
    if result["key_files"]:
        items.append("Просмотрите самый часто меняемый файл `%s`"
                     % result["key_files"][0]["path"])
    if result["api"]:
        items.append("Пройдитесь по карте API и вызовите 1–2 эндпоинта локально")
    if result["db"]["models"] or result["db"]["migrations"]["count"]:
        items.append("Разберитесь со схемой БД: модели и миграции из раздела «База данных»")
    if result["contributors"]:
        items.append("Познакомьтесь с экспертами: %s" % ", ".join(
            c["name"] for c in result["contributors"][:3]))
    items.append("Возьмите первую небольшую задачу и откройте merge request")
    return items


def main(argv):
    # На Windows stdout по умолчанию в локальной кодировке (cp1251),
    # а onboarder.js читает вывод как UTF-8 — приводим к UTF-8 явно.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    repo, output = ".", None
    args, i = argv[1:], 0
    while i < len(args):
        if args[i] == "--output" and i + 1 < len(args):
            output = args[i + 1]
            i += 2
        else:
            repo = args[i]
            i += 1
    repo = os.path.abspath(repo)
    if not os.path.isdir(repo):
        print(json.dumps({"error": "Каталог не найден: %s" % repo},
                         ensure_ascii=False))
        return 1

    start = time.time()
    files = walk_files(repo)
    lang_lines, api, models = scan_code(repo, files)
    migration_paths = sorted({rel.split("/")[0] + "/..." for rel in files
                              if any(h in rel for h in MIGRATION_HINTS)})
    migration_count = sum(1 for rel in files
                          if any(h in rel for h in MIGRATION_HINTS))

    result = {
        "name": os.path.basename(repo),
        "repo": repo,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "stats": {"files": len(files), "lines": sum(lang_lines.values())},
        "languages": [{"name": n, "lines": l}
                      for n, l in lang_lines.most_common()],
        "stack": detect_stack(repo),
        "modules": detect_modules(repo, files),
        "key_files": detect_key_files(repo, files),
        "contributors": detect_contributors(repo),
        "api": api,
        "db": {
            "migrations": {"count": migration_count, "paths": migration_paths[:10]},
            "models": models,
        },
        "commands": detect_commands(repo, files),
    }
    result["checklist"] = build_checklist(result)
    result["elapsed_sec"] = round(time.time() - start, 2)

    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if output:
        with open(output, "w", encoding="utf-8") as fh:
            fh.write(payload)
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
