# B2B Logistics Portal

A multi-tenant backend system for a logistics SaaS platform built with Django, Django REST Framework, Celery, PostgreSQL, and Redis.

## Features

- **Multi-tenancy**: Company-based data isolation
- **Role-based Access Control**: Admin, Operator, and Viewer roles
- **Order Management**: Create, process, and track orders
- **Background Processing**: Celery-based async order processing
- **Export Functionality**: Generate CSV exports of orders
- **RESTful API**: JWT-authenticated API endpoints
- **Health Monitoring**: `/health/` endpoint for system status
- **Dockerized**: Complete Docker setup with Nginx reverse proxy
- **CSV Product Upload**: Bulk upload products via admin (Bonus ✨)
- **Company Feature Toggles**: Per-company feature control (Bonus ✨)
- **API Rate Limiting**: Token bucket algorithm with Redis (Bonus ✨)

## Tech Stack

- Python 3.9+
- Django 4.x
- Django REST Framework
- PostgreSQL 15
- Redis 7
- Celery 5.x
- Docker & docker-compose
- Nginx

## Project Structure

```
PayMobTask/
├── core/                   # Core app (models, admin, tasks)
│   ├── models.py          # Company, Profile, Product, Order, Export
│   ├── admin.py           # Django admin with custom actions
│   ├── tasks.py           # Celery tasks
│   └── management/
│       └── commands/
│           └── create_sample_data.py
├── api/                    # API app (DRF)
│   ├── serializers.py     # DRF serializers
│   ├── views.py           # ViewSets
│   ├── permissions.py     # Custom permissions
│   └── urls.py            # API routes
├── logistics_portal/       # Project settings
│   ├── settings.py
│   ├── urls.py
│   └── celery.py          # Celery configuration
├── docker-compose.yml
├── Dockerfile
├── nginx.conf
├── requirements.txt
└── README.md
```

## Setup Instructions

### Prerequisites

- Docker and docker-compose installed
- OR Python 3.9+, PostgreSQL, and Redis installed locally

### Option 1: Docker Setup (Recommended)

1. **Clone the repository**
   ```bash
   cd /home/abdelrhman/PayMobTask
   ```

2. **Build and start services**
   ```bash
   docker compose up --build
   ```

3. **Run migrations** (in a new terminal)
   ```bash
   docker compose exec web python manage.py migrate
   ```

4. **Create sample data**
   ```bash
   docker compose exec web python manage.py create_sample_data
   ```

5. **Create a superuser** (optional)
   ```bash
   docker compose exec web python manage.py createsuperuser
   ```

6. **Access the application**
   - Django Admin: http://localhost/admin/
   - API: http://localhost/api/
   - Health Check: http://localhost/health/

### Option 2: Local Development Setup

1. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   - Copy `.env.example` to `.env`
   - Update database and Redis settings if needed

4. **Run migrations**
   ```bash
   python manage.py migrate
   ```

5. **Create sample data**
   ```bash
   python manage.py create_sample_data
   ```

6. **Start Redis** (in separate terminal)
   ```bash
   redis-server
   ```

7. **Start Celery worker** (in separate terminal)
   ```bash
   celery -A logistics_portal worker --loglevel=info
   ```

8. **Start Django development server**
   ```bash
   python manage.py runserver
   ```

## Sample Data

The `create_sample_data` command creates:

### Company 1: Acme Corporation
- **Admin**: `admin1` / `admin123`
- **Operator**: `operator1` / `operator123`
- **Viewer**: `viewer1` / `viewer123`
- **Products**: Widget A, Widget B, Gadget X

### Company 2: Tech Solutions Inc
- **Admin**: `admin2` / `admin123`
- **Products**: Server Rack, Network Switch

## API Usage

### Authentication

Get JWT token:
```bash
curl -X POST http://localhost/api/token/ \\
  -H "Content-Type: application/json" \\
  -d '{"username": "operator1", "password": "operator123"}'
```

Response:
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

### API Endpoints

#### Products
```bash
# List products
GET /api/products/
Authorization: Bearer {access_token}
```

#### Orders
```bash
# List orders
GET /api/orders/
Authorization: Bearer {access_token}

# Create order
POST /api/orders/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "product": 1,
  "quantity": 5
}

# Bulk create orders
POST /api/orders/bulk/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "orders": [
    {"product": 1, "quantity": 5},
    {"product": 2, "quantity": 10}
  ]
}

# Retry failed order
POST /api/orders/{id}/retry/
Authorization: Bearer {access_token}
```

#### Exports
```bash
# List exports
GET /api/exports/
Authorization: Bearer {access_token}

# Download export
GET /api/exports/{id}/download/
Authorization: Bearer {access_token}
```

## Django Admin Features

Access at http://localhost/admin/

### Admin Actions

1. **Export Selected Orders**: Creates a CSV export via Celery task
2. **Approve Selected Orders**: Manually approve pending orders
3. **Retry Failed Orders**: Re-queue failed orders for processing
4. **Block Profiles with 3+ Failed Orders**: Automatically block users with multiple failures

### Multi-tenancy

- Superusers see all data
- Admins see all company data
- Operators see only their own orders
- Viewers have read-only access

## Background Processing

### Order Processing Flow

1. Order created → Status: `pending`
2. Celery task triggered → Status: `processing`
3. Simulated external API call (1-3 seconds)
4. Random approval/failure (70% approval rate)
5. If approved: Stock deducted → Status: `approved`
6. If failed: Status: `failed`
7. `has_been_processed` = True

### Export Generation

1. Admin selects orders and triggers export action
2. Export record created with status: `pending`
3. Celery task generates CSV file
4. Export status updated to: `ready`
5. File available for download via API or admin

## Retry Logic

Orders can be retried if:
- Status is `failed`
- `has_been_processed` is `True`

Retry process:
1. Reset status to `pending`
2. Set `has_been_processed` to `False`
3. Trigger new Celery processing task

## Health Check

```bash
curl http://localhost/health/
```

Response:
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "celery": "configured"
}
```

## Testing

Run tests:
```bash
python manage.py test
```

With Docker:
```bash
docker compose exec web python manage.py test
```

## Logging

All order transitions, exports, and external calls are logged:
- Order processing: INFO level
- Failures: WARNING/ERROR level
- Export generation: INFO level

View logs:
```bash
# Docker
docker compose logs -f web
docker compose logs -f worker

# Local
# Check console output
```

## Architecture Notes

### Multi-tenancy Implementation
- Company-based data isolation via foreign keys
- QuerySet filtering in admin and API
- Row-level security enforced at application level

### Permissions
- `IsCompanyMember`: Ensures access to company data only
- `IsOperator`: Operator and Admin roles
- `IsViewer`: Read-only access
- `IsAdmin`: Admin-only actions
- All permissions check `is_blocked` status

### Celery Tasks
- `process_order(order_id)`: Async order processing
- `generate_export(export_id, order_ids)`: CSV generation

## Troubleshooting

### Database connection errors
- Ensure PostgreSQL is running
- Check `.env` database credentials
- Wait for DB to be ready in Docker: `docker-compose logs db`

### Celery not processing tasks
- Ensure Redis is running
- Check worker logs: `docker-compose logs worker`
- Verify Celery broker URL in settings

### Permission denied errors
- Ensure user has a Profile
- Check user's role and company
- Verify `is_blocked` is False

## Bonus Features (Completed ✅)

- [x] **CSV product upload via admin** - See [Bonus Features Documentation](BONUS_FEATURES.md#1-csv-product-upload)
- [x] **Company feature toggles** - See [Bonus Features Documentation](BONUS_FEATURES.md#2-company-feature-toggles)
- [x] **API rate limiting (Token Bucket)** - See [Bonus Features Documentation](BONUS_FEATURES.md#3-api-rate-limiting-token-bucket-algorithm)

For detailed documentation on bonus features, see [BONUS_FEATURES.md](BONUS_FEATURES.md)


## License

This project is for assignment purposes.

## Author

Developed as part of Backend Engineer Assignment
