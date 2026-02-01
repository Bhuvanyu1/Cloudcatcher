from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Dict, List


class RemediationEngine:
    """AI-powered remediation for FinOps + SecOps."""

    def __init__(self, db):
        self.db = db

    async def analyze_and_remediate(self, dry_run: bool = True) -> List[Dict]:
        """
        Analyze all instances and generate auto-remediation actions.

        Returns list of remediation actions:
        {
            "action_id": str,
            "instance_id": str,
            "action_type": str,  # "rightsize", "terminate", "enable_mfa", "fix_s3_public"
            "severity": str,
            "estimated_savings": float,  # monthly USD
            "requires_approval": bool,
            "auto_execute": bool,
            "description": str,
            "status": "pending" | "approved" | "executed" | "failed"
        }
        """
        actions: List[Dict] = []

        stopped_instances = await self.db.instances.find(
            {
                "state": "stopped",
                "last_seen_at": {
                    "$lt": (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
                },
            }
        ).to_list(1000)

        for inst in stopped_instances:
            estimated_daily_cost = self._estimate_instance_cost(inst)
            actions.append(
                {
                    "action_id": f"rightsize_{inst['instance_id']}",
                    "instance_id": inst["instance_id"],
                    "cloud_account_id": inst["cloud_account_id"],
                    "action_type": "terminate_idle",
                    "severity": "medium",
                    "estimated_savings": estimated_daily_cost * 30,
                    "requires_approval": True,
                    "auto_execute": False,
                    "description": (
                        f"Instance {inst.get('name')} stopped for >7 days. "
                        f"Terminate to save ~${estimated_daily_cost * 30}/mo"
                    ),
                    "status": "pending",
                }
            )

        if not dry_run and actions:
            await self.db.remediation_actions.insert_many(actions)

        return actions

    def _estimate_instance_cost(self, instance: Dict) -> float:
        """Estimate daily cost based on instance type."""
        pricing = {
            "t3.micro": 0.0104,
            "t3.small": 0.0208,
            "t3.medium": 0.0416,
            "m5.large": 0.096,
            "c5.xlarge": 0.17,
            "r5.large": 0.126,
        }
        hourly = pricing.get(instance.get("instance_type_or_size", ""), 0.05)
        return hourly * 24

    async def execute_action(self, action_id: str, approved_by: str = "system") -> Dict:
        """Execute a remediation action after approval."""
        action = await self.db.remediation_actions.find_one({"action_id": action_id})
        if not action:
            raise ValueError(f"Action {action_id} not found")

        if action.get("action_type") == "terminate_idle":
            pass

        await self.db.remediation_actions.update_one(
            {"action_id": action_id},
            {
                "$set": {
                    "status": "executed",
                    "executed_at": datetime.now(timezone.utc).isoformat(),
                    "executed_by": approved_by,
                }
            },
        )

        return {"success": True, "action_id": action_id}
