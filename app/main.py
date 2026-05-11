from aws_fetcher import get_security_group_by_name, get_ec2_instance_by_id
from comparator import detect_drift

import json
from datetime import datetime
import os
import requests
import subprocess

# --- CONFIGURATION ---
DESIRED_PORTS = [80, 443]
DESIRED_INSTANCE_TYPE = "t3.micro"

INSTANCE_ID = "i-0d8fba0469aef3a03"
SG_NAME = "demo-sg-v2"


def save_result(resource, result, actual):
    log = {
        "timestamp": str(datetime.now()),
        "resource": resource,
        "actual": actual,
        "result": result
    }

    with open("drift_log.json", "a") as f:
        f.write(json.dumps(log) + "\n")


def create_self_healing_pr(title, body, branch_name):
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPO")

    if not token or not repo:
        print(f"❌ Missing GitHub Credentials for: {title}")
        return

    # --- Prepare Fresh Branch ---
    subprocess.run(["git", "checkout", "main"])
    subprocess.run(["git", "pull", "origin", "main"])
    subprocess.run(["git", "checkout", "-b", branch_name])

    # --- Create reconciliation marker file ---
    marker_file = "reconcile.txt"

    with open(marker_file, "w") as f:
        f.write(f"Reconciliation approved at {datetime.now()}\n")

    print(f"📝 Created reconciliation marker: {marker_file}")

    # --- Commit real change ---
    subprocess.run(["git", "add", marker_file])
    subprocess.run(["git", "commit", "-m", title])

    # --- Push branch ---
    subprocess.run([
        "git",
        "push",
        "--set-upstream",
        "origin",
        branch_name
    ])

    # --- Create PR ---
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

    response = requests.post(url, json=data, headers=headers)

    if response.status_code == 201:
        print(f"\n🔧 PR Created Successfully:")
        print(response.json()["html_url"])

        # return back to main
        subprocess.run(["git", "checkout", "main"])

    else:
        print(f"\n❌ PR Failed:")
        print(response.text)


def main():
    print("\n🚀 GITOPS SELF-HEALING ENGINE")
    print("=" * 40)

    # =========================================================
    # EC2 DRIFT CHECK
    # =========================================================

    print(f"\n🔍 Checking EC2: {INSTANCE_ID}...")

    instance = get_ec2_instance_by_id(INSTANCE_ID)

    if instance:

        actual_type = instance["type"]

        if actual_type != DESIRED_INSTANCE_TYPE:

            print(
                f"   ⚠️ DRIFT: AWS has {actual_type}, "
                f"Code has {DESIRED_INSTANCE_TYPE}"
            )

            result = {
                "drift": True,
                "severity": "HIGH",
                "reason": "EC2 instance type drift"
            }

            save_result(
                "ec2_instance_type",
                result,
                actual_type
            )

            timestamp = datetime.now().strftime('%H%M%S')

            create_self_healing_pr(
                title="Ops Fix: Reconcile EC2 Instance Type Drift",
                body=(
                    f"GitOps detected EC2 drift.\n\n"
                    f"AWS Instance Type: {actual_type}\n"
                    f"Terraform Desired State: {DESIRED_INSTANCE_TYPE}\n\n"
                    f"Merge this PR to trigger Terraform reconciliation "
                    f"and restore infrastructure to desired state."
                ),
                branch_name=f"fix/ec2-healing-{timestamp}"
            )

        else:
            print("   ✅ EC2 Instance type is in sync")

    else:
        print("❌ EC2 instance not found")

    # =========================================================
    # SECURITY GROUP DRIFT CHECK
    # =========================================================

    print(f"\n🔍 Checking Security Group: {SG_NAME}...")

    sg = get_security_group_by_name(SG_NAME)

    if sg:

        actual_ports = sg["ports"]

        result = detect_drift(
            DESIRED_PORTS,
            actual_ports
        )

        save_result(
            "security_group_ports",
            result,
            actual_ports
        )

        print("Actual Ports:", actual_ports)

        if result["drift"]:

            print(
                f"\n⚠️ Drift detected! "
                f"Severity: {result['severity']}"
            )

            print("Reason:", result["reason"])
            print("Extra Ports:", result["extra_ports"])
            print("Missing Ports:", result["missing_ports"])

            # Example:
            # AWS has port 22 manually added
            # Terraform does not allow it

            if 22 in result.get("extra_ports", []):

                timestamp = datetime.now().strftime('%H%M%S')

                create_self_healing_pr(
                    title="Security Fix: Remove SSH Exposure",
                    body=(
                        "GitOps detected unauthorized SSH exposure.\n\n"
                        "Port 22 exists in AWS but not in Terraform.\n\n"
                        "Merge this PR to trigger Terraform reconciliation "
                        "and remove the drift."
                    ),
                    branch_name=f"fix/sg-healing-{timestamp}"
                )

        else:
            print("   ✅ Security Group is in sync")

    else:
        print("❌ Security Group not found")

    print("\n✅ ANALYSIS COMPLETE\n")


if __name__ == "__main__":
    main()