"""
Real Cloud Provider Connectors for CloudWatcher
- AWS EC2 (boto3)
- Azure Virtual Machines (azure-mgmt-compute)
- GCP Compute Engine (google-cloud-compute)
- DigitalOcean Droplets (API calls)
"""
import os
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid
import aiohttp

logger = logging.getLogger(__name__)

# ==================== AWS EC2 CONNECTOR ====================

class AWSConnector:
    """AWS EC2 instance connector using boto3"""
    
    def __init__(self, credentials: Dict[str, str]):
        self.access_key_id = credentials.get("access_key_id")
        self.secret_access_key = credentials.get("secret_access_key")
        self.region = credentials.get("region", "us-east-1")
        self.regions = credentials.get("regions", [self.region])  # Can scan multiple regions
    
    async def list_instances(self, account_id: str) -> List[Dict]:
        """List all EC2 instances across specified regions"""
        import boto3
        
        instances = []
        
        try:
            for region in self.regions:
                ec2 = boto3.client(
                    'ec2',
                    aws_access_key_id=self.access_key_id,
                    aws_secret_access_key=self.secret_access_key,
                    region_name=region
                )
                
                # Use run_in_executor for async
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: ec2.describe_instances()
                )
                
                for reservation in response.get('Reservations', []):
                    for instance in reservation.get('Instances', []):
                        # Extract tags as dict
                        tags = {}
                        for tag in instance.get('Tags', []):
                            tags[tag.get('Key', '')] = tag.get('Value', '')
                        
                        # Get instance name from tags
                        name = tags.get('Name', '')
                        
                        normalized = {
                            "id": str(uuid.uuid4()),
                            "provider": "aws",
                            "cloud_account_id": account_id,
                            "region_or_zone": region,
                            "instance_id": instance.get('InstanceId'),
                            "name": name,
                            "instance_type_or_size": instance.get('InstanceType'),
                            "state": instance.get('State', {}).get('Name', 'unknown'),
                            "public_ip": instance.get('PublicIpAddress'),
                            "private_ip": instance.get('PrivateIpAddress'),
                            "tags": tags,
                            "raw": {
                                "launch_time": instance.get('LaunchTime').isoformat() if instance.get('LaunchTime') else None,
                                "vpc_id": instance.get('VpcId'),
                                "subnet_id": instance.get('SubnetId'),
                                "image_id": instance.get('ImageId'),
                                "architecture": instance.get('Architecture'),
                                "platform": instance.get('Platform', 'linux')
                            },
                            "first_seen_at": datetime.now(timezone.utc).isoformat(),
                            "last_seen_at": datetime.now(timezone.utc).isoformat(),
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }
                        instances.append(normalized)
                        
        except Exception as e:
            logger.error(f"AWS connector error: {str(e)}")
            raise Exception(f"Failed to fetch AWS instances: {str(e)}")
        
        return instances


# ==================== AZURE VM CONNECTOR ====================

class AzureConnector:
    """Azure Virtual Machine connector using azure-mgmt-compute"""
    
    def __init__(self, credentials: Dict[str, str]):
        self.tenant_id = credentials.get("tenant_id")
        self.client_id = credentials.get("client_id")
        self.client_secret = credentials.get("client_secret")
        self.subscription_id = credentials.get("subscription_id")
    
    async def list_instances(self, account_id: str) -> List[Dict]:
        """List all Azure VMs in the subscription"""
        from azure.identity import ClientSecretCredential
        from azure.mgmt.compute import ComputeManagementClient
        
        instances = []
        
        try:
            # Create credentials
            credential = ClientSecretCredential(
                tenant_id=self.tenant_id,
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            
            # Create compute client
            compute_client = ComputeManagementClient(
                credential=credential,
                subscription_id=self.subscription_id
            )
            
            # List all VMs
            loop = asyncio.get_event_loop()
            vms = await loop.run_in_executor(
                None,
                lambda: list(compute_client.virtual_machines.list_all())
            )
            
            for vm in vms:
                # Parse resource group and location from ID
                # /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Compute/virtualMachines/{name}
                parts = vm.id.split('/')
                resource_group = parts[4] if len(parts) > 4 else 'unknown'
                
                # Get instance view for power state
                try:
                    instance_view = await loop.run_in_executor(
                        None,
                        lambda rg=resource_group, n=vm.name: compute_client.virtual_machines.instance_view(rg, n)
                    )
                    power_state = "unknown"
                    for status in instance_view.statuses or []:
                        if status.code.startswith('PowerState/'):
                            power_state = status.code.replace('PowerState/', '')
                            break
                except:
                    power_state = "unknown"
                
                # Map Azure power state to common state
                state_map = {
                    "running": "running",
                    "deallocated": "stopped",
                    "stopped": "stopped",
                    "starting": "pending",
                    "stopping": "pending",
                    "deallocating": "pending"
                }
                
                # Extract tags
                tags = vm.tags or {}
                
                normalized = {
                    "id": str(uuid.uuid4()),
                    "provider": "azure",
                    "cloud_account_id": account_id,
                    "region_or_zone": vm.location,
                    "instance_id": vm.vm_id or vm.name,
                    "name": vm.name,
                    "instance_type_or_size": vm.hardware_profile.vm_size if vm.hardware_profile else None,
                    "state": state_map.get(power_state, power_state),
                    "public_ip": None,  # Would need network client to get this
                    "private_ip": None,
                    "tags": tags,
                    "raw": {
                        "resource_group": resource_group,
                        "os_type": vm.storage_profile.os_disk.os_type if vm.storage_profile and vm.storage_profile.os_disk else None,
                        "provisioning_state": vm.provisioning_state
                    },
                    "first_seen_at": datetime.now(timezone.utc).isoformat(),
                    "last_seen_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                instances.append(normalized)
                
        except Exception as e:
            logger.error(f"Azure connector error: {str(e)}")
            raise Exception(f"Failed to fetch Azure VMs: {str(e)}")
        
        return instances


# ==================== GCP COMPUTE CONNECTOR ====================

class GCPConnector:
    """GCP Compute Engine connector using google-cloud-compute"""
    
    def __init__(self, credentials: Dict[str, Any]):
        self.project_id = credentials.get("project_id")
        self.service_account_json = credentials.get("service_account_json")
        # Can be JSON string or dict
        if isinstance(self.service_account_json, str):
            try:
                self.service_account_json = json.loads(self.service_account_json)
            except:
                pass
    
    async def list_instances(self, account_id: str) -> List[Dict]:
        """List all GCP Compute Engine instances in the project"""
        from google.cloud import compute_v1
        from google.oauth2 import service_account
        
        instances = []
        
        try:
            # Create credentials from service account
            if self.service_account_json and isinstance(self.service_account_json, dict):
                credentials = service_account.Credentials.from_service_account_info(
                    self.service_account_json
                )
            else:
                # Use default credentials
                credentials = None
            
            # Create instance client
            if credentials:
                instance_client = compute_v1.InstancesClient(credentials=credentials)
            else:
                instance_client = compute_v1.InstancesClient()
            
            # List instances in all zones using aggregated list
            loop = asyncio.get_event_loop()
            request = compute_v1.AggregatedListInstancesRequest(project=self.project_id)
            
            agg_list = await loop.run_in_executor(
                None,
                lambda: instance_client.aggregated_list(request=request)
            )
            
            for zone, response in agg_list:
                if response.instances:
                    for instance in response.instances:
                        # Extract zone name from full path
                        zone_name = zone.replace('zones/', '')
                        
                        # Map GCP status to common state
                        status_map = {
                            "RUNNING": "running",
                            "TERMINATED": "terminated",
                            "STOPPED": "stopped",
                            "STAGING": "pending",
                            "PROVISIONING": "pending",
                            "SUSPENDING": "pending",
                            "SUSPENDED": "stopped"
                        }
                        
                        # Get IPs
                        public_ip = None
                        private_ip = None
                        for nic in instance.network_interfaces or []:
                            private_ip = nic.network_i_p
                            for access in nic.access_configs or []:
                                if access.nat_i_p:
                                    public_ip = access.nat_i_p
                                    break
                        
                        # Extract labels (GCP's tags)
                        labels = dict(instance.labels) if instance.labels else {}
                        
                        # Extract machine type name
                        machine_type = instance.machine_type.split('/')[-1] if instance.machine_type else None
                        
                        normalized = {
                            "id": str(uuid.uuid4()),
                            "provider": "gcp",
                            "cloud_account_id": account_id,
                            "region_or_zone": zone_name,
                            "instance_id": str(instance.id),
                            "name": instance.name,
                            "instance_type_or_size": machine_type,
                            "state": status_map.get(instance.status, instance.status.lower()),
                            "public_ip": public_ip,
                            "private_ip": private_ip,
                            "tags": labels,
                            "raw": {
                                "self_link": instance.self_link,
                                "creation_timestamp": instance.creation_timestamp,
                                "description": instance.description
                            },
                            "first_seen_at": datetime.now(timezone.utc).isoformat(),
                            "last_seen_at": datetime.now(timezone.utc).isoformat(),
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }
                        instances.append(normalized)
                        
        except Exception as e:
            logger.error(f"GCP connector error: {str(e)}")
            raise Exception(f"Failed to fetch GCP instances: {str(e)}")
        
        return instances


# ==================== DIGITALOCEAN CONNECTOR ====================

class DigitalOceanConnector:
    """DigitalOcean Droplets connector using REST API"""
    
    def __init__(self, credentials: Dict[str, str]):
        self.token = credentials.get("token")
        self.base_url = "https://api.digitalocean.com/v2"
    
    async def list_instances(self, account_id: str) -> List[Dict]:
        """List all DigitalOcean Droplets"""
        instances = []
        
        try:
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/droplets",
                    headers=headers
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"API error {response.status}: {error_text}")
                    
                    data = await response.json()
                    
                    for droplet in data.get('droplets', []):
                        # Get IPs
                        public_ip = None
                        private_ip = None
                        for network in droplet.get('networks', {}).get('v4', []):
                            if network.get('type') == 'public':
                                public_ip = network.get('ip_address')
                            elif network.get('type') == 'private':
                                private_ip = network.get('ip_address')
                        
                        # Map status
                        status_map = {
                            "active": "running",
                            "off": "stopped",
                            "new": "pending",
                            "archive": "terminated"
                        }
                        
                        # Extract tags
                        tags = {}
                        for tag in droplet.get('tags', []):
                            if ':' in tag:
                                key, value = tag.split(':', 1)
                                tags[key] = value
                            else:
                                tags[tag] = 'true'
                        
                        normalized = {
                            "id": str(uuid.uuid4()),
                            "provider": "do",
                            "cloud_account_id": account_id,
                            "region_or_zone": droplet.get('region', {}).get('slug'),
                            "instance_id": str(droplet.get('id')),
                            "name": droplet.get('name'),
                            "instance_type_or_size": droplet.get('size_slug'),
                            "state": status_map.get(droplet.get('status'), droplet.get('status')),
                            "public_ip": public_ip,
                            "private_ip": private_ip,
                            "tags": tags,
                            "raw": {
                                "image": droplet.get('image', {}).get('slug'),
                                "vcpus": droplet.get('vcpus'),
                                "memory": droplet.get('memory'),
                                "disk": droplet.get('disk'),
                                "created_at": droplet.get('created_at')
                            },
                            "first_seen_at": datetime.now(timezone.utc).isoformat(),
                            "last_seen_at": datetime.now(timezone.utc).isoformat(),
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }
                        instances.append(normalized)
                        
        except Exception as e:
            logger.error(f"DigitalOcean connector error: {str(e)}")
            raise Exception(f"Failed to fetch DigitalOcean droplets: {str(e)}")
        
        return instances


# ==================== CONNECTOR FACTORY ====================

def get_connector(provider: str, credentials: Dict[str, Any]):
    """Factory function to get the appropriate connector"""
    connectors = {
        "aws": AWSConnector,
        "azure": AzureConnector,
        "gcp": GCPConnector,
        "do": DigitalOceanConnector
    }
    
    connector_class = connectors.get(provider)
    if not connector_class:
        raise ValueError(f"Unknown provider: {provider}")
    
    return connector_class(credentials)


async def fetch_instances(provider: str, credentials: Dict[str, Any], account_id: str) -> List[Dict]:
    """Fetch instances from a cloud provider"""
    connector = get_connector(provider, credentials)
    return await connector.list_instances(account_id)
