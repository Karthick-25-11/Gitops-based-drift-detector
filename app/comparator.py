def detect_drift(desired_ports, actual_ports):
    desired_set = set(desired_ports)
    actual_set = set(actual_ports)

    if desired_set == actual_set:
        return {
            "drift": False,
            "severity": "NONE",
            "message": "No drift detected"
        }

    extra_ports = list(actual_set - desired_set)
    missing_ports = list(desired_set - actual_set)

    # Severity logic
    severity = "MEDIUM"
    reason = "Configuration drift detected"

    if 22 in extra_ports:
        severity = "HIGH"
        reason = "SSH port exposed (security risk)"

    return {
        "drift": True,
        "severity": severity,
        "missing_ports": missing_ports,
        "extra_ports": extra_ports,
        "reason": reason
    }