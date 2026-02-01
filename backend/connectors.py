from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import boto3
from azure.identity import ClientSecretCredential
from azure.mgmt.compute import ComputeManagementClient
from google.cloud import compute_v1
from digitalocean import Manager


class CloudConnector:
    """Base class for all cloud connectors."""

    async def list_instances(self) -> List[Dict[str, Any]]:
        raise NotImplementedError


class AWSConnector(CloudConnector):
    def __init__(self, access_key: str, secret_key: str, region: str, account_id: str):
        self.account_id = account_id
        session = boto3.session.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )
        self.ec2_client = session.client("ec2")

    async def list_instances(self) -> List[Dict[str, Any]]:
        response = await asyncio.to_thread(self.ec2_client.describe_instances)
        instances: List[Dict[str, Any]] = []
        for reservation in response.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                tags = {tag.get("Key"): tag.get("Value") for tag in instance.get("Tags", []) if tag.get("Key")}
                name = tags.get("Name")
                now = datetime.now(timezone.utc).isoformat()
                instances.append(
                    {
                        "id": str(uuid.uuid4()),
                        "provider": "aws",
                        "cloud_account_id": self.account_id,
                        "region_or_zone": instance.get("Placement", {}).get("AvailabilityZone"),
                        "instance_id": instance.get("InstanceId"),
                        "name": name,
                        "instance_type_or_size": instance.get("InstanceType"),
                        "state": instance.get("State", {}).get("Name"),
                        "public_ip": instance.get("PublicIpAddress"),
                        "private_ip": instance.get("PrivateIpAddress"),
                        "tags": tags,
                        "raw": instance,
                        "first_seen_at": now,
                        "last_seen_at": now,
                        "updated_at": now,
                    }
                )
        return instances


class AzureConnector(CloudConnector):
    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        subscription_id: str,
        account_id: str,
    ):
        self.account_id = account_id
        credential = ClientSecretCredential(tenant_id=tenant_id, client_id=client_id, client_secret=client_secret)
        self.compute_client = ComputeManagementClient(credential, subscription_id)

    async def list_instances(self) -> List[Dict[str, Any]]:
        vms = await asyncio.to_thread(lambda: list(self.compute_client.virtual_machines.list_all()))
        instances: List[Dict[str, Any]] = []
        now = datetime.now(timezone.utc).isoformat()
        for vm in vms:
            instances.append(
                {
                    "id": str(uuid.uuid4()),
                    "provider": "azure",
                    "cloud_account_id": self.account_id,
                    "region_or_zone": getattr(vm, "location", None),
                    "instance_id": getattr(vm, "id", None),
                    "name": getattr(vm, "name", None),
                    "instance_type_or_size": getattr(getattr(vm, "hardware_profile", None), "vm_size", None),
                    "state": None,
                    "public_ip": None,
                    "private_ip": None,
                    "tags": getattr(vm, "tags", {}) or {},
                    "raw": vm.as_dict() if hasattr(vm, "as_dict") else {},
                    "first_seen_at": now,
                    "last_seen_at": now,
                    "updated_at": now,
                }
            )
        return instances


class GCPConnector(CloudConnector):
    def __init__(self, project_id: str, service_account_json: str, account_id: str):
        self.project_id = project_id
        self.account_id = account_id
        self.client = compute_v1.InstancesClient.from_service_account_json(service_account_json)

    async def list_instances(self) -> List[Dict[str, Any]]:
        request = compute_v1.AggregatedListInstancesRequest(project=self.project_id)
        response = await asyncio.to_thread(lambda: list(self.client.aggregated_list(request=request)))
        instances: List[Dict[str, Any]] = []
        now = datetime.now(timezone.utc).isoformat()
        for _, scoped_list in response:
            for instance in scoped_list.instances or []:
                network_interfaces = instance.network_interfaces or []
                public_ip = None
                private_ip = None
                if network_interfaces:
                    private_ip = network_interfaces[0].network_ip
                    for access_config in network_interfaces[0].access_configs or []:
                        if access_config.nat_i_p:
                            public_ip = access_config.nat_i_p
                            break
                instances.append(
                    {
                        "id": str(uuid.uuid4()),
                        "provider": "gcp",
                        "cloud_account_id": self.account_id,
                        "region_or_zone": instance.zone.split("/")[-1] if instance.zone else None,
                        "instance_id": instance.id,
                        "name": instance.name,
                        "instance_type_or_size": instance.machine_type.split("/")[-1] if instance.machine_type else None,
                        "state": instance.status.lower() if instance.status else None,
                        "public_ip": public_ip,
                        "private_ip": private_ip,
                        "tags": {"items": instance.tags.items} if instance.tags and instance.tags.items else {},
                        "raw": instance.to_dict() if hasattr(instance, "to_dict") else {},
                        "first_seen_at": now,
                        "last_seen_at": now,
                        "updated_at": now,
                    }
                )
        return instances


class DigitalOceanConnector(CloudConnector):
    def __init__(self, token: str, account_id: str):
        self.account_id = account_id
        self.manager = Manager(token=token)

    async def list_instances(self) -> List[Dict[str, Any]]:
        droplets = await asyncio.to_thread(self.manager.get_all_droplets)
        instances: List[Dict[str, Any]] = []
        now = datetime.now(timezone.utc).isoformat()
        for droplet in droplets:
            public_ip = None
            private_ip = None
            networks = getattr(droplet, "networks", {}) or {}
            for network in networks.get("v4", []) or []:
                if network.get("type") == "public":
                    public_ip = network.get("ip_address")
                elif network.get("type") == "private":
                    private_ip = network.get("ip_address")
            instances.append(
                {
                    "id": str(uuid.uuid4()),
                    "provider": "do",
                    "cloud_account_id": self.account_id,
                    "region_or_zone": getattr(getattr(droplet, "region", None), "slug", None),
                    "instance_id": getattr(droplet, "id", None),
                    "name": getattr(droplet, "name", None),
                    "instance_type_or_size": getattr(droplet, "size_slug", None),
                    "state": getattr(droplet, "status", None),
                    "public_ip": public_ip,
                    "private_ip": private_ip,
                    "tags": {"items": getattr(droplet, "tags", []) or []},
                    "raw": droplet.__dict__,
                    "first_seen_at": now,
                    "last_seen_at": now,
                    "updated_at": now,
                }
            )
        return instances
