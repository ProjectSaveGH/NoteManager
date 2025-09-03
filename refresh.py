import subprocess
from pathlib import Path
from datetime import datetime
import json
import fnmatch
import hashlib
import pyzipper
import zipfile
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
import argparse
from difflib import get_close_matches

# ----------------- Console -----------------
console = Console()


def style_panel(title, text, color="cyan"):
    return Panel(text, title=title, style=color, expand=True)


# ----------------- Config -----------------
CONFIG = {
    "exclude_from_backup": ["backup"],
    "protected_files": [".env"],
    "hooks": {"pre_update": [], "post_update": []},
    "dry_run": False,
    "backup_password": None,
}

REQUIRED_KEYS = list(CONFIG.keys())


def load_config():
    cfg_file = Path("refresh.config.json")
    if cfg_file.exists():
        try:
            with cfg_file.open("r", encoding="utf-8") as f:
                cfg = json.load(f)
                CONFIG.update(cfg)
                validate_config(cfg)
                console.print("✔ Config loaded")
        except Exception as e:
            console.print(f"[ERROR] Failed to load config: {e}")
    else:
        console.print("[WARN] No config found, using default values")


def validate_config(cfg):
    for key in REQUIRED_KEYS:
        if key not in cfg:
            console.print(f"[ERROR] Missing config key '{key}'")
    for key in cfg.keys():
        if key not in REQUIRED_KEYS:
            suggestion = get_close_matches(key, REQUIRED_KEYS, n=1)
            if suggestion:
                console.print(
                    f"[WARN] Unknown config key '{key}'. Did you mean '{suggestion[0]}'?"
                )
            else:
                console.print(f"[WARN] Unknown config key '{key}'.")


# ----------------- Commands -----------------
def run_command(cmd, capture=False):
    if CONFIG.get("dry_run"):
        console.print(f"[DRY-RUN] {cmd}")
        return None
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        console.print(f"[ERROR] Command failed: {cmd}\n{result.stderr.strip()}")
        return None
    return result.stdout.strip() if capture else ""


# ----------------- Git -----------------
def ensure_gitignore():
    gitignore = Path(".gitignore")
    existing = gitignore.read_text().splitlines() if gitignore.exists() else []
    with gitignore.open("a") as f:
        for pf in CONFIG["protected_files"]:
            if pf not in existing:
                f.write(f"{pf}\n")
                console.print(f"'{pf}' added to .gitignore.")


def sensitive_file_check():
    gitignore = (
        Path(".gitignore").read_text().splitlines()
        if Path(".gitignore").exists()
        else []
    )
    for pf in CONFIG["protected_files"]:
        if pf not in gitignore:
            console.print(f"[WARN] Sensitive file {pf} not in .gitignore!")


def get_default_branch():
    branch_info = run_command("git remote show origin", capture=True)
    if branch_info:
        for line in branch_info.splitlines():
            if "HEAD branch:" in line:
                return line.split(":")[1].strip()
    return run_command("git rev-parse --abbrev-ref HEAD", capture=True) or "main"


def refresh_repo(branch):
    console.print(style_panel("Repo Update", f"Updating branch '{branch}'", "magenta"))
    run_command("git fetch --all")
    run_command(f"git reset --hard origin/{branch}")
    run_command(f"git pull origin {branch}")
    run_command("git gc")


def repo_status():
    branch = run_command("git rev-parse --abbrev-ref HEAD", capture=True) or "?"
    latest_commit = run_command("git log -1 --pretty=%B", capture=True) or "?"
    author = run_command("git log -1 --pretty=%an", capture=True) or "?"
    table = Table(title="Repository Status", header_style="bold cyan")
    table.add_column("Branch", style="yellow")
    table.add_column("Last Commit", style="green")
    table.add_column("Author", style="magenta")
    table.add_row(branch, latest_commit, author)
    console.print(table)


# ----------------- Backup -----------------
def should_exclude(item_name):
    for pattern in CONFIG["exclude_from_backup"]:
        if fnmatch.fnmatch(item_name, f"{pattern}*"):
            return True
    return False


def backup_repo():
    timestamp = datetime.now().isoformat(timespec="seconds").replace(":", "-")
    backup_dir = Path(".backup")
    backup_dir.mkdir(parents=True, exist_ok=True)
    zip_path = backup_dir / f"backup_{timestamp}.zip"
    password = CONFIG.get("backup_password")

    console.print(style_panel("Backup", f"Creating {zip_path}", "cyan"))

    if CONFIG.get("dry_run"):
        console.print("[DRY-RUN] Backup skipped")
        return

    if password:
        with pyzipper.AESZipFile(
            zip_path, "w", compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES
        ) as zf:
            zf.setpassword(password.encode("utf-8"))
            for item in Path(".").rglob("*"):
                if item.is_file():
                    rel_path = str(item.relative_to(Path(".")))
                    if should_exclude(rel_path) or rel_path.startswith(".backup/"):
                        continue
                    zf.write(item, rel_path)
    else:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for item in Path(".").rglob("*"):
                if item.is_file():
                    rel_path = str(item.relative_to(Path(".")))
                    if should_exclude(rel_path) or rel_path.startswith(".backup/"):
                        continue
                    zf.write(item, rel_path)

    sha256 = hashlib.sha256()
    with open(zip_path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    hash_file = backup_dir / f"{timestamp}.hash"
    hash_file.write_text(sha256.hexdigest())
    console.print(f"Backup completed. Hash stored in {hash_file}")


# ----------------- Hooks -----------------
def run_hooks(phase):
    hooks = CONFIG.get("hooks", {}).get(phase, [])
    if not hooks:
        return
    console.print(style_panel("Hooks", f"Running {phase}", "cyan"))
    for cmd in hooks:
        run_command(cmd)


# ----------------- Dependencies -----------------
def install_dependencies():
    if Path("package-lock.json").exists():
        run_command("npm ci")
    elif Path("package.json").exists():
        run_command("npm install")
    if Path("poetry.lock").exists():
        run_command("poetry install")
    if Path("Pipfile.lock").exists():
        run_command("pipenv install")
    for req in sorted(Path(".").glob("requirements*.txt")):
        run_command(f"pip install -r {req}")


# ----------------- Branch Choice -----------------
def interactive_branch_choice(default_branch):
    branches = run_command("git branch -r", capture=True)
    if not branches:
        return default_branch
    branch_list = [
        b.strip().replace("origin/", "") for b in branches.splitlines() if "->" not in b
    ]
    if not branch_list:
        return default_branch
    return Prompt.ask("Which branch?", choices=branch_list, default=default_branch)


# ----------------- Main -----------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Git Repo Refresher")
    parser.add_argument("--no-backup", action="store_true", help="Skip backup")
    parser.add_argument("--no-hooks", action="store_true", help="Skip pre/post hooks")
    parser.add_argument("--no-deps", action="store_true", help="Skip dependencies")
    parser.add_argument("--silent", action="store_true", help="Minimal output")
    parser.add_argument("--dry-run", action="store_true", help="Simulate only")
    args = parser.parse_args()

    CONFIG["dry_run"] = args.dry_run

    console.print(style_panel("🚀 Git Repo Refresher", "Starting...", "cyan"))
    load_config()
    ensure_gitignore()
    sensitive_file_check()

    if not args.no_backup:
        backup_repo()
    else:
        console.print("[INFO] Skipping backup (--no-backup)")

    default_branch = get_default_branch()
    branch = interactive_branch_choice(default_branch)

    if not args.no_hooks:
        run_hooks("pre_update")
    refresh_repo(branch)
    if not args.no_deps:
        install_dependencies()
    if not args.no_hooks:
        run_hooks("post_update")

    repo_status()
    console.print("✅ Repository updated & ready")
