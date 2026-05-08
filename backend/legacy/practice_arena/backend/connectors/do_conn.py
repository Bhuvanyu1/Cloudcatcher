import requests


class DoConnector:
    def list_instances(self, creds):
        token = creds.get("token")
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get("https://api.digitalocean.com/v2/droplets", headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        items = []
        for droplet in data.get("droplets", []):
            networks = droplet.get("networks", {}).get("v4", [])
            public_ip = None
            private_ip = None
            for net in networks:
                if net.get("type") == "public":
                    public_ip = net.get("ip_address")
                elif net.get("type") == "private":
                    private_ip = net.get("ip_address")

            items.append(
                {
                    "provider": "do",
                    "account": None,
                    "region": (droplet.get("region") or {}).get("slug"),
                    "instance_id": str(droplet.get("id")),
                    "name": droplet.get("name"),
                    "size": droplet.get("size_slug"),
                    "state": droplet.get("status"),
                    "public_ip": public_ip,
                    "private_ip": private_ip,
                    "tags": {"tags": droplet.get("tags", [])},
                    "raw": droplet,
                }
            )
        return items
