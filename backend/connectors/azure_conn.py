from azure.identity import ClientSecretCredential
from azure.mgmt.compute import ComputeManagementClient


class AzureConnector:
    def list_instances(self, creds):
        credential = ClientSecretCredential(
            tenant_id=creds.get("tenant_id"),
            client_id=creds.get("client_id"),
            client_secret=creds.get("client_secret"),
        )
        subscription_id = creds.get("subscription_id")
        client = ComputeManagementClient(credential, subscription_id)

        items = []
        for vm in client.virtual_machines.list_all():
            items.append(
                {
                    "provider": "azure",
                    "account": subscription_id,
                    "region": vm.location,
                    "instance_id": vm.id,
                    "name": vm.name,
                    "size": (vm.hardware_profile.vm_size if vm.hardware_profile else None),
                    "state": None,
                    "public_ip": None,
                    "private_ip": None,
                    "tags": vm.tags or {},
                    "raw": vm.as_dict(),
                }
            )
        return items
