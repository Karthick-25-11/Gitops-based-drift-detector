import json
from datetime import datetime
import os
import requests
import subprocess
from aws_fetcher import (
    get_security_group_by_name, 
    get_ec2_instance_by_id, 
    get_s3_public_access_status, 
    get_iam_attached_role_policies
)
from comparator import (
    detect_drift, 
    compare_ec2_instance, 
    compare_s3_public_access, 
    compare_iam_policies
)

# --- CONFIGURATION ---
DESIRED_PORTS = [80, 443]
DESIRED_INSTANCE_TYPE = "t3.small"
INSTANCE_ID = "i-0d8fba0469aef3a03"
SG_NAME = "demo-sg-v2"

# Security Desired States
BUCKET_NAME = "gitops-drift-demo-bucket"
DESIRED_S3_BLOCKS = {
    "block_public_acls": True,
    "ignore_public_acls": True,
    "block_public_policy": True,
    "restrict_public_buckets": True
}

ROLE_NAME = "gitops-app-role"
DESIRED_IAM_POLICIES = ["AmazonS3ReadOnlyAccess"]

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

    subprocess.run(["git", "checkout", "main"])
    subprocess.run(["git", "pull", "origin", "main"])
    subprocess.run(["git", "checkout", "-b", branch_name])

    marker_file = "reconcile.txt"
    with open(marker_file, "w") as f:
        f.write(f"Reconciliation approved at {datetime.now()}\n")

    print(f"📝 Created reconciliation marker: {marker_file}")
    subprocess.run(["git", "add", marker_file])
    subprocess.run(["git", "commit", "-m", title])
    subprocess.run(["git", "push", "--set-upstream", "origin", branch_name])

    url = f"https://api.github.com/repos/{repo}/pulls"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
    data = {"title": title, "head": branch_name, "base": "main", "body": body}

    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 201:
        print(f"\n🔧 PR Created Successfully:\n{response.json()['html_url']}")
        subprocess.run(["git", "checkout", "main"])
    else:
        print(f"\n❌ PR Failed:\n{response.text}")

def main():
    print("\n🚀 GITOPS SELF-HEALING ENGINE")
    print("=" * 40)

    # 1. EC2 DRIFT CHECK
    print(f"\n🔍 Checking EC2: {INSTANCE_ID}...")
    instance = get_ec2_instance_by_id(INSTANCE_ID)
    if instance:
        actual_type = instance["type"]
        if not compare_ec2_instance(actual_type, DESIRED_INSTANCE_TYPE):
            print(f"   ⚠️ DRIFT: AWS has {actual_type}, Code has {DESIRED_INSTANCE_TYPE}")
            timestamp = datetime.now().strftime('%H%M%S')
            create_self_healing_pr(
                title="Ops Fix: Reconcile EC2 Instance Type Drift",
                body=f"GitOps detected EC2 drift.\n\nAWS Type: {actual_type}\nDesired: {DESIRED_INSTANCE_TYPE}",
                branch_name=f"fix/ec2-healing-{timestamp}"
            )
        else:
            print("   ✅ EC2 Instance type is in sync")

    # 2. SECURITY GROUP DRIFT CHECK
    print(f"\n🔍 Checking Security Group: {SG_NAME}...")
    sg = get_security_group_by_name(SG_NAME)
    if sg:
        actual_ports = sg["ports"]
        result = detect_drift(DESIRED_PORTS, actual_ports)
        print("Actual Ports:", actual_ports)
        if result["drift"]:
            print(f"\n⚠️ Drift detected! Severity: {result['severity']}")
            if 22 in result.get("extra_ports", []):
                timestamp = datetime.now().strftime('%H%M%S')
                create_self_healing_pr(
                    title="Security Fix: Remove SSH Exposure",
                    body="GitOps detected unauthorized SSH exposure (Port 22).",
                    branch_name=f"fix/sg-healing-{timestamp}"
                )
        else:
            print("   ✅ Security Group is in sync")

    # 3. S3 PUBLIC ACCESS DRIFT CHECK
    print(f"\n🔍 Checking S3 Bucket: {BUCKET_NAME}...")
    s3_actual = get_s3_public_access_status(BUCKET_NAME)
    if s3_actual:
        s3_drifts = compare_s3_public_access(s3_actual, DESIRED_S3_BLOCKS)
        if s3_drifts:
            print(f"   ⚠️ DRIFT: Public Access Blocks disabled: {s3_drifts}")
            timestamp = datetime.now().strftime('%H%M%S')
            create_self_healing_pr(
                title="Security Fix: Restore S3 Public Access Blocks",
                body=f"GitOps detected disabled S3 security blocks: {s3_drifts}",
                branch_name=f"fix/s3-healing-{timestamp}"
            )
        else:
            print("   ✅ S3 Public Access settings are in sync")

    # 4. IAM ROLE POLICY DRIFT CHECK
    print(f"\n🔍 Checking IAM Role: {ROLE_NAME}...")
    iam_actual = get_iam_attached_role_policies(ROLE_NAME)
    if iam_actual:
        extra_policies = compare_iam_policies(iam_actual['attached_policies'], DESIRED_IAM_POLICIES)
        if extra_policies:
            print(f"   ⚠️ DRIFT: Unauthorized Policies detected: {extra_policies}")
            timestamp = datetime.now().strftime('%H%M%S')
            create_self_healing_pr(
                title="Security Fix: Remove Unauthorized IAM Policies",
                body=f"GitOps detected unapproved IAM policies: {extra_policies}",
                branch_name=f"fix/iam-healing-{timestamp}"
            )
        else:
            print("   ✅ IAM Role Policies are in sync")

    print("\n✅ ANALYSIS COMPLETE\n")

if __name__ == "__main__":
    main()