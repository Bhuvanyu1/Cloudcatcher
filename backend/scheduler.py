"""
Scheduled Tasks for CloudWatcher using APScheduler
- Automatic inventory sync
- Recommendation generation
- Email notifications
"""
import os
import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

# Scheduler instance
scheduler: Optional[AsyncIOScheduler] = None

# Default sync interval (minutes)
DEFAULT_SYNC_INTERVAL = int(os.environ.get("SYNC_INTERVAL_MINUTES", "60"))


def get_scheduler() -> AsyncIOScheduler:
    """Get or create the scheduler instance"""
    global scheduler
    if scheduler is None:
        scheduler = AsyncIOScheduler(
            timezone="UTC",
            job_defaults={
                'coalesce': True,
                'max_instances': 1,
                'misfire_grace_time': 60
            }
        )
    return scheduler


async def scheduled_sync_job(db, email_service=None, notification_service=None):
    """
    Scheduled job to sync all cloud accounts
    This function will be called by the scheduler
    """
    from connectors import fetch_instances
    from server import generate_recommendations, log_audit_event
    
    logger.info("Starting scheduled sync...")
    
    try:
        # Get all enabled accounts
        accounts = await db.cloud_accounts.find(
            {"status": {"$ne": "disabled"}}
        ).to_list(100)
        
        if not accounts:
            logger.info("No accounts to sync")
            return
        
        total_instances = 0
        total_recommendations = 0
        errors = []
        
        for account in accounts:
            try:
                # Update status to syncing
                await db.cloud_accounts.update_one(
                    {"id": account["id"]},
                    {"$set": {
                        "status": "syncing",
                        "last_checked_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
                
                # Fetch instances using real connectors
                credentials = account.get("credentials", {})
                instances = await fetch_instances(
                    provider=account["provider"],
                    credentials=credentials,
                    account_id=account["id"]
                )
                
                # Clear old instances for this account
                await db.instances.delete_many({"cloud_account_id": account["id"]})
                
                # Insert new instances
                if instances:
                    await db.instances.insert_many(instances)
                
                # Generate recommendations
                recommendations = generate_recommendations(instances)
                
                # Clear old recommendations for this account
                await db.recommendations.delete_many({"cloud_account_id": account["id"]})
                
                # Insert new recommendations
                if recommendations:
                    await db.recommendations.insert_many(recommendations)
                    total_recommendations += len(recommendations)
                
                # Update account status
                await db.cloud_accounts.update_one(
                    {"id": account["id"]},
                    {"$set": {
                        "status": "connected",
                        "last_sync_at": datetime.now(timezone.utc).isoformat(),
                        "last_error": None,
                        "instance_count": len(instances)
                    }}
                )
                
                total_instances += len(instances)
                logger.info(f"Synced account {account['id']}: {len(instances)} instances")
                
            except Exception as e:
                error_msg = str(e)
                errors.append(f"{account.get('account_name', account['id'])}: {error_msg}")
                logger.error(f"Error syncing account {account['id']}: {error_msg}")
                
                await db.cloud_accounts.update_one(
                    {"id": account["id"]},
                    {"$set": {
                        "status": "error",
                        "last_error": error_msg
                    }}
                )
        
        # Log audit event
        await log_audit_event(
            db,
            "scheduled_sync.completed",
            "system",
            payload={
                "accounts_synced": len(accounts) - len(errors),
                "instances_found": total_instances,
                "recommendations_generated": total_recommendations,
                "errors": errors
            }
        )
        
        # Send email notifications if there are new high-severity recommendations
        if email_service and total_recommendations > 0:
            # Get admin users to notify
            admins = await db.users.find(
                {"role": {"$in": ["admin", "msp_admin"]}},
                {"_id": 0}
            ).to_list(100)
            
            # Get high severity recommendations
            high_severity = await db.recommendations.find(
                {"severity": "high", "status": "open"},
                {"_id": 0}
            ).to_list(20)
            
            if high_severity:
                for admin in admins:
                    if admin.get("settings", {}).get("email_notifications", True):
                        await email_service.send_alert_notification(
                            to=admin["email"],
                            name=admin["name"],
                            alerts=high_severity[:5]  # Send top 5
                        )
        
        # Send Slack/Teams notifications for high severity recommendations
        if notification_service and total_recommendations > 0:
            high_severity_count = len(
                await db.recommendations.find(
                    {"severity": "high", "status": "open"},
                    {"_id": 0}
                ).to_list(100)
            )
            if high_severity_count > 0:
                await notification_service.send_recommendation_summary(
                    total_recommendations=total_recommendations,
                    high_severity_count=high_severity_count,
                    accounts_synced=len(accounts) - len(errors)
                )
        
        logger.info(f"Scheduled sync completed: {total_instances} instances, {total_recommendations} recommendations")
        
    except Exception as e:
        logger.error(f"Scheduled sync failed: {str(e)}")


async def log_audit_event(db, event_type: str, entity_type: str, entity_id: str = None, payload: dict = None):
    """Log an audit event (helper for scheduler)"""
    import uuid
    event = {
        "id": str(uuid.uuid4()),
        "event_type": event_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "payload": payload or {},
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.audit_events.insert_one(event)


def setup_scheduler(db, email_service=None, notification_service=None, sync_interval_minutes: int = None):
    """
    Setup and start the scheduler with default jobs
    
    Args:
        db: MongoDB database instance
        email_service: Optional email service for notifications
        notification_service: Optional Slack/Teams notification service
        sync_interval_minutes: Sync interval in minutes (default: 60)
    """
    global scheduler
    
    interval = sync_interval_minutes or DEFAULT_SYNC_INTERVAL
    sched = get_scheduler()
    
    # Add scheduled sync job
    sched.add_job(
        scheduled_sync_job,
        trigger=IntervalTrigger(minutes=interval),
        args=[db, email_service, notification_service],
        id="scheduled_sync",
        name="Scheduled Inventory Sync",
        replace_existing=True
    )
    
    # You can also add cron-based jobs
    # Example: Run daily at 2 AM UTC
    # sched.add_job(
    #     scheduled_sync_job,
    #     trigger=CronTrigger(hour=2, minute=0),
    #     args=[db, email_service],
    #     id="daily_sync",
    #     name="Daily Inventory Sync",
    #     replace_existing=True
    # )
    
    logger.info(f"Scheduler configured: sync every {interval} minutes")
    
    return sched


def start_scheduler():
    """Start the scheduler"""
    global scheduler
    if scheduler and not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")


def stop_scheduler():
    """Stop the scheduler"""
    global scheduler
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


def get_scheduled_jobs():
    """Get list of scheduled jobs"""
    global scheduler
    if not scheduler:
        return []
    
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger)
        })
    
    return jobs


def trigger_job_now(job_id: str):
    """Manually trigger a scheduled job"""
    global scheduler
    if not scheduler:
        raise Exception("Scheduler not initialized")
    
    job = scheduler.get_job(job_id)
    if not job:
        raise Exception(f"Job not found: {job_id}")
    
    # Run the job immediately
    job.modify(next_run_time=datetime.now(timezone.utc))
    
    return {"success": True, "message": f"Job {job_id} triggered"}
