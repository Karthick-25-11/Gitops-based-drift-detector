import boto3

# --- CONFIGURATION ---
# Region locked to us-east-1 as per user requirement
REGION = "us-east-1"

# Initialize clients
ec2_client = boto3.client("ec2", region_name=REGION)
s3_client = boto3.client("s3", region_name=REGION)
iam_client = boto3.client("iam") # IAM is a global service

def get_security_group_by_name(name):
    """Fetches security group ports by name."""
    response = ec2_client.describe_security_groups(
        Filters=[{"Name": "group-name", "Values": [name]}]
    )

    if not response["SecurityGroups"]:
        return None

    sg = response["SecurityGroups"][0]

    ports = []
    for perm in sg.get("IpPermissions", []):
        port = perm.get("FromPort")
        if port is not None:
            ports.append(port)

    return {
        "group_id": sg["GroupId"],
        "ports": ports
    }

def get_ec2_instance_by_id(instance_id):
    """Fetches EC2 instance details (type and state) by ID."""
    try:
        response = ec2_client.describe_instances(InstanceIds=[instance_id])
        
        # Navigate the Reservations -> Instances structure
        instance = response['Reservations'][0]['Instances'][0]
        
        return {
            "id": instance['InstanceId'],
            "type": instance['InstanceType'],
            "state": instance['State']['Name']
        }
    except Exception as e:
        print(f"❌ Error fetching EC2 {instance_id}: {e}")
        return None

def get_s3_public_access_status(bucket_name):
    """
    Fetches the Public Access Block configuration for a bucket.
    Identifies if 'Block all public access' has been disabled manually.
    """
    try:
        response = s3_client.get_public_access_block(Bucket=bucket_name)
        config = response['PublicAccessBlockConfiguration']
        
        return {
            "bucket": bucket_name,
            "block_public_acls": config.get('BlockPublicAcls'),
            "ignore_public_acls": config.get('IgnorePublicAcls'),
            "block_public_policy": config.get('BlockPublicPolicy'),
            "restrict_public_buckets": config.get('RestrictPublicBuckets')
        }
    except Exception as e:
        print(f"❌ Error fetching S3 Public Access for {bucket_name}: {e}")
        return None

def get_iam_attached_role_policies(role_name):
    """
    Lists policies attached to a specific IAM role.
    Used to detect manual policy attachments (Privilege Escalation).
    """
    try:
        response = iam_client.list_attached_role_policies(RoleName=role_name)
        policies = [p['PolicyName'] for p in response['AttachedPolicies']]
        
        return {
            "role_name": role_name,
            "attached_policies": policies
        }
    except Exception as e:
        print(f"❌ Error fetching IAM policies for {role_name}: {e}")
        return None