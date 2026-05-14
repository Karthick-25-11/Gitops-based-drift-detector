def detect_drift(desired_ports, actual_ports):
    """
    Existing logic for Security Group port comparison.
    """
    extra_ports = [p for p in actual_ports if p not in desired_ports]
    missing_ports = [p for p in desired_ports if p not in actual_ports]
    
    drift = len(extra_ports) > 0 or len(missing_ports) > 0
    
    return {
        "drift": drift,
        "severity": "HIGH" if 22 in extra_ports else "MEDIUM",
        "reason": "Security Group port mismatch",
        "extra_ports": extra_ports,
        "missing_ports": missing_ports
    }

def compare_ec2_instance(actual_type, desired_type):
    """Returns True if instance types match."""
    return actual_type == desired_type

def compare_s3_public_access(actual_config, desired_config):
    """
    Compares S3 Public Access Block settings.
    Returns a list of keys that have drifted (e.g., set to False in AWS).
    """
    drifts = []
    for key, desired_value in desired_config.items():
        if actual_config.get(key) != desired_value:
            drifts.append(key)
    return drifts

def compare_iam_policies(actual_policies, desired_policies):
    """
    Checks for extra policies attached to the role.
    Returns a list of unauthorized policies found in AWS.
    """
    # We identify policies in AWS that are NOT in our Git Source of Truth
    extra_policies = [p for p in actual_policies if p not in desired_policies]
    return extra_policies