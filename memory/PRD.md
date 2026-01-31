# Cloud Watcher MVP - PRD

## Original Problem Statement
Cloud Watcher is a hackathon MVP that unifies multi-cloud instance inventory across AWS EC2, Azure Virtual Machines, GCP Compute Engine, and DigitalOcean Droplets. Provides FinOps recommendations, SecOps recommendations, and anomaly detection/alerts.

## User Choices
- Database: MongoDB (with SQLite compatibility structure)
- Cloud Connectors: Actual API connectors with mock data for demo
- Authentication: Skip (single-user hackathon mode)
- Design: Neo-brutalist dark theme with sharp edges and colorful buttons

## Architecture
- **Backend**: FastAPI + MongoDB
- **Frontend**: React + Tailwind CSS + shadcn/ui
- **Design**: Neo-brutalist (dark, sharp edges, neon lime/cyan accents)

## Core Requirements
1. Connect multiple cloud accounts (AWS, Azure, GCP, DigitalOcean)
2. Sync instance inventory from all connected accounts
3. Normalize and store all instances into a unified schema
4. Query/filter instances by provider, region, state, tags, name
5. FinOps recommendations (rule-based)
6. SecOps recommendations (rule-based)

## What's Been Implemented (Jan 2026)
- [x] Cloud Accounts CRUD (create, read, update, delete)
- [x] Mock data connectors for all 4 providers
- [x] Instance inventory sync (per-account and all)
- [x] Instance query with filters (provider, region, state, name)
- [x] FinOps recommendations engine
- [x] SecOps recommendations engine
- [x] Dashboard with stats overview
- [x] Recommendation dismiss/resolve workflow
- [x] Audit events logging
- [x] Neo-brutalist UI with dark theme

## API Endpoints
- `GET /api/health` - Health check
- `POST /api/cloud-accounts` - Create cloud account
- `GET /api/cloud-accounts` - List cloud accounts
- `PATCH /api/cloud-accounts/{id}` - Update account
- `DELETE /api/cloud-accounts/{id}` - Delete account
- `POST /api/sync` - Sync all accounts
- `POST /api/sync/{id}` - Sync single account
- `GET /api/instances` - Query instances
- `GET /api/recommendations` - Get recommendations
- `PATCH /api/recommendations/{id}` - Update status
- `GET /api/dashboard/stats` - Dashboard statistics

## Prioritized Backlog

### P0 (Critical)
- [ ] Real cloud provider API connectors (AWS EC2, Azure, GCP, DO)
- [ ] Secure credentials storage (encrypted)

### P1 (High)
- [ ] User authentication (JWT or OAuth)
- [ ] Real-time sync scheduling (cron)
- [ ] Cost data integration

### P2 (Medium)
- [ ] Anomaly detection engine
- [ ] Alert webhook ingestion
- [ ] Email notifications
- [ ] RBAC (roles & permissions)

### P3 (Low)
- [ ] Multi-tenant support
- [ ] Billing/cost analytics
- [ ] Custom recommendation rules
- [ ] Export functionality

## Tech Stack
- FastAPI 0.115.0
- React 18
- MongoDB (Motor driver)
- Tailwind CSS
- shadcn/ui components
