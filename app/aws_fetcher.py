import boto3

ec2 = boto3.client("ec2", region_name="us-east-1")


def get_security_group_by_name(name):
    response = ec2.describe_security_groups(
        Filters=[{"Name": "group-name", "Values": [name]}]
    )

    if not response["SecurityGroups"]:
        return None

    sg = response["SecurityGroups"][0]

    ports = []
    for perm in sg["IpPermissions"]:
        ports.append(perm.get("FromPort"))

    return {
        "group_id": sg["GroupId"],
        "ports": ports
    }