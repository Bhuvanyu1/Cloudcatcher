import json
from google.oauth2 import service_account
from googleapiclient.discovery import build


class GcpConnector:
    def list_instances(self, creds):
        project_id = creds.get("project_id")
        sa = creds.get("service_account_json")
        if isinstance(sa, str):
            sa = json.loads(sa)

        credentials = service_account.Credentials.from_service_account_info(sa)
        compute = build("compute", "v1", credentials=credentials, cache_discovery=False)

        req = compute.instances().aggregatedList(project=project_id)
        items = []
        while req is not None:
            resp = req.execute()
            for _, scoped_list in resp.get("items", {}).items():
                for inst in scoped_list.get("instances", []) or []:
                    nics = inst.get("networkInterfaces", []) or []
                    private_ip = None
                    public_ip = None
                    if nics:
                        private_ip = nics[0].get("networkIP")
                        access_configs = nics[0].get("accessConfigs", []) or []
                        if access_configs:
                            public_ip = access_configs[0].get("natIP")

                    items.append(
                        {
                            "provider": "gcp",
                            "account": project_id,
                            "region": inst.get("zone"),
                            "instance_id": inst.get("id"),
                            "name": inst.get("name"),
                            "size": inst.get("machineType"),
                            "state": inst.get("status"),
                            "public_ip": public_ip,
                            "private_ip": private_ip,
                            "tags": (inst.get("labels") or {}),
                            "raw": inst,
                        }
                    )
            req = compute.instances().aggregatedList_next(previous_request=req, previous_response=resp)
        return items
