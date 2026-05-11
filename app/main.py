from aws_fetcher import get_security_group_by_name, get_ec2_instance_by_id
from comparator import detect_drift

import json
from datetime import datetime
import os
import requests
import subprocess

# --- CONFIGURATION ---
DESIRED_PORTS = [80, 443]

# Must match Terraform desired state
DESIRED_INSTANCE_TYPE = "t3.micro"

INSTANCE_ID = "i-0d8fba0469aef3a03"
SG_NAME = "demo-sg-v2"

# Correct Terraform files
EC2_TF_FILE = "../terraform/ec2.tf"
SG_TF_FILE = "../terraform/security_group.tf"


def save_result(resource, result, actual):
    log = {
        "timestamp": str(datetime.now()),
        "resource": resource,
        "actual": actual,
        "result": result
    }

    with open("drift_log.json", "a") as f:
        f.write(json.dumps(log) + "\n")


def create_self_healing_pr(
    title,
    body,
    branch_name,
    tf_file,
    old_val,
    new_val
):
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPO")

    if not token or not repo:
        print(f"❌ Missing GitHub Credentials for: {title}")
        return

    # -----------------------------
    # Prepare fresh branch
    # -----------------------------
    subprocess.run(
        ["git", "checkout", "main"],
        stderr=subprocess.DEVNULL
    )

    subprocess.run(
        ["git", "pull", "origin", "main"],
        stderr=subprocess.DEVNULL
    )

    subprocess.run(
        ["git", "checkout", "-b", branch_name],
        stderr=subprocess.DEVNULL
    )

    # -----------------------------
    # Modify Terraform file
    # -----------------------------
    try:
        with open(tf_file, "r") as f:
            content = f.read()

        updated_content = content.replace(
            f'"{old_val}"',
            f'"{new_val}"'
        )

        if content == updated_content:
            print(f"❌ No changes detected in {tf_file}")
            return

        with open(tf_file, "w") as f:
            f.write(updated_content)

        print(f"📝 Modified {tf_file}")
        print(f"   Changed '{old_val}' -> '{new_val}'")

    except FileNotFoundError:
        print(f"❌ Error: {tf_file} not found")
        return

    # -----------------------------
    # Commit changes
    # -----------------------------
    subprocess.run(["git", "add", tf_file])

    commit_result = subprocess.run(
        ["git", "commit", "-m", title],
        capture_output=True,
        text=True
    )

    if "nothing to commit" in commit_result.stdout.lower():
        print("❌ Nothing changed. Commit skipped.")
        return

    # -----------------------------
    # Push branch
    # -----------------------------
    subprocess.run(
        ["git", "push", "-u", "origin", branch_name],
        stderr=subprocess.DEVNULL
    )

    # -----------------------------
    # Create PR
    # -----------------------------
    url = f"https://api.github.com/repos/{repo}/pulls"

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json"
    }

    data = {
        "title": title,
        "head": branch_name,
        "base": "main",
        "body": body
    }

    response = requests.post(
        url,
        json=data,
        headers=headers
    )

    if response.status_code == 201:
        print(f"\n🔧 PR Created Successfully")
        print(response.json()["html_url"])

    else:
        print(f"\n❌ PR Failed")
        print(response.text)

    subprocess.run(
        ["git", "checkout", "main"],
        stderr=subprocess.DEVNULL
    )


def check_ec2_drift():

    print(f"\n🔍 Checking EC2: {INSTANCE_ID}...")

    instance = get_ec2_instance_by_id(INSTANCE_ID)

    if not instance:
        print("❌ EC2 instance not found")
        return

    actual_type = instance["type"]

    if actual_type != DESIRED_INSTANCE_TYPE:

        print(
            f"⚠️ DRIFT: AWS has {actual_type}, "
            f"Terraform has {DESIRED_INSTANCE_TYPE}"
        )

        timestamp = datetime.now().strftime('%H%M%S')

        create_self_healing_pr(
            title=f"Fix: Update EC2 type to {actual_type}",

            body=(
                f"Drift Intelligence detected EC2 drift.\n\n"
                f"Terraform desired state: {DESIRED_INSTANCE_TYPE}\n"
                f"AWS actual state: {actual_type}\n\n"
                f"This PR updates Terraform to match AWS."
            ),

            branch_name=f"fix/ec2-healing-{timestamp}",

            # IMPORTANT FIX
            tf_file=EC2_TF_FILE,

            old_val=DESIRED_INSTANCE_TYPE,
            new_val=actual_type
        )

    else:
        print("✅ EC2 instance type is in sync")


def check_security_group_drift():

    print(f"\n🔍 Checking Security Group: {SG_NAME}")

    sg = get_security_group_by_name(SG_NAME)

    if not sg:
        print("❌ Security group not found")
        return

    actual_ports = sg["ports"]

    result = detect_drift(
        DESIRED_PORTS,
        actual_ports
    )

    save_result(
        "security_group",
        result,
        actual_ports
    )

    if result["drift"]:

        print(
            f"⚠️ SECURITY GROUP DRIFT: "
            f"Extra Ports {result['extra_ports']}"
        )

    else:
        print("✅ Security group is in sync")


def main():

    print("\n🚀 GITOPS SELF-HEALING ENGINE")
    print("=" * 40)

    # EC2 Drift Detection
    check_ec2_drift()

    # Security Group Drift Detection
    check_security_group_drift()

    print("\n✅ ANALYSIS COMPLETE\n")


if __name__ == "__main__":
    main()