# Cloud Watcher

A multi-cloud instance inventory platform that unifies AWS EC2, Azure VMs, GCP Compute Engine, and DigitalOcean Droplets into a single dashboard with FinOps and SecOps recommendations.

![Dashboard](https://img.shields.io/badge/Dashboard-Neo--Brutalist-black?style=flat-square)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square)
![React](https://img.shields.io/badge/Frontend-React-61DAFB?style=flat-square)
![MongoDB](https://img.shields.io/badge/Database-MongoDB-47A248?style=flat-square)

## Features

### Core Functionality
- **Multi-Cloud Support**: Connect and manage AWS, Azure, GCP, and DigitalOcean accounts
- **Unified Inventory**: View all cloud instances in a single, normalized table
- **Real-time Sync**: Pull latest instance data from all connected providers
- **Advanced Filtering**: Filter by provider, region, state, name, and tags

### FinOps Recommendations
- Identify stopped instances incurring storage costs
- Detect oversized instances in non-production environments
- Track idle resources for cost optimization

### SecOps Recommendations
- Flag instances with public IP exposure
- Identify security misconfigurations
- Monitor production environment risks

### Remediation & WAFR
- Generate remediation actions for idle resources and approve execution flows
- Run AWS Well-Architected Framework Review (WAFR) assessments for AWS accounts
- Correlate cost + security alerts for at-risk resources

### Anomaly Detection & Alerts
- Detect unusual inventory changes
- Webhook ingestion for external alerts
- Threshold-based anomaly detection

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI (Python 3.11+) |
| Frontend | React 18 + Tailwind CSS |
| Database | MongoDB |
| UI Components | shadcn/ui |
| Design | Neo-Brutalist Dark Theme |

## Project Structure

```
/app
├── backend/
│   ├── server.py          # FastAPI application
│   ├── requirements.txt   # Python dependencies
│   └── .env              # Environment variables
├── frontend/
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── pages/        # Page components
│   │   ├── lib/          # Utilities & API client
│   │   └── App.js        # Main app component
│   ├── package.json      # Node dependencies
│   └── .env              # Frontend environment
└── README.md
```

## API Endpoints

### Health
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |

### Cloud Accounts
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/cloud-accounts` | Create cloud account |
| GET | `/api/cloud-accounts` | List all accounts |
| GET | `/api/cloud-accounts/{id}` | Get account details |
| PATCH | `/api/cloud-accounts/{id}` | Update account |
| DELETE | `/api/cloud-accounts/{id}` | Delete account |

### Sync
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/sync` | Sync all accounts |
| POST | `/api/sync/{id}` | Sync single account |

### Instances
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/instances` | Query instances (with filters) |
| GET | `/api/instances/{id}` | Get instance details |

### Recommendations
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/recommendations` | List recommendations |
| PATCH | `/api/recommendations/{id}` | Update status (dismiss/resolve) |
| POST | `/api/recommendations/run` | Generate recommendations |

### Alerts
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/alerts` | List alerts |
| POST | `/api/alerts/webhook` | Ingest external alert |
| POST | `/api/alerts/detect` | Run anomaly detection |

### Remediation
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/remediation/analyze` | Analyze and generate remediation actions |
| GET | `/api/remediation/actions` | List remediation actions |
| POST | `/api/remediation/actions/{action_id}/approve` | Approve and execute action |

### WAFR (AWS)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/wafr/assess/{account_id}` | Run WAFR assessment for an AWS account |

### Dashboard
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard/stats` | Get dashboard statistics |
| GET | `/api/dashboard/correlated-alerts` | List correlated cost + security alerts |

## Installation

### Deploying on an Existing Azure Free-Tier VM

If you already have a free Azure VM and do not want to create a new one, use this path.

1. Open **Azure Portal** → **Virtual Machines** → select your existing VM.
2. Ensure the VM is in **Running** state (click **Start** if needed).
3. Open **Networking** for that VM and verify inbound rules allow:
   - **22** (SSH)
   - **80** (HTTP)
   - **443** (HTTPS, optional but recommended)
4. Copy the VM **Public IP address** from the **Overview** tab.
5. Connect from your local terminal:

```bash
ssh <vm-username>@<vm-public-ip>
```

Example:

```bash
ssh azureuser@20.115.10.42
```

6. Confirm you are connected:

```bash
hostname && whoami
```

7. Continue with backend/frontend setup from the sections below, but run commands directly on this VM.

### Prerequisites
- Python 3.11+
- Node.js 18+
- MongoDB

### Backend Setup

```bash
cd backend
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your MongoDB URL

# Run server
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

### Frontend Setup

```bash
cd frontend
yarn install

# Configure environment
cp .env.example .env
# Edit .env with your backend URL

# Run development server
yarn start
```

## Environment Variables

### Backend (`/backend/.env`)
```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=cloudwatcher
CORS_ORIGINS=*
ENCRYPTION_KEY=base64-encoded-32-byte-key
```

### Frontend (`/frontend/.env`)
```env
REACT_APP_BACKEND_URL=http://localhost:8001
```

## Usage

### Adding a Cloud Account

```bash
curl -X POST http://localhost:8001/api/cloud-accounts \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "aws",
    "account_name": "Production AWS",
    "credentials": {
      "access_key_id": "YOUR_KEY",
      "secret_access_key": "YOUR_SECRET",
      "region": "us-east-1"
    }
  }'
```

### Syncing Inventory

```bash
curl -X POST http://localhost:8001/api/sync
```

### Querying Instances

```bash
# All instances
curl http://localhost:8001/api/instances

# Filter by provider
curl http://localhost:8001/api/instances?provider=aws

# Filter by state
curl http://localhost:8001/api/instances?state=running
```

### Webhook Alert Ingestion

```bash
curl -X POST http://localhost:8001/api/alerts/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "source": "cloudwatch",
    "alert_type": "high_cpu",
    "severity": "high",
    "resource_id": "i-1234567890",
    "payload": {"cpu_percent": 95}
  }'
```

### WAFR Assessment (AWS)

```bash
curl -X POST http://localhost:8001/api/wafr/assess/{account_id}
```

## Supported Cloud Providers

| Provider | Credentials Required |
|----------|---------------------|
| AWS | Access Key ID, Secret Access Key, Region |
| Azure | Tenant ID, Client ID, Client Secret, Subscription ID |
| GCP | Project ID, Service Account JSON |
| DigitalOcean | Personal Access Token |

> **Note**: Current implementation uses mock data for demo purposes. Real cloud provider SDKs can be integrated when credentials are provided.

## Data Models

### Instance (Normalized)
```json
{
  "provider": "aws|azure|gcp|do",
  "cloud_account_id": "uuid",
  "region_or_zone": "us-east-1",
  "instance_id": "i-1234567890",
  "name": "web-server-01",
  "instance_type_or_size": "t3.medium",
  "state": "running|stopped|pending|terminated",
  "public_ip": "1.2.3.4",
  "private_ip": "10.0.0.5",
  "tags": {"environment": "production"}
}
```

### Recommendation
```json
{
  "category": "finops|secops",
  "severity": "low|medium|high",
  "rule_id": "FINOPS-001",
  "title": "Stopped Instance Incurring Storage Costs",
  "description": "...",
  "status": "open|dismissed|resolved"
}
```

## Screenshots

The application features a neo-brutalist design with:
- Dark theme with high contrast
- Sharp edges and thick borders
- Neon lime (#CCFF00) and cyan (#00FFFF) accents
- Monospace typography (JetBrains Mono)

## Roadmap

- [ ] Real cloud provider API integration
- [ ] Scheduled auto-sync (cron jobs)
- [ ] Secure credential encryption (KMS/Vault)
- [ ] User authentication (JWT/OAuth)
- [ ] Cost analytics dashboard
- [ ] Email/Slack notifications
- [ ] Custom recommendation rules
- [ ] Multi-tenant support

## License

MIT

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
