# Quick Reference Guide

## Common Commands

### Docker Operations
```bash
# Start all services
docker-compose up

# Start in background
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f web
docker-compose logs -f worker

# Rebuild after code changes
docker-compose up --build

# Execute commands in container
docker-compose exec web python manage.py <command>
```

### Database Operations
```bash
# Create migrations
docker-compose exec web python manage.py makemigrations

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Create sample data
docker-compose exec web python manage.py create_sample_data

# Django shell
docker-compose exec web python manage.py shell
```

### Testing
```bash
# Run all tests
docker-compose exec web python manage.py test

# Run specific test file
docker-compose exec web python manage.py test core.tests

# Run with verbosity
docker-compose exec web python manage.py test --verbosity=2
```

### Celery Operations
```bash
# View worker logs
docker-compose logs -f worker

# Restart worker
docker-compose restart worker

# Check Celery status (inside container)
docker-compose exec worker celery -A logistics_portal inspect active
```

## API Examples

### Get JWT Token
```bash
curl -X POST http://localhost/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "operator1", "password": "operator123"}'
```

### List Products
```bash
curl -X GET http://localhost/api/products/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Create Order
```bash
curl -X POST http://localhost/api/orders/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"product": 1, "quantity": 5}'
```

### Bulk Create Orders
```bash
curl -X POST http://localhost/api/orders/bulk/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "orders": [
      {"product": 1, "quantity": 5},
      {"product": 2, "quantity": 10}
    ]
  }'
```

### Retry Failed Order
```bash
curl -X POST http://localhost/api/orders/1/retry/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### List Exports
```bash
curl -X GET http://localhost/api/exports/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Download Export
```bash
curl -X GET http://localhost/api/exports/1/download/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -o export.csv
```

### Health Check
```bash
curl http://localhost/health/
```

## Sample Credentials

### Company 1: Acme Corporation
- **Admin**: `admin1` / `admin123`
- **Operator**: `operator1` / `operator123`
- **Viewer**: `viewer1` / `viewer123`

### Company 2: Tech Solutions Inc
- **Admin**: `admin2` / `admin123`

## Django Admin URLs

- Main Admin: http://localhost/admin/
- Companies: http://localhost/admin/core/company/
- Profiles: http://localhost/admin/core/profile/
- Products: http://localhost/admin/core/product/
- Orders: http://localhost/admin/core/order/
- Exports: http://localhost/admin/core/export/
- Users: http://localhost/admin/auth/user/

## Troubleshooting

### Database not ready
```bash
# Wait a few seconds and retry
docker-compose logs db

# Restart services
docker-compose restart
```

### Celery not processing
```bash
# Check worker logs
docker-compose logs worker

# Restart worker
docker-compose restart worker

# Check Redis
docker-compose exec redis redis-cli ping
```

### Port already in use
```bash
# Change port in docker-compose.yml
# For example, change "80:80" to "8080:80"
```

### Clear all data and restart
```bash
docker-compose down -v  # Removes volumes
docker-compose up --build
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py create_sample_data
```

## File Locations

- **Models**: `core/models.py`
- **Admin**: `core/admin.py`
- **Tasks**: `core/tasks.py`
- **API Views**: `api/views.py`
- **API Serializers**: `api/serializers.py`
- **Permissions**: `api/permissions.py`
- **Settings**: `logistics_portal/settings.py`
- **URLs**: `logistics_portal/urls.py`, `api/urls.py`
- **Docker**: `docker-compose.yml`, `Dockerfile`, `nginx.conf`
- **Env**: `.env`
