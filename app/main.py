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

# Updated path: Assuming you are running from /app and your tf is in /terraform
TF_FILE = "../terraform/security_group.tf" 

def save_result(resource, result, actual):
    log = {"timestamp": str(datetime.now()), "resource": resource, "actual": actual, "result": result}
    with open("drift_log.json", "a") as f:
        f.write(json.dumps(log) + "\n")

def create_self_healing_pr(title, body, branch_name, old_val, new_val):
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPO") 

    if not token or not repo:
        print(f"❌ Missing GitHub Credentials for: {title}")
        return

    # 1. Prepare Git Branch - always start fresh from main
    subprocess.run(["git", "checkout", "main"], stderr=subprocess.DEVNULL)
    subprocess.run(["git", "pull", "origin", "main"], stderr=subprocess.DEVNULL)
    subprocess.run(["git", "checkout", "-b", branch_name], stderr=subprocess.DEVNULL)
    
    # 2. THE CORE LOGIC: Edit the actual Terraform file
    try:
        with open(TF_FILE, 'r') as f:
            content = f.read()
        
        # Self-Healing Replacement
        updated_content = content.replace(f'"{old_val}"', f'"{new_val}"')
        
        with open(TF_FILE, 'w') as f:
            f.write(updated_content)
        
        print(f"📝 Modified {TF_FILE}: Changed '{old_val}' -> '{new_val}'")
    except FileNotFoundError:
        print(f"❌ Error: {TF_FILE} not found at that path. Check your directory structure!")
        return

    # 3. Commit and Push the REAL code change
    subprocess.run(["git", "add", TF_FILE])
    subprocess.run(["git", "commit", "-m", title], stderr=subprocess.DEVNULL)
    subprocess.run(["git", "push", "-u", "origin", branch_name], stderr=subprocess.DEVNULL)

    # 4. Open PR via API
    url = f"https://api.github.com/repos/{repo}/pulls"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
    data = {"title": title, "head": branch_name, "base": "main", "body": body}

    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 201:
        print(f"🔧 PR Created: {response.json()['html_url']}")
        # Cleanup: Return to main
        subprocess.run(["git", "checkout", "main"], stderr=subprocess.DEVNULL)
    else:
        print(f"❌ PR Failed: {response.text}")

def main():
    print("\n🚀 GITOPS SELF-HEALING ENGINE")
    print("="*40)

    # --- EC2 INSTANCE TYPE CHECK ---
    print(f"🔍 Checking EC2: {INSTANCE_ID}...")
    instance = get_ec2_instance_by_id(INSTANCE_ID)
    
    if instance:
        actual_type = instance["type"]
        if actual_type != DESIRED_INSTANCE_TYPE:
            print(f"   ⚠️ DRIFT: AWS has {actual_type}, Code has {DESIRED_INSTANCE_TYPE}")
            
            # Create a unique branch for this specific fix
            timestamp = datetime.now().strftime('%H%M%S')
            create_self_healing_pr(
                title=f"Fix: Update EC2 type to {actual_type}",
                body=f"Drift Intelligence detected manual scaling. This PR updates {TF_FILE} to match AWS.",
                branch_name=f"fix/ec2-healing-{timestamp}",
                old_val=DESIRED_INSTANCE_TYPE,
                new_val=actual_type
            )
        else:
            print("   ✅ EC2 Instance type is in sync.")

    print("\n✅ ANALYSIS COMPLETE\n")

if __name__ == "__main__":
    main()

#check