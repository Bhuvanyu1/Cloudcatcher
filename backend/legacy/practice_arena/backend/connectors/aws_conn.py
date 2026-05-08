import boto3


class AwsConnector:
    def list_instances(self, creds):
        client = boto3.client(
            "ec2",
            aws_access_key_id=creds.get("access_key_id"),
            aws_secret_access_key=creds.get("secret_access_key"),
            region_name=creds.get("region"),
        )

        resp = client.describe_instances()
        items = []
        for reservation in resp.get("Reservations", []):
            for inst in reservation.get("Instances", []):
                tags_list = inst.get("Tags", []) or []
                tags = {t.get("Key"): t.get("Value") for t in tags_list if t.get("Key")}
                items.append(
                    {
                        "provider": "aws",
                        "account": None,
                        "region": creds.get("region"),
                        "instance_id": inst.get("InstanceId"),
                        "name": tags.get("Name"),
                        "size": inst.get("InstanceType"),
                        "state": (inst.get("State") or {}).get("Name"),
                        "public_ip": inst.get("PublicIpAddress"),
                        "private_ip": inst.get("PrivateIpAddress"),
                        "tags": tags,
                        "raw": inst,
                    }
                )
        return items
