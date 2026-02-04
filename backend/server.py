from fastapi import FastAPI, APIRouter, HTTPException, Query, Depends, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Set
import uuid
from datetime import datetime, timezone, timedelta
from enum import Enum
from remediation import RemediationEngine
from credentials_encryption import encrypt_credentials, decrypt_credentials
from wafr import WAFREngine
from email_service import email_service
from notification_service import notification_service

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI(title="Cloud Watcher API", version="2.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Initialize auth service (will be set after db initialization)
auth_service = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== WEBSOCKET MANAGER ====================

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
    
    async def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
    
    async def send_to_user(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except:
                    pass
    
    async def broadcast(self, message: dict):
        for connections in self.active_connections.values():
            for connection in connections:
                try:
                    await connection.send_json(message)
                except:
                    pass

ws_manager = WebSocketManager()

# ==================== ENUMS ====================

class CloudProvider(str, Enum):
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    DIGITALOCEAN = "do"

class AccountStatus(str, Enum):
    CONNECTED = "connected"
    ERROR = "error"
    DISABLED = "disabled"
    SYNCING = "syncing"

class RecommendationCategory(str, Enum):
    FINOPS = "finops"
    SECOPS = "secops"

class RecommendationSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class RecommendationStatus(str, Enum):
    OPEN = "open"
    DISMISSED = "dismissed"
    RESOLVED = "resolved"

# ==================== AUTH MODELS ====================

class UserRegister(BaseModel):
    email: str
    password: str
    name: str
    organization_name: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class TokenRefresh(BaseModel):
    refresh_token: str

class PasswordReset(BaseModel):
    token: str
    new_password: str


class NotificationTestRequest(BaseModel):
    channel: str = "all"
    message: Optional[str] = None

class User(BaseModel):
    id: str
    email: str
    name: str
    role: str
    organization_id: Optional[str] = None
    email_verified: bool = False
    created_at: str
    last_login_at: Optional[str] = None

class Organization(BaseModel):
    id: str
    name: str
    created_at: str
    settings: Dict[str, Any] = {}

class Tenant(BaseModel):
    id: str
    name: str
    msp_organization_id: str
    settings: Dict[str, Any] = {}
    status: str = "active"
    created_at: str

# ==================== MODELS ====================

class CloudAccountCreate(BaseModel):
    provider: CloudProvider
    account_name: Optional[str] = None
    credentials: Dict[str, Any]

class CloudAccountUpdate(BaseModel):
    account_name: Optional[str] = None
    credentials: Optional[Dict[str, Any]] = None
    status: Optional[AccountStatus] = None

class CloudAccount(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    provider: CloudProvider
    account_name: Optional[str] = None
    account_identifier: Optional[str] = None
    status: AccountStatus = AccountStatus.CONNECTED
    last_checked_at: Optional[str] = None
    last_sync_at: Optional[str] = None
    last_error: Optional[str] = None
    instance_count: int = 0
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class Instance(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    provider: CloudProvider
    cloud_account_id: str
    region_or_zone: Optional[str] = None
    instance_id: str
    name: Optional[str] = None
    instance_type_or_size: Optional[str] = None
    state: Optional[str] = None
    public_ip: Optional[str] = None
    private_ip: Optional[str] = None
    tags: Dict[str, str] = Field(default_factory=dict)
    raw: Dict[str, Any] = Field(default_factory=dict)
    first_seen_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_seen_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class Recommendation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    provider: Optional[CloudProvider] = None
    cloud_account_id: Optional[str] = None
    resource_type: str = "instance"
    resource_id: Optional[str] = None
    category: RecommendationCategory
    rule_id: str
    severity: RecommendationSeverity
    title: str
    description: str
    evidence: Dict[str, Any] = Field(default_factory=dict)
    status: RecommendationStatus = RecommendationStatus.OPEN
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class AuditEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    entity_type: str
    entity_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class DashboardStats(BaseModel):
    total_instances: int = 0
    total_accounts: int = 0
    accounts_by_provider: Dict[str, int] = Field(default_factory=dict)
    instances_by_provider: Dict[str, int] = Field(default_factory=dict)
    instances_by_state: Dict[str, int] = Field(default_factory=dict)
    open_recommendations: int = 0
    finops_recommendations: int = 0
    secops_recommendations: int = 0
    correlated_alerts: List[Dict[str, Any]] = Field(default_factory=list)
    last_sync: Optional[str] = None

class SyncResult(BaseModel):
    success: bool
    accounts_synced: int
    instances_found: int
    errors: List[str] = Field(default_factory=list)
    timestamp: str

# ==================== MOCK DATA GENERATOR ====================

def generate_mock_instances(account_id: str, provider: CloudProvider, count: int = 5) -> List[Dict]:
    """Generate mock instance data for demo purposes"""
    import random
    
    regions = {
        CloudProvider.AWS: ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"],
        CloudProvider.AZURE: ["eastus", "westus2", "westeurope", "southeastasia"],
        CloudProvider.GCP: ["us-central1-a", "us-east1-b", "europe-west1-b", "asia-east1-a"],
        CloudProvider.DIGITALOCEAN: ["nyc1", "sfo3", "lon1", "sgp1"]
    }
    
    instance_types = {
        CloudProvider.AWS: ["t3.micro", "t3.small", "t3.medium", "m5.large", "c5.xlarge", "r5.large"],
        CloudProvider.AZURE: ["Standard_B1s", "Standard_B2s", "Standard_D2s_v3", "Standard_E2s_v3"],
        CloudProvider.GCP: ["e2-micro", "e2-small", "e2-medium", "n1-standard-1", "n2-standard-2"],
        CloudProvider.DIGITALOCEAN: ["s-1vcpu-1gb", "s-1vcpu-2gb", "s-2vcpu-2gb", "s-2vcpu-4gb"]
    }
    
    states = ["running", "stopped", "pending", "terminated"]
    state_weights = [0.6, 0.25, 0.1, 0.05]
    
    names = [
        "web-server", "api-gateway", "db-primary", "db-replica", "cache-server",
        "worker-node", "monitoring", "logging", "bastion", "load-balancer",
        "app-server", "batch-processor", "scheduler", "proxy", "nat-gateway"
    ]
    
    instances = []
    for i in range(count):
        state = random.choices(states, weights=state_weights)[0]
        region = random.choice(regions[provider])
        instance_type = random.choice(instance_types[provider])
        name = f"{random.choice(names)}-{random.randint(1, 99):02d}"
        
        instance = {
            "id": str(uuid.uuid4()),
            "provider": provider.value,
            "cloud_account_id": account_id,
            "region_or_zone": region,
            "instance_id": f"i-{uuid.uuid4().hex[:12]}",
            "name": name,
            "instance_type_or_size": instance_type,
            "state": state,
            "public_ip": f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}" if state == "running" and random.random() > 0.3 else None,
            "private_ip": f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}",
            "tags": {
                "environment": random.choice(["production", "staging", "development"]),
                "team": random.choice(["platform", "backend", "frontend", "devops", "data"]),
                "cost_center": f"cc-{random.randint(100, 999)}"
            },
            "raw": {},
            "first_seen_at": datetime.now(timezone.utc).isoformat(),
            "last_seen_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        instances.append(instance)
    
    return instances

def generate_recommendations(instances: List[Dict]) -> List[Dict]:
    """Generate mock FinOps and SecOps recommendations"""
    recommendations = []
    
    for instance in instances:
        # FinOps: Idle/Stopped instance
        if instance.get("state") == "stopped":
            recommendations.append({
                "id": str(uuid.uuid4()),
                "provider": instance["provider"],
                "cloud_account_id": instance["cloud_account_id"],
                "resource_type": "instance",
                "resource_id": instance["instance_id"],
                "category": "finops",
                "rule_id": "FINOPS-001",
                "severity": "medium",
                "title": "Stopped Instance Incurring Storage Costs",
                "description": f"Instance {instance['name']} has been stopped but is still incurring storage costs. Consider terminating if no longer needed.",
                "evidence": {
                    "instance_name": instance["name"],
                    "region": instance["region_or_zone"],
                    "state": instance["state"]
                },
                "status": "open",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            })
        
        # SecOps: Public IP exposure
        if instance.get("public_ip"):
            recommendations.append({
                "id": str(uuid.uuid4()),
                "provider": instance["provider"],
                "cloud_account_id": instance["cloud_account_id"],
                "resource_type": "instance",
                "resource_id": instance["instance_id"],
                "category": "secops",
                "rule_id": "SECOPS-001",
                "severity": "high" if instance.get("tags", {}).get("environment") == "production" else "medium",
                "title": "Instance with Public IP Exposure",
                "description": f"Instance {instance['name']} has a public IP ({instance['public_ip']}). Verify this is intentional and security groups are properly configured.",
                "evidence": {
                    "instance_name": instance["name"],
                    "public_ip": instance["public_ip"],
                    "environment": instance.get("tags", {}).get("environment", "unknown")
                },
                "status": "open",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            })
        
        # FinOps: Large instance type
        large_types = ["xlarge", "2xlarge", "large", "Standard_E", "n2-standard"]
        if any(lt in str(instance.get("instance_type_or_size", "")) for lt in large_types):
            if instance.get("tags", {}).get("environment") != "production":
                recommendations.append({
                    "id": str(uuid.uuid4()),
                    "provider": instance["provider"],
                    "cloud_account_id": instance["cloud_account_id"],
                    "resource_type": "instance",
                    "resource_id": instance["instance_id"],
                    "category": "finops",
                    "rule_id": "FINOPS-002",
                    "severity": "low",
                    "title": "Large Instance in Non-Production Environment",
                    "description": f"Instance {instance['name']} uses {instance['instance_type_or_size']} in {instance.get('tags', {}).get('environment', 'unknown')}. Consider rightsizing.",
                    "evidence": {
                        "instance_name": instance["name"],
                        "instance_type": instance["instance_type_or_size"],
                        "environment": instance.get("tags", {}).get("environment", "unknown")
                    },
                    "status": "open",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                })
    
    return recommendations

# ==================== HELPER FUNCTIONS ====================

async def log_audit_event(event_type: str, entity_type: str, entity_id: str = None, payload: Dict = None):
    """Log an audit event"""
    event = {
        "id": str(uuid.uuid4()),
        "event_type": event_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "payload": payload or {},
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.audit_events.insert_one(event)

# ==================== ANOMALY DETECTION ====================

async def detect_anomalies(instances: List[Dict], previous_instances: List[Dict] = None) -> List[Dict]:
    """Basic anomaly detection for inventory changes"""
    anomalies = []
    
    # Group current instances by provider and region
    current_by_region = {}
    for inst in instances:
        key = f"{inst.get('provider')}:{inst.get('region_or_zone')}"
        current_by_region[key] = current_by_region.get(key, 0) + 1
    
    # Count instances with public IPs
    public_ip_count = sum(1 for inst in instances if inst.get('public_ip'))
    
    # Anomaly: High number of instances with public IPs (>50%)
    if instances and public_ip_count / len(instances) > 0.5:
        anomalies.append({
            "id": str(uuid.uuid4()),
            "alert_type": "high_public_exposure",
            "severity": "high",
            "payload": {
                "public_ip_count": public_ip_count,
                "total_instances": len(instances),
                "percentage": round(public_ip_count / len(instances) * 100, 1)
            },
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    # Anomaly: New region detected (would compare with previous sync)
    # This is a placeholder - in production, compare with historical data
    
    return anomalies

# ==================== CORRELATED ALERTS ====================

async def fetch_correlated_alerts(limit: int = 100) -> List[Dict[str, Any]]:
    """Find instances with both cost anomalies and security issues"""
    problematic = await db.instances.find(
        {"state": "stopped", "public_ip": {"$ne": None}},
        {"_id": 0}
    ).to_list(limit)

    alerts = []
    for inst in problematic:
        finops_rec = await db.recommendations.find_one({
            "resource_id": inst["instance_id"],
            "category": "finops",
            "status": "open"
        })

        secops_rec = await db.recommendations.find_one({
            "resource_id": inst["instance_id"],
            "category": "secops",
            "status": "open"
        })

        if finops_rec and secops_rec:
            alerts.append({
                "id": inst["instance_id"],
                "title": f"Instance {inst.get('name') or inst['instance_id']} has BOTH cost and security issues",
                "description": f"FinOps: {finops_rec['title']}. SecOps: {secops_rec['title']}",
                "cost_impact": 5.0,
                "security_severity": secops_rec["severity"],
                "instance": inst
            })

    return alerts

# ==================== ALERTS ENDPOINTS ====================

class Alert(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    provider: Optional[str] = None
    cloud_account_id: Optional[str] = None
    alert_type: str
    severity: str
    resource_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class WebhookAlert(BaseModel):
    source: str
    alert_type: str
    severity: str = "medium"
    resource_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)

@api_router.get("/alerts", response_model=List[Alert])
async def list_alerts(
    alert_type: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = Query(default=50, le=200)
):
    """Get alerts from anomaly detection and webhook ingestion"""
    query = {}
    if alert_type:
        query["alert_type"] = alert_type
    if severity:
        query["severity"] = severity
    
    alerts = await db.alerts.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return alerts

@api_router.post("/alerts/webhook", response_model=Alert)
async def ingest_webhook_alert(alert_data: WebhookAlert):
    """Ingest external alerts via webhook"""
    alert = Alert(
        alert_type=alert_data.alert_type,
        severity=alert_data.severity,
        resource_id=alert_data.resource_id,
        payload={**alert_data.payload, "source": alert_data.source}
    )
    
    doc = alert.model_dump()
    await db.alerts.insert_one(doc)
    
    await log_audit_event("alert.ingested", "alert", alert.id, {"source": alert_data.source})
    
    return alert

@api_router.post("/alerts/detect")
async def run_anomaly_detection():
    """Run anomaly detection on current inventory"""
    instances = await db.instances.find({}, {"_id": 0}).to_list(1000)
    
    anomalies = await detect_anomalies(instances)
    
    # Store detected anomalies as alerts
    for anomaly in anomalies:
        await db.alerts.insert_one(anomaly)
    
    await log_audit_event("anomaly_detection.completed", "system", payload={"alerts_generated": len(anomalies)})
    
    return {"success": True, "anomalies_detected": len(anomalies), "alerts": anomalies}

# ==================== API ENDPOINTS ====================

@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"ok": True, "timestamp": datetime.now(timezone.utc).isoformat(), "version": "2.0.0"}

# ----- Authentication -----

@api_router.post("/auth/register")
async def register_user(data: UserRegister):
    """Register a new user"""
    global auth_service
    if not auth_service:
        auth_service = AuthService(db)
    
    result = await auth_service.register_user(
        email=data.email,
        password=data.password,
        name=data.name,
        organization_name=data.organization_name
    )
    
    await log_audit_event("user.registered", "user", result["id"], {"email": data.email})
    
    return result

@api_router.post("/auth/login")
async def login_user(data: UserLogin):
    """Login with email and password"""
    global auth_service
    if not auth_service:
        auth_service = AuthService(db)
    
    result = await auth_service.login(data.email, data.password)
    
    await log_audit_event("user.login", "user", result["user"]["id"], {"email": data.email})
    
    return result

@api_router.post("/auth/logout")
async def logout_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    refresh_token: Optional[str] = None
):
    """Logout and invalidate tokens"""
    global auth_service
    if not auth_service:
        auth_service = AuthService(db)
    
    if credentials:
        await auth_service.logout(credentials.credentials, refresh_token)
    
    return {"success": True, "message": "Logged out"}

@api_router.post("/auth/refresh")
async def refresh_tokens(data: TokenRefresh):
    """Refresh access token"""
    global auth_service
    if not auth_service:
        auth_service = AuthService(db)
    
    return await auth_service.refresh_tokens(data.refresh_token)

@api_router.post("/auth/verify-email")
async def verify_email(token: str):
    """Verify email address"""
    global auth_service
    if not auth_service:
        auth_service = AuthService(db)
    
    return await auth_service.verify_email(token)

@api_router.post("/auth/request-password-reset")
async def request_password_reset(email: str):
    """Request password reset"""
    global auth_service
    if not auth_service:
        auth_service = AuthService(db)
    
    return await auth_service.request_password_reset(email)

@api_router.post("/auth/reset-password")
async def reset_password(data: PasswordReset):
    """Reset password with token"""
    global auth_service
    if not auth_service:
        auth_service = AuthService(db)
    
    return await auth_service.reset_password(data.token, data.new_password)

@api_router.get("/auth/me")
async def get_current_user_profile(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get current user profile"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = await get_current_user(credentials)
    
    # Fetch full user details
    user_doc = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password": 0})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user_doc

# ----- Users (Admin) -----

@api_router.get("/users")
async def list_users(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    limit: int = Query(default=50, le=200)
):
    """List users in organization (Admin only)"""
    current_user = await get_current_user(credentials)
    
    if current_user["role"] not in ["admin", "msp_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = {}
    if current_user.get("organization_id"):
        query["organization_id"] = current_user["organization_id"]
    
    users = await db.users.find(query, {"_id": 0, "password": 0}).limit(limit).to_list(limit)
    return users

@api_router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Delete a user (Admin only)"""
    current_user = await get_current_user(credentials)
    
    if current_user["role"] not in ["admin", "msp_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Cannot delete yourself
    if current_user["id"] == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    result = await db.users.delete_one({"id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    await log_audit_event("user.deleted", "user", user_id, {"deleted_by": current_user["id"]})
    
    return {"success": True}

# ----- WebSocket -----

@api_router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time updates"""
    await ws_manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, user_id)

# ----- Cloud Accounts -----

@api_router.post("/cloud-accounts", response_model=CloudAccount)
async def create_cloud_account(input_data: CloudAccountCreate):
    """Create a new cloud account connection"""
    account = CloudAccount(
        provider=input_data.provider,
        account_name=input_data.account_name or f"{input_data.provider.value}-account",
        account_identifier=input_data.credentials.get("account_id") or input_data.credentials.get("project_id") or input_data.credentials.get("subscription_id"),
        status=AccountStatus.CONNECTED
    )
    
    doc = account.model_dump()
    doc["credentials"] = encrypt_credentials(input_data.credentials)
    await db.cloud_accounts.insert_one(doc)
    
    await log_audit_event("cloud_account.created", "cloud_account", account.id, {"provider": input_data.provider.value})
    
    return account

@api_router.get("/cloud-accounts", response_model=List[CloudAccount])
async def list_cloud_accounts(
    provider: Optional[CloudProvider] = None,
    status: Optional[AccountStatus] = None
):
    """List all cloud accounts"""
    query = {}
    if provider:
        query["provider"] = provider.value
    if status:
        query["status"] = status.value
    
    accounts = await db.cloud_accounts.find(query, {"_id": 0, "credentials": 0}).to_list(100)
    return accounts

@api_router.get("/cloud-accounts/{account_id}", response_model=CloudAccount)
async def get_cloud_account(account_id: str):
    """Get a specific cloud account"""
    account = await db.cloud_accounts.find_one({"id": account_id}, {"_id": 0, "credentials": 0})
    if not account:
        raise HTTPException(status_code=404, detail="Cloud account not found")
    return account

@api_router.patch("/cloud-accounts/{account_id}", response_model=CloudAccount)
async def update_cloud_account(account_id: str, update_data: CloudAccountUpdate):
    """Update a cloud account"""
    account = await db.cloud_accounts.find_one({"id": account_id})
    if not account:
        raise HTTPException(status_code=404, detail="Cloud account not found")
    
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    update_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.cloud_accounts.update_one({"id": account_id}, {"$set": update_dict})
    
    await log_audit_event("cloud_account.updated", "cloud_account", account_id, update_dict)
    
    updated = await db.cloud_accounts.find_one({"id": account_id}, {"_id": 0, "credentials": 0})
    return updated

@api_router.delete("/cloud-accounts/{account_id}")
async def delete_cloud_account(account_id: str):
    """Delete a cloud account and its instances"""
    account = await db.cloud_accounts.find_one({"id": account_id})
    if not account:
        raise HTTPException(status_code=404, detail="Cloud account not found")
    
    # Delete associated instances
    await db.instances.delete_many({"cloud_account_id": account_id})
    # Delete associated recommendations
    await db.recommendations.delete_many({"cloud_account_id": account_id})
    # Delete the account
    await db.cloud_accounts.delete_one({"id": account_id})
    
    await log_audit_event("cloud_account.deleted", "cloud_account", account_id)
    
    return {"success": True, "message": "Cloud account deleted"}

# ----- Sync -----

@api_router.post("/sync", response_model=SyncResult)
async def sync_all_accounts():
    """Sync inventory from all connected cloud accounts using real cloud provider APIs"""
    accounts = await db.cloud_accounts.find({"status": {"$ne": "disabled"}}).to_list(100)
    
    if not accounts:
        return SyncResult(
            success=True,
            accounts_synced=0,
            instances_found=0,
            errors=["No cloud accounts configured"],
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    
    total_instances = 0
    total_recommendations = 0
    errors = []
    
    await log_audit_event("sync.started", "system", payload={"account_count": len(accounts)})
    
    for account in accounts:
        try:
            # Update account status to syncing
            await db.cloud_accounts.update_one(
                {"id": account["id"]},
                {"$set": {"status": "syncing", "last_checked_at": datetime.now(timezone.utc).isoformat()}}
            )
            
            # Fetch instances using real cloud connectors
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
                {
                    "$set": {
                        "status": "connected",
                        "last_sync_at": datetime.now(timezone.utc).isoformat(),
                        "last_error": None,
                        "instance_count": len(instances)
                    }
                }
            )
            
            total_instances += len(instances)
            logger.info(f"Synced account {account['id']} ({account['provider']}): {len(instances)} instances")
            
        except Exception as e:
            logger.error(f"Error syncing account {account['id']}: {str(e)}")
            errors.append(f"Account {account.get('account_name', account['id'])}: {str(e)}")
            await db.cloud_accounts.update_one(
                {"id": account["id"]},
                {"$set": {"status": "error", "last_error": str(e)}}
            )
    
    await log_audit_event("sync.completed", "system", payload={
        "accounts_synced": len(accounts) - len(errors),
        "instances_found": total_instances,
        "recommendations_generated": total_recommendations,
        "errors": errors
    })
    
    # Notify WebSocket clients
    await ws_manager.broadcast({
        "type": "sync_complete",
        "data": {
            "accounts_synced": len(accounts) - len(errors),
            "instances_found": total_instances,
            "recommendations": total_recommendations
        }
    })
    
    return SyncResult(
        success=len(errors) == 0,
        accounts_synced=len(accounts),
        instances_found=total_instances,
        errors=errors,
        timestamp=datetime.now(timezone.utc).isoformat()
    )

@api_router.post("/sync/{account_id}", response_model=SyncResult)
async def sync_single_account(account_id: str):
    """Sync inventory from a single cloud account"""
    account = await db.cloud_accounts.find_one({"id": account_id})
    if not account:
        raise HTTPException(status_code=404, detail="Cloud account not found")
    
    try:
        await db.cloud_accounts.update_one(
            {"id": account_id},
            {"$set": {"status": "syncing", "last_checked_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        import random
        instance_count = random.randint(3, 10)
        instances = generate_mock_instances(account_id, CloudProvider(account["provider"]), instance_count)
        
        await db.instances.delete_many({"cloud_account_id": account_id})
        if instances:
            await db.instances.insert_many(instances)
        
        recommendations = generate_recommendations(instances)
        await db.recommendations.delete_many({"cloud_account_id": account_id})
        if recommendations:
            await db.recommendations.insert_many(recommendations)
        
        await db.cloud_accounts.update_one(
            {"id": account_id},
            {
                "$set": {
                    "status": "connected",
                    "last_sync_at": datetime.now(timezone.utc).isoformat(),
                    "last_error": None,
                    "instance_count": len(instances)
                }
            }
        )
        
        return SyncResult(
            success=True,
            accounts_synced=1,
            instances_found=len(instances),
            errors=[],
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
    except Exception as e:
        await db.cloud_accounts.update_one(
            {"id": account_id},
            {"$set": {"status": "error", "last_error": str(e)}}
        )
        raise HTTPException(status_code=500, detail=str(e))

# ----- Instances -----

@api_router.get("/instances", response_model=List[Instance])
async def list_instances(
    provider: Optional[CloudProvider] = None,
    cloud_account_id: Optional[str] = None,
    region: Optional[str] = None,
    state: Optional[str] = None,
    name: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0
):
    """Query normalized instance inventory"""
    query = {}
    if provider:
        query["provider"] = provider.value
    if cloud_account_id:
        query["cloud_account_id"] = cloud_account_id
    if region:
        query["region_or_zone"] = {"$regex": region, "$options": "i"}
    if state:
        query["state"] = state
    if name:
        query["name"] = {"$regex": name, "$options": "i"}
    
    instances = await db.instances.find(query, {"_id": 0}).skip(offset).limit(limit).to_list(limit)
    return instances

@api_router.get("/instances/{instance_id}")
async def get_instance(instance_id: str):
    """Get a specific instance by ID"""
    instance = await db.instances.find_one({"instance_id": instance_id}, {"_id": 0})
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")
    return instance

# ----- Recommendations -----

@api_router.get("/recommendations", response_model=List[Recommendation])
async def list_recommendations(
    category: Optional[RecommendationCategory] = None,
    severity: Optional[RecommendationSeverity] = None,
    status: Optional[RecommendationStatus] = None,
    cloud_account_id: Optional[str] = None,
    limit: int = Query(default=100, le=500)
):
    """Get FinOps and SecOps recommendations"""
    query = {}
    if category:
        query["category"] = category.value
    if severity:
        query["severity"] = severity.value
    if status:
        query["status"] = status.value
    if cloud_account_id:
        query["cloud_account_id"] = cloud_account_id
    
    recommendations = await db.recommendations.find(query, {"_id": 0}).limit(limit).to_list(limit)
    return recommendations

@api_router.patch("/recommendations/{recommendation_id}")
async def update_recommendation(recommendation_id: str, status: RecommendationStatus):
    """Update recommendation status (dismiss/resolve)"""
    result = await db.recommendations.update_one(
        {"id": recommendation_id},
        {"$set": {"status": status.value, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    await log_audit_event("recommendation.updated", "recommendation", recommendation_id, {"new_status": status.value})
    
    return {"success": True}

@api_router.post("/recommendations/run")
async def run_recommendations():
    """Manually trigger recommendation generation"""
    instances = await db.instances.find({}, {"_id": 0}).to_list(1000)
    
    if not instances:
        return {"success": True, "recommendations_generated": 0, "message": "No instances to analyze"}
    
    # Clear all existing recommendations
    await db.recommendations.delete_many({})
    
    recommendations = generate_recommendations(instances)
    
    if recommendations:
        await db.recommendations.insert_many(recommendations)
    
    await log_audit_event("recommendations.generated", "system", payload={"count": len(recommendations)})
    
    return {"success": True, "recommendations_generated": len(recommendations)}

# ----- Remediation -----

@api_router.post("/remediation/analyze")
async def analyze_remediations(dry_run: bool = True):
    """Analyze and generate remediation actions"""
    engine = RemediationEngine(db)
    actions = await engine.analyze_and_remediate(dry_run=dry_run)
    return {"success": True, "actions": actions, "count": len(actions)}


@api_router.get("/remediation/actions")
async def list_remediation_actions(status: Optional[str] = None):
    """List all remediation actions"""
    query = {"status": status} if status else {}
    actions = await db.remediation_actions.find(query, {"_id": 0}).to_list(1000)
    return actions


@api_router.post("/remediation/actions/{action_id}/approve")
async def approve_remediation(action_id: str):
    """Approve and execute a remediation action"""
    engine = RemediationEngine(db)
    result = await engine.execute_action(action_id, approved_by="api_user")
    return result

# ----- WAFR -----

@api_router.post("/wafr/assess/{account_id}")
async def run_wafr_assessment(account_id: str):
    """Run AWS Well-Architected Review for an account"""
    account = await db.cloud_accounts.find_one({"id": account_id})
    if not account:
        raise HTTPException(status_code=404, detail="Cloud account not found")
    if account["provider"] != "aws":
        raise HTTPException(status_code=400, detail="WAFR only supports AWS accounts")

    credentials = decrypt_credentials(account["credentials"])
    engine = WAFREngine(
        credentials["access_key_id"],
        credentials["secret_access_key"],
        credentials.get("region", "us-east-1"),
    )

    results = await engine.run_wafr_assessment()

    await db.wafr_assessments.insert_one(
        {
            "account_id": account_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "results": results,
        }
    )

    return results

# ----- Dashboard Stats -----

@api_router.get("/dashboard/correlated-alerts")
async def get_correlated_alerts():
    """Find instances with both cost anomalies and security issues"""
    alerts = await fetch_correlated_alerts()
    return alerts

@api_router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats():
    """Get aggregated dashboard statistics"""
    # Count accounts by provider
    accounts = await db.cloud_accounts.find({}, {"_id": 0}).to_list(100)
    accounts_by_provider = {}
    for acc in accounts:
        provider = acc.get("provider", "unknown")
        accounts_by_provider[provider] = accounts_by_provider.get(provider, 0) + 1
    
    # Count instances by provider and state
    instances = await db.instances.find({}, {"_id": 0}).to_list(1000)
    instances_by_provider = {}
    instances_by_state = {}
    for inst in instances:
        provider = inst.get("provider", "unknown")
        state = inst.get("state", "unknown")
        instances_by_provider[provider] = instances_by_provider.get(provider, 0) + 1
        instances_by_state[state] = instances_by_state.get(state, 0) + 1
    
    # Count recommendations
    open_recs = await db.recommendations.count_documents({"status": "open"})
    finops_recs = await db.recommendations.count_documents({"category": "finops", "status": "open"})
    secops_recs = await db.recommendations.count_documents({"category": "secops", "status": "open"})
    
    # Get last sync time
    last_sync_account = await db.cloud_accounts.find_one(
        {"last_sync_at": {"$ne": None}},
        sort=[("last_sync_at", -1)]
    )
    last_sync = last_sync_account.get("last_sync_at") if last_sync_account else None

    correlated_alerts = await fetch_correlated_alerts(limit=100)
    
    return DashboardStats(
        total_instances=len(instances),
        total_accounts=len(accounts),
        accounts_by_provider=accounts_by_provider,
        instances_by_provider=instances_by_provider,
        instances_by_state=instances_by_state,
        open_recommendations=open_recs,
        finops_recommendations=finops_recs,
        secops_recommendations=secops_recs,
        correlated_alerts=correlated_alerts,
        last_sync=last_sync
    )

# ----- Audit Events -----

@api_router.get("/audit-events")
async def list_audit_events(limit: int = Query(default=50, le=200)):
    """Get recent audit events"""
    events = await db.audit_events.find({}, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return events

# ----- Scheduler -----

@api_router.get("/scheduler/jobs")
async def list_scheduled_jobs(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """List all scheduled jobs (Admin only)"""
    current_user = await get_current_user(credentials)
    if current_user["role"] not in ["admin", "msp_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return get_scheduled_jobs()

@api_router.post("/scheduler/trigger/{job_id}")
async def trigger_scheduled_job(
    job_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Manually trigger a scheduled job (Admin only)"""
    current_user = await get_current_user(credentials)
    if current_user["role"] not in ["admin", "msp_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        result = trigger_job_now(job_id)
        await log_audit_event("scheduler.job_triggered", "scheduler", job_id, {"triggered_by": current_user["id"]})
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ----- Email Test -----

@api_router.post("/email/test")
async def send_test_email(
    email: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Send a test email (Admin only)"""
    current_user = await get_current_user(credentials)
    if current_user["role"] not in ["admin", "msp_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Fetch user details
    user = await db.users.find_one({"id": current_user["id"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Send test sync notification
    result = await email_service.send_sync_complete_notification(
        to=email,
        name=user["name"],
        accounts_synced=2,
        instances_found=15,
        new_recommendations=5
    )
    
    await log_audit_event("email.test_sent", "email", None, {"to": email, "result": result})
    
    return result

# ----- Notification Test -----

@api_router.post("/notifications/test")
async def send_test_notification(
    data: NotificationTestRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Send a test Slack/Teams notification (Admin only)"""
    current_user = await get_current_user(credentials)
    if current_user["role"] not in ["admin", "msp_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")

    message = data.message or "CloudWatcher test notification"
    results = {}

    if data.channel in ["all", "slack"]:
        results["slack"] = await notification_service.send_slack_message(message)
    if data.channel in ["all", "teams"]:
        results["teams"] = await notification_service.send_teams_message(message)

    await log_audit_event("notification.test_sent", "notification", None, {"channel": data.channel, "results": results})

    return {"success": True, "results": results}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize scheduler on startup"""
    global auth_service
    auth_service = AuthService(db)
    
    # Setup and start scheduler
    sync_interval = int(os.environ.get("SYNC_INTERVAL_MINUTES", "60"))
    setup_scheduler(db, email_service, notification_service, sync_interval)
    start_scheduler()
    logger.info(f"CloudWatcher started with {sync_interval} minute sync interval")

@app.on_event("shutdown")
async def shutdown_db_client():
    """Cleanup on shutdown"""
    stop_scheduler()
    client.close()
    logger.info("CloudWatcher shutdown complete")
