import os
import logging
from typing import Optional, Dict, Any
import httpx

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self) -> None:
        self.slack_webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
        self.teams_webhook_url = os.environ.get("TEAMS_WEBHOOK_URL")

        self.slack_enabled = bool(self.slack_webhook_url)
        self.teams_enabled = bool(self.teams_webhook_url)

        if not self.slack_enabled:
            logger.warning("Slack notifications disabled: SLACK_WEBHOOK_URL not set")
        if not self.teams_enabled:
            logger.warning("Teams notifications disabled: TEAMS_WEBHOOK_URL not set")

    async def send_slack_message(self, text: str, context: Optional[Dict[str, Any]] = None) -> dict:
        if not self.slack_enabled:
            return {"success": False, "message": "Slack notifications disabled"}

        payload: Dict[str, Any] = {"text": text}
        if context:
            payload["attachments"] = [{"fields": self._format_fields(context)}]

        return await self._post_webhook(self.slack_webhook_url, payload, "slack")

    async def send_teams_message(self, text: str, context: Optional[Dict[str, Any]] = None) -> dict:
        if not self.teams_enabled:
            return {"success": False, "message": "Teams notifications disabled"}

        payload: Dict[str, Any] = {"text": text}
        if context:
            payload["sections"] = [
                {"facts": self._format_teams_facts(context)}
            ]

        return await self._post_webhook(self.teams_webhook_url, payload, "teams")

    async def send_recommendation_summary(
        self,
        total_recommendations: int,
        high_severity_count: int,
        accounts_synced: int
    ) -> dict:
        text = (
            "CloudWatcher scheduled sync completed.\n"
            f"Accounts synced: {accounts_synced}\n"
            f"Recommendations generated: {total_recommendations}\n"
            f"High severity recommendations: {high_severity_count}"
        )
        context = {
            "accounts_synced": accounts_synced,
            "recommendations_generated": total_recommendations,
            "high_severity_recommendations": high_severity_count
        }

        results = {}
        if self.slack_enabled:
            results["slack"] = await self.send_slack_message(text, context)
        if self.teams_enabled:
            results["teams"] = await self.send_teams_message(text, context)

        if not results:
            return {"success": False, "message": "No notification channels enabled"}

        return {"success": True, "results": results}

    async def _post_webhook(self, url: Optional[str], payload: Dict[str, Any], channel: str) -> dict:
        if not url:
            return {"success": False, "message": f"{channel.title()} webhook URL not configured"}

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, json=payload)
        if response.status_code >= 400:
            logger.error(
                "Failed to send %s notification: %s - %s",
                channel,
                response.status_code,
                response.text
            )
            return {"success": False, "status": response.status_code, "message": response.text}
        return {"success": True, "status": response.status_code}

    @staticmethod
    def _format_fields(context: Dict[str, Any]) -> list:
        return [{"title": key.replace("_", " ").title(), "value": str(value), "short": True} for key, value in context.items()]

    @staticmethod
    def _format_teams_facts(context: Dict[str, Any]) -> list:
        return [{"name": key.replace("_", " ").title(), "value": str(value)} for key, value in context.items()]


notification_service = NotificationService()
