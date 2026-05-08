from aws_fetcher import get_security_group_by_name  
from comparator import detect_drift

import json
from datetime import datetime
import os
import requests
import subprocess

# Desired state (from Terraform)
DESIRED_PORTS = [80]


def save_result(result, actual_ports):
    log = {
        "timestamp": str(datetime.now()),
        "actual_ports": actual_ports,
        "result": result
    }

    with open("drift_log.json", "a") as f:
        f.write(json.dumps(log) + "\n")


# 🔧 NEW: Create branch
def create_branch():
    branch_name = "fix/remove-ssh"

    # create branch (ignore if exists)
    subprocess.run(["git", "checkout", "-b", branch_name], stderr=subprocess.DEVNULL)
    subprocess.run(["git", "push", "-u", "origin", branch_name], stderr=subprocess.DEVNULL)

    return branch_name


# 🔧 NEW: Add commit so PR can be created
def make_dummy_commit():
    with open("auto_fix.txt", "a") as f:
        f.write("trigger-pr\n")

    subprocess.run(["git", "add", "auto_fix.txt"])
    subprocess.run(
        ["git", "commit", "-m", "fix: trigger PR for SSH drift"],
        stderr=subprocess.DEVNULL
    )


# 🔧 NEW: Create PR
def create_fix_pr():
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPO")  # format: username/repo

    if not token or not repo:
        print("\n❌ GitHub token or repo not set")
        return

    branch = create_branch()

    # 🔧 NEW: ensure commit exists
    make_dummy_commit()

    # push commit to branch
    subprocess.run(["git", "push"], stderr=subprocess.DEVNULL)

    url = f"https://api.github.com/repos/{repo}/pulls"

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json"
    }

    data = {
        "title": "Fix: Remove SSH (port 22) exposure",
        "head": branch,
        "base": "main",
        "body": "Drift detected: Port 22 is open in AWS but not in Terraform. Run terraform apply to enforce desired state."
    }

    response = requests.post(url, json=data, headers=headers)

    if response.status_code == 201:
        print("\n🔧 PR created successfully:", response.json()["html_url"])
    else:
        print("\n❌ Failed to create PR:", response.text)


def main():
    # Fetch actual AWS state
    sg = get_security_group_by_name("demo-sg")

    if not sg:
        print("❌ Security group not found")
        return

    actual_ports = sg["ports"]

    # Detect drift
    result = detect_drift(DESIRED_PORTS, actual_ports)

    # ✅ Logging (this is the new part)
    save_result(result, actual_ports)

    # Output
    print("\n=== Drift Analysis ===")
    print("Actual Ports:", actual_ports)

    if result["drift"]:
        print(f"\n⚠️ Drift detected! Severity: {result['severity']}")
        print("Reason:", result["reason"])
        print("Extra Ports:", result["extra_ports"])
        print("Missing Ports:", result["missing_ports"])

        # 🔧 NEW: Create PR if SSH port is exposed
        if 22 in result.get("extra_ports", []):
            create_fix_pr()

    else:
        print("\n✅ No drift detected — system is in desired state")


if __name__ == "__main__":
    main() 