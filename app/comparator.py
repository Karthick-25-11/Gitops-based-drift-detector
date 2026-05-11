def detect_drift(desired, actual):
    """
    Intelligence logic to detect differences between IaC and Cloud.
    Works for both Security Group lists and EC2 attribute strings.
    """
    
    # CASE 1: Comparing Lists (Security Group Ports)
    if isinstance(desired, list) and isinstance(actual, list):
        desired_set = set(desired)
        actual_set = set(actual)

        if desired_set == actual_set:
            return {"drift": False, "severity": "NONE", "reason": "No drift detected"}

        extra_ports = list(actual_set - desired_set)
        missing_ports = list(desired_set - actual_set)

        # Intelligence: Severity logic
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

    # CASE 2: Comparing Strings (EC2 Instance Type)
    else:
        if desired == actual:
            return {"drift": False, "severity": "NONE", "reason": "No drift detected"}
        
        return {
            "drift": True,
            "severity": "MEDIUM",
            "reason": f"Attribute mismatch: Expected {desired}, found {actual}",
            "actual": actual,
            "desired": desired
        }