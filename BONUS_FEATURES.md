# Bonus Features Documentation

This document provides detailed information about the three bonus features implemented in the B2B Logistics Portal.

## Table of Contents
1. [CSV Product Upload](#1-csv-product-upload)
2. [Company Feature Toggles](#2-company-feature-toggles)
3. [API Rate Limiting](#3-api-rate-limiting-token-bucket-algorithm)

---

## 1. CSV Product Upload

### Overview
Bulk upload products via CSV files through the Django Admin interface with automatic validation and error reporting.

### Features
- ✅ Async processing via Celery
- ✅ Row-by-row validation
- ✅ Create or update existing products
- ✅ Comprehensive error logging
- ✅ Company isolation
- ✅ Feature toggle integration

### CSV Format
```csv
SKU,Name,Stock Quantity
PROD-001,Product Name,100
PROD-002,Another Product,50
```

### Usage

1. **Access Admin**: http://localhost/admin/core/productupload/
2. **Click "Add Product Upload"**
3. **Select CSV file** (see `sample_products.csv` for example)
4. **Click Save** - Upload queued for processing
5. **View Results**: Check `processed_count`, `error_count`, and `errors_log`

### Example
```bash
# Sample CSV file provided
cat sample_products.csv
```

### Admin Interface
- Upload history with status tracking
- Error logs for failed rows
- Automatic company assignment
- Feature toggle check before upload

---

## 2. Company Feature Toggles

### Overview
Enable/disable specific features per company for fine-grained access control.

### Available Toggles
- `bulk_orders_enabled`: Allow bulk order creation via API
- `exports_enabled`: Allow order export downloads
- `api_access_enabled`: Allow API access (future use)
- `csv_upload_enabled`: Allow CSV product uploads

### Features
- ✅ Per-company configuration
- ✅ Default all features enabled
- ✅ Automatic toggle creation
- ✅ API integration
- ✅ Admin integration

### Usage

#### Via Admin
1. Navigate to: http://localhost/admin/core/companyfeaturetoggle/
2. Select company's toggle
3. Enable/disable features
4. Save changes

#### API Behavior
When a feature is disabled:
```json
{
  "error": "Bulk orders are disabled for your company"
}
```
HTTP Status: 403 Forbidden

### Testing
```bash
# Disable bulk orders for Company 1
# Then try bulk order creation
curl -X POST http://localhost/api/orders/bulk/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"orders": [{"product": 1, "quantity": 5}]}'

# Response: 403 Forbidden
```

---

## 3. API Rate Limiting (Token Bucket Algorithm)

### Overview
Implements token bucket algorithm for API throttling with Redis backend to prevent abuse and ensure fair usage.

### Rate Limits

| Endpoint | Capacity | Refill Rate |
|----------|----------|-------------|
| Products | 100 tokens | 100/minute |
| Orders | 50 tokens | 50/minute |
| Exports | 10 tokens | 10/minute |

### Features
- ✅ Token bucket algorithm
- ✅ Redis-backed distributed state
- ✅ Per-user rate limiting
- ✅ Different rates per endpoint
- ✅ Superuser bypass
- ✅ Automatic token refill

### How It Works

1. Each user gets a bucket with tokens
2. Each request consumes 1 token
3. Tokens refill at specified rate
4. If no tokens available → 429 Too Many Requests

### Testing

```bash
# Get authentication token
TOKEN=$(curl -s -X POST http://localhost/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "operator1", "password": "operator123"}' \
  | jq -r '.access')

# Make 100 requests (should all succeed)
for i in {1..100}; do
  curl -s -X GET http://localhost/api/products/ \
    -H "Authorization: Bearer $TOKEN" > /dev/null
  echo "Request $i completed"
done

# 101st request should be throttled
curl -X GET http://localhost/api/products/ \
  -H "Authorization: Bearer $TOKEN" \
  -w "\nStatus: %{http_code}\n"

# Expected: 429 Too Many Requests

# Wait 6 seconds (10 tokens/min = 1 token per 6 seconds)
sleep 6

# Next request should succeed
curl -X GET http://localhost/api/products/ \
  -H "Authorization: Bearer $TOKEN" \
  -w "\nStatus: %{http_code}\n"
```

### Response When Throttled
```json
{
  "detail": "Request was throttled. Expected available in 6 seconds."
}
```
HTTP Status: 429 Too Many Requests

### Configuration

Adjust rates in `api/throttling.py`:
```python
class OrdersThrottle(TokenBucketThrottle):
    capacity = 50  # Maximum burst
    refill_rate = 50 / 60  # Tokens per second
```

---

## Implementation Details

### New Models
- `CompanyFeatureToggle`: OneToOne with Company
- `ProductUpload`: Tracks CSV upload history

### New Files
- `api/throttling.py`: Token bucket implementation
- `sample_products.csv`: Example CSV file

### Modified Files
- `core/models.py`: Added new models
- `core/admin.py`: Added admin classes
- `core/tasks.py`: Added `process_product_upload` task
- `api/permissions.py`: Added `HasFeatureEnabled`
- `api/views.py`: Added throttling and feature checks
- `logistics_portal/settings.py`: Added cache configuration

### Database Migrations
```bash
# New migration created
core/migrations/0002_productupload_companyfeaturetoggle.py
```

---

## Troubleshooting

### CSV Upload Issues

**Problem**: Upload stuck in "pending"
**Solution**: Check Celery worker logs
```bash
docker compose logs -f worker
```

**Problem**: All rows have errors
**Solution**: Verify CSV format matches: `SKU,Name,Stock Quantity`

### Feature Toggle Issues

**Problem**: Feature toggle doesn't exist
**Solution**: Automatically created on first check, or create manually in admin

### Rate Limiting Issues

**Problem**: Always getting 429
**Solution**: Check Redis connection
```bash
docker compose exec redis redis-cli ping
```

**Problem**: Rate limits not working
**Solution**: Ensure cache is configured correctly in settings

---

## Benefits

### CSV Upload
- **Efficiency**: Bulk product management saves time
- **Validation**: Immediate feedback on errors
- **Async**: Non-blocking uploads
- **Audit**: Complete upload history

### Feature Toggles
- **Flexibility**: Control features per company
- **Gradual Rollout**: Enable features selectively
- **Safety**: Disable problematic features quickly
- **Access Control**: Fine-grained permissions

### Rate Limiting
- **Protection**: Prevents API abuse
- **Fairness**: Equal access for all users
- **Performance**: Prevents server overload
- **Scalability**: Distributed state with Redis

---

## Summary

All three bonus features are fully implemented and production-ready:

✅ **CSV Product Upload**: Complete with admin interface, Celery processing, and error handling  
✅ **Company Feature Toggles**: Integrated with API and admin, automatic creation  
✅ **Token Bucket Rate Limiting**: Redis-backed, per-endpoint rates, superuser bypass

For more technical details, see the [Bonus Features Walkthrough](../brain/bonus_features_walkthrough.md) in the artifacts directory.
