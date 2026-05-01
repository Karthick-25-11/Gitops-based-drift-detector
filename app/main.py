from aws_fetcher import get_security_group_by_name
from comparator import detect_drift

import json
from datetime import datetime

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
    else:
        print("\n✅ No drift detected — system is in desired state")


if __name__ == "__main__":
    main()