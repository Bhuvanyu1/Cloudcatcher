# CloudWatcher Phase 2 PRD Feature Build Summary

This summary presents the features to be built for CloudWatcher Phase 2 (production readiness), organized by sprint and aligned to the PRD goals and success criteria.

## Current Baseline (Phase 1 Already Built)
- Multi-cloud connectors: AWS, Azure, GCP, DigitalOcean
- Encrypted credential storage
- AI remediation engine (basic rules)
- WAFR automation framework (AWS-only)
- Correlated FinOps + SecOps dashboard
- Neo-brutalist UI with 4 core pages

## Sprint 1–2 (Weeks 1–4): Foundation & Security
**Goal:** Make the product sellable to the first 10 customers.

### 1. Authentication & Authorization (P0)
- JWT-based authentication with short-lived access tokens and refresh tokens
- Secure password hashing with bcrypt (12 rounds)
- Token blacklisting for logout
- OAuth/OIDC integrations: Google, Microsoft Azure AD, GitHub
- User management: profiles, email verification, password reset, deactivation
- New auth endpoints for registration, login, logout, refresh, verification, reset, OAuth

### 2. Role-Based Access Control (RBAC) (P0)
- Roles: User, Admin, MSP Admin
- Permission-based enforcement on all sensitive endpoints
- Organization-level and MSP tenant-aware row-level security
- Admin user management and audit log visibility

### 3. Real-Time Monitoring & Scheduled Syncs (P0)
- Scheduled background syncs with configurable cadence per account
- Retry failed syncs with exponential backoff and provider rate limiting
- Real-time event ingestion (AWS CloudWatch, Azure Event Grid, GCP Pub/Sub)
- WebSocket updates to the frontend
- Alert delivery via email, Slack, Microsoft Teams, and PagerDuty

### 4. Audit Logging & Compliance (P1)
- Immutable, append-only audit logs for sensitive operations
- Compliance-ready exports (SOC 2 / ISO 27001 readiness)
- Retention policy defaults to 90 days, configurable

## Sprint 3–4 (Weeks 5–8): Scale & Intelligence
**Goal:** Support 50–100 customers with smarter automation.

### 1. ML-Powered Anomaly Detection (P0)
- Cost anomaly detection (time-series forecasting, 3x+ spike detection)
- Security anomaly detection (IAM, config drift, privilege escalation, lateral movement)
- Explainability with confidence scores and baseline comparisons
- Daily model runs and alert notifications

### 2. Enhanced AI Remediation (P0)
- Expanded FinOps automation (savings plans, reserved instances, storage optimization)
- Expanded SecOps automation (MFA enforcement, access key rotation, S3 hardening)
- Approval workflow for high-risk remediations
- ROI tracking on executed remediations

### 3. Cost Allocation & Chargeback (P1)
- Tag-based cost allocation (team, project, environment)
- Chargeback reporting by team and month
- Budget alerts and cost trend analysis
- CSV exports for finance workflows

## Sprint 5–6 (Weeks 9–12): Market Differentiation
**Goal:** Launch MSP features and vertical bundles.

### 1. Multi-Tenancy for MSPs (P0)
- Strong tenant isolation with per-tenant encryption
- White-labeling: custom logos, domains, email templates, and branding
- MSP billing with reseller markup and unified invoicing
- Client portal with read-only access

### 2. Industry Vertical Bundles (P1)
- CloudComply (BFSI): RBI, PCI-DSS, SOC 2 automation
- TrustCloud (Healthcare): HIPAA compliance and PHI data controls
- PeakScale (Retail): PCI-DSS, traffic spike optimization, CDN cost tuning
- One-click deployment with compliance gap remediation

## Production Readiness Checklist
- **Infrastructure:** production MongoDB, Redis, load balancer, HTTPS, CDN, backups
- **Security:** pen testing, OWASP audits, dependency scanning, secrets management
- **Performance:** optimized indexes, pagination, caching, sub-200ms APIs
- **Documentation:** API docs, user/admin guides, SOC 2 documentation
- **Legal:** terms, privacy, DPA, SLA commitments

## Phase 2 Success Metrics
- 99.9% uptime
- <200ms API response time
- <10% false positives in anomaly detection
- 50+ remediation rules
- 3 vertical bundles live
- 100 paying customers / $30K MRR
- NPS > 50 and <5% monthly churn
