import os
import subprocess
import time
import requests
from google.genai import Client
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# Initialize rich console
console = Console()

# Load environment variables
load_dotenv()

# Gemini API key
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    console.print("[bold red]Error:[/bold red] GEMINI_API_KEY must be set in .env file")
    raise ValueError("GEMINI_API_KEY must be set")

# GitHub repo info
base_branch = "main"


def run_verbose(cmd, description="", capture_output=False):
    """Run a shell command with rich verbose output."""
    console.print(
        Panel(
            f"[bold cyan]Running:[/bold cyan] {' '.join(cmd)}\n{description}",
            style="magenta",
        )
    )
    if capture_output:
        result = subprocess.run(cmd, text=True, capture_output=True)
        if result.stdout:
            console.print(Panel(result.stdout.strip(), style="green"))
        if result.stderr:
            console.print(Panel(result.stderr.strip(), style="red"))
        return result
    else:
        subprocess.run(cmd, check=True)


def gemini_generate(prompt, task_name):
    """Show spinner while Gemini generates content."""
    console.print(f"[bold blue]{task_name} via Gemini...[/bold blue]")
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console,
    ) as progress:
        task = progress.add_task(f"{task_name} in progress", start=False)
        progress.start_task(task)
        response = client.models.generate_content(
            model="gemini-2.5-flash", contents=prompt
        )
    return response.text.strip()


# Stage all changes
run_verbose(["git", "add", "."], description="Staging all changes")

# Save staged diff
diff_file = "changes.diff"
with open(diff_file, "w") as f:
    subprocess.run(["git", "diff", "--staged"], stdout=f, check=True)
console.print(f"[bold yellow]Staged diff saved to {diff_file}[/bold yellow]")

# Read diff
with open(diff_file, "r") as f:
    diff_content = f.read()
console.print(f"[dim]Diff length: {len(diff_content)} characters[/dim]")

# Initialize Gemini client
client = Client(api_key=api_key)

# Detect commit type (multiple labels)
type_prompt = f"""
Analyze the following code diff and determine all applicable change types.
Possible labels: feature, fix, docs, refactor, test, chore.
YOU MUST RETURN THE LABELS, AND ONLY THE LABES, IN A COMMA SEPERATED LIST.
(e.g. 'feature, docs')

Diff:
{diff_content}
"""
labels_text = gemini_generate(type_prompt, "Detecting change types")
labels = [label.strip().lower() for label in labels_text.split(",") if label.strip()]
if not labels:
    labels = ["feature"]
console.print(f"[bold green]Detected labels:[/bold green] {', '.join(labels)}")

# Generate commit message
commit_prompt = f"Generate a concise commit message for this code diff. YOU MUST RETURN JUST ONE MESSAGE; NOT A COLLECTION OFF MESSAGES. A MESSAGE CAN CONTAIN MULTIPLE SENTENCES:\n{diff_content}"
commit_message = gemini_generate(commit_prompt, "Commit message generation")
if not commit_message:
    commit_message = "Auto commit with generated message"
console.print(Panel(commit_message, title="Commit Message", style="green"))

# Generate PR title
pr_title_prompt = f"Generate a short, descriptive Pull Request title based on this code diff. YOU MUST RETURN ONLY  ONE  TITLE FOR APULL REQUEST, NOT A COLLECTION:\n{diff_content}"
pr_title = gemini_generate(pr_title_prompt, "PR title generation")
if not pr_title:
    pr_title = commit_message
console.print(Panel(pr_title, title="PR Title", style="yellow"))

# Create branch
branch_name = f"{labels[0]}/auto-update-{int(time.time())}"
run_verbose(
    ["git", "checkout", "-b", branch_name],
    description=f"Creating branch: {branch_name}",
)

# Commit changes
run_verbose(["git", "commit", "-m", commit_message], description="Committing changes")

# Push branch
run_verbose(
    ["git", "push", "origin", branch_name], description="Pushing Branch to remote"
)
# GitHub API info
repo = os.getenv("GITHUB_REPO", "ProjectSaveGH/NoteManager")
token = os.getenv("GITHUB_TOKEN")
if not token:
    console.print("[bold red]Error:[/bold red] GITHUB_TOKEN must be set")
    raise ValueError("GITHUB_TOKEN not set")

headers = {"Authorization": f"token {token}"}

# Create Pull Request via API
url_create_pr = f"https://api.github.com/repos/{repo}/pulls"
payload = {
    "title": pr_title,
    "head": branch_name,
    "base": base_branch,
    "body": f"Commit Message:\n{commit_message}\n\nThis PR was generated automatically using Gemini.",
}
response = requests.post(url_create_pr, json=payload, headers=headers)

if response.status_code == 201:
    pr_number = response.json()["number"]
    console.print(f"[bold green]✅ Pull Request created: #{pr_number}[/bold green]")
else:
    console.print(
        f"[bold red]❌ Failed to create PR:[/bold red] {response.status_code} {response.text}"
    )
    pr_number = None

# Add labels if PR creation succeeded
if pr_number:
    url_labels = f"https://api.github.com/repos/{repo}/issues/{pr_number}/labels"
    payload_labels = {"labels": labels}
    resp_labels = requests.post(url_labels, json=payload_labels, headers=headers)
    if resp_labels.status_code == 200:
        console.print(
            f"[bold green]✅ Labels added to PR #{pr_number}:[/bold green] {', '.join(labels)}"
        )
    else:
        console.print(
            f"[bold red]❌ Failed to add labels:[/bold red] {resp_labels.status_code} {resp_labels.text}"
        )

# Optional: reset local main to match remote (opt-in)
if os.getenv("RESET_LOCAL_MAIN", "0") == "1":
    run_verbose(
        ["git", "fetch", "origin", "--prune"],
        description="Sync with origin before resetting local main",
    )
    run_verbose(
        ["git", "checkout", "-B", "main", "origin/main"],
        description="Reset local main to match origin/main",
    )
    run_verbose(
        ["git", "pull"],
        description="Trying to pull changes, if previous step did not work",
    )
# Clean up
if os.path.exists(diff_file):
    os.remove(diff_file)
    console.print(
        f"[bold magenta]Temporary diff file {diff_file} removed[/bold magenta]"
    )
