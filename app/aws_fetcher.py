import boto3

# Initialize the client once at the top
ec2 = boto3.client("ec2", region_name="us-east-1")

def get_security_group_by_name(name):
    """Fetches security group ports by name."""
    response = ec2.describe_security_groups(
        Filters=[{"Name": "group-name", "Values": [name]}]
    )

    if not response["SecurityGroups"]:
        return None

    sg = response["SecurityGroups"][0]

    ports = []
    for perm in sg.get("IpPermissions", []):
        # We use .get() because some protocols (like ICMP or -1) don't have ports
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
        response = ec2.describe_instances(InstanceIds=[instance_id])
        
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