"""
Authentication & Authorization Module for CloudWatcher
- JWT-based authentication
- Password hashing with bcrypt
- Role-based access control (RBAC)
- Token refresh and blacklisting
"""
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from enum import Enum
from functools import wraps
import os
import uuid

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Configuration
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "cloudwatcher-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Security bearer
security = HTTPBearer(auto_error=False)

# ==================== ENUMS ====================

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    MSP_ADMIN = "msp_admin"

class Permission(str, Enum):
    VIEW_CLOUD_ACCOUNTS = "view:cloud_accounts"
    MANAGE_CLOUD_ACCOUNTS = "manage:cloud_accounts"
    VIEW_INSTANCES = "view:instances"
    VIEW_RECOMMENDATIONS = "view:recommendations"
    APPROVE_REMEDIATIONS = "approve:remediations"
    MANAGE_USERS = "manage:users"
    VIEW_AUDIT_LOGS = "view:audit_logs"
    MANAGE_BILLING = "manage:billing"
    MANAGE_TENANTS = "manage:tenants"
    VIEW_AGGREGATED_BILLING = "view:aggregated_billing"

# Role to permissions mapping
ROLE_PERMISSIONS = {
    UserRole.USER: [
        Permission.VIEW_CLOUD_ACCOUNTS,
        Permission.VIEW_INSTANCES,
        Permission.VIEW_RECOMMENDATIONS,
        Permission.APPROVE_REMEDIATIONS
    ],
    UserRole.ADMIN: [
        Permission.VIEW_CLOUD_ACCOUNTS,
        Permission.MANAGE_CLOUD_ACCOUNTS,
        Permission.VIEW_INSTANCES,
        Permission.VIEW_RECOMMENDATIONS,
        Permission.APPROVE_REMEDIATIONS,
        Permission.MANAGE_USERS,
        Permission.VIEW_AUDIT_LOGS,
        Permission.MANAGE_BILLING
    ],
    UserRole.MSP_ADMIN: [
        Permission.VIEW_CLOUD_ACCOUNTS,
        Permission.MANAGE_CLOUD_ACCOUNTS,
        Permission.VIEW_INSTANCES,
        Permission.VIEW_RECOMMENDATIONS,
        Permission.APPROVE_REMEDIATIONS,
        Permission.MANAGE_USERS,
        Permission.VIEW_AUDIT_LOGS,
        Permission.MANAGE_BILLING,
        Permission.MANAGE_TENANTS,
        Permission.VIEW_AGGREGATED_BILLING
    ]
}

# ==================== HELPER FUNCTIONS ====================

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(user_id: str, role: str, organization_id: str = None) -> str:
    """Create a JWT access token"""
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": user_id,
        "role": role,
        "org": organization_id,
        "exp": expire,
        "type": "access"
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(user_id: str) -> str:
    """Create a JWT refresh token"""
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {
        "sub": user_id,
        "exp": expire,
        "type": "refresh"
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    """Decode and validate a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def create_verification_token(email: str) -> str:
    """Create email verification token"""
    expire = datetime.now(timezone.utc) + timedelta(hours=24)
    to_encode = {
        "email": email,
        "exp": expire,
        "type": "verification"
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_password_reset_token(email: str) -> str:
    """Create password reset token"""
    expire = datetime.now(timezone.utc) + timedelta(hours=1)
    to_encode = {
        "email": email,
        "exp": expire,
        "type": "password_reset"
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# ==================== AUTH SERVICE ====================

class AuthService:
    def __init__(self, db):
        self.db = db
    
    async def register_user(self, email: str, password: str, name: str, organization_name: str = None) -> dict:
        """Register a new user"""
        # Check if user exists
        existing = await self.db.users.find_one({"email": email})
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create organization if first user
        org_id = None
        if organization_name:
            org_id = f"org_{uuid.uuid4().hex[:12]}"
            await self.db.organizations.insert_one({
                "id": org_id,
                "name": organization_name,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "settings": {}
            })
        
        # Create user
        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        user = {
            "id": user_id,
            "email": email,
            "password": hash_password(password),
            "name": name,
            "role": UserRole.ADMIN.value if organization_name else UserRole.USER.value,
            "organization_id": org_id,
            "email_verified": False,  # Set to True for demo
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_login_at": None,
            "settings": {
                "timezone": "UTC",
                "email_notifications": True,
                "slack_notifications": False
            }
        }
        
        await self.db.users.insert_one(user)
        
        # In production, send verification email here
        # verification_token = create_verification_token(email)
        # await send_verification_email(email, verification_token)
        
        return {
            "id": user_id,
            "email": email,
            "name": name,
            "role": user["role"],
            "organization_id": org_id
        }
    
    async def login(self, email: str, password: str) -> dict:
        """Authenticate user and return tokens"""
        user = await self.db.users.find_one({"email": email})
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        if not verify_password(password, user["password"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # For demo, skip email verification check
        # if not user.get("email_verified"):
        #     raise HTTPException(status_code=403, detail="Email not verified")
        
        # Update last login
        await self.db.users.update_one(
            {"id": user["id"]},
            {"$set": {"last_login_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        # Create tokens
        access_token = create_access_token(
            user["id"], 
            user["role"], 
            user.get("organization_id")
        )
        refresh_token = create_refresh_token(user["id"])
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": user["id"],
                "email": user["email"],
                "name": user["name"],
                "role": user["role"],
                "organization_id": user.get("organization_id")
            }
        }
    
    async def refresh_tokens(self, refresh_token: str) -> dict:
        """Refresh access token using refresh token"""
        try:
            payload = decode_token(refresh_token)
            
            if payload.get("type") != "refresh":
                raise HTTPException(status_code=401, detail="Invalid token type")
            
            # Check if token is blacklisted
            blacklisted = await self.db.tokens_blacklist.find_one({"token": refresh_token})
            if blacklisted:
                raise HTTPException(status_code=401, detail="Token has been revoked")
            
            user_id = payload.get("sub")
            user = await self.db.users.find_one({"id": user_id})
            
            if not user:
                raise HTTPException(status_code=401, detail="User not found")
            
            # Create new tokens
            new_access_token = create_access_token(
                user["id"],
                user["role"],
                user.get("organization_id")
            )
            new_refresh_token = create_refresh_token(user["id"])
            
            # Blacklist old refresh token
            await self.db.tokens_blacklist.insert_one({
                "token": refresh_token,
                "blacklisted_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": datetime.fromtimestamp(payload["exp"], tz=timezone.utc).isoformat()
            })
            
            return {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer"
            }
            
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    async def logout(self, access_token: str, refresh_token: str = None):
        """Logout user by blacklisting tokens"""
        try:
            payload = decode_token(access_token)
            await self.db.tokens_blacklist.insert_one({
                "token": access_token,
                "blacklisted_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": datetime.fromtimestamp(payload["exp"], tz=timezone.utc).isoformat()
            })
            
            if refresh_token:
                refresh_payload = decode_token(refresh_token)
                await self.db.tokens_blacklist.insert_one({
                    "token": refresh_token,
                    "blacklisted_at": datetime.now(timezone.utc).isoformat(),
                    "expires_at": datetime.fromtimestamp(refresh_payload["exp"], tz=timezone.utc).isoformat()
                })
            
            return {"success": True}
        except:
            return {"success": True}  # Even if token is invalid, logout succeeds
    
    async def verify_email(self, token: str):
        """Verify user email"""
        try:
            payload = decode_token(token)
            
            if payload.get("type") != "verification":
                raise HTTPException(status_code=400, detail="Invalid token type")
            
            email = payload.get("email")
            result = await self.db.users.update_one(
                {"email": email},
                {"$set": {"email_verified": True}}
            )
            
            if result.modified_count == 0:
                raise HTTPException(status_code=404, detail="User not found")
            
            return {"success": True, "message": "Email verified"}
            
        except JWTError:
            raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    async def request_password_reset(self, email: str):
        """Request password reset"""
        user = await self.db.users.find_one({"email": email})
        
        # Don't reveal if user exists
        if not user:
            return {"success": True, "message": "If email exists, reset link sent"}
        
        reset_token = create_password_reset_token(email)
        
        # In production, send email here
        # await send_password_reset_email(email, reset_token)
        
        # For demo, return token
        return {
            "success": True,
            "message": "If email exists, reset link sent",
            "reset_token": reset_token  # Remove in production
        }
    
    async def reset_password(self, token: str, new_password: str):
        """Reset password using token"""
        try:
            payload = decode_token(token)
            
            if payload.get("type") != "password_reset":
                raise HTTPException(status_code=400, detail="Invalid token type")
            
            email = payload.get("email")
            hashed = hash_password(new_password)
            
            result = await self.db.users.update_one(
                {"email": email},
                {"$set": {"password": hashed}}
            )
            
            if result.modified_count == 0:
                raise HTTPException(status_code=404, detail="User not found")
            
            return {"success": True, "message": "Password reset successfully"}
            
        except JWTError:
            raise HTTPException(status_code=400, detail="Invalid or expired token")

# ==================== DEPENDENCY INJECTION ====================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db=None  # Will be injected from main app
) -> dict:
    """Get current user from JWT token"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = credentials.credentials
    
    try:
        payload = decode_token(token)
        
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        
        user_id = payload.get("sub")
        
        # For now, return payload directly
        # In production, fetch user from DB
        return {
            "id": user_id,
            "role": payload.get("role"),
            "organization_id": payload.get("org")
        }
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[dict]:
    """Get current user if authenticated, None otherwise"""
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except:
        return None

def require_permission(permission: Permission):
    """Decorator to require specific permission"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get("current_user")
            if not current_user:
                raise HTTPException(status_code=401, detail="Not authenticated")
            
            user_role = UserRole(current_user.get("role", "user"))
            user_permissions = ROLE_PERMISSIONS.get(user_role, [])
            
            if permission not in user_permissions:
                raise HTTPException(
                    status_code=403, 
                    detail=f"Missing permission: {permission.value}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_role(role: UserRole):
    """Decorator to require specific role"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get("current_user")
            if not current_user:
                raise HTTPException(status_code=401, detail="Not authenticated")
            
            user_role = current_user.get("role")
            
            if user_role != role.value:
                raise HTTPException(
                    status_code=403,
                    detail=f"Required role: {role.value}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# ==================== ROW-LEVEL SECURITY ====================

async def filter_by_organization(query: dict, current_user: dict, db) -> dict:
    """Add organization filter to queries for row-level security"""
    if not current_user:
        return query
    
    role = current_user.get("role")
    org_id = current_user.get("organization_id")
    
    if role == UserRole.MSP_ADMIN.value:
        # MSP admins can see all tenants they manage
        tenants = await db.tenants.find(
            {"msp_organization_id": org_id}
        ).distinct("id")
        if tenants:
            query["organization_id"] = {"$in": tenants}
    elif org_id:
        # Regular users see only their organization
        query["organization_id"] = org_id
    
    return query
