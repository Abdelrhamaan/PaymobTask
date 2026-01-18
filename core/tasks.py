import random
import time
import csv
import logging
import io
from celery import shared_task
from django.core.files.base import ContentFile
from django.db import transaction
from .models import Order, Export, Product, ProductUpload

logger = logging.getLogger(__name__)


@shared_task
def process_order(order_id):
    """
    Process an order:
    1. Mark as processing
    2. Simulate external API call
    3. Randomly approve or fail
    4. Deduct stock if approved (with transaction and locking)
    5. Mark as processed
    """
    
    try:
        order = Order.objects.get(id=order_id)
        
        # Mark as processing
        order.status = 'processing'
        order.save()
        logger.info(f"Order {order.reference_code} marked as processing")

        # Simulate external service call
        time.sleep(random.uniform(1, 3))
        logger.info(f"Simulated external API call for order {order.reference_code}")

        # Randomly approve or fail (70% approval rate)
        if random.random() < 0.7:
            # Use transaction and select_for_update to prevent race conditions
            with transaction.atomic():
                # Lock the product row for update
                product = Product.objects.select_for_update().get(id=order.product.id)
                
                # Check stock availability
                if product.stock_quantity >= order.quantity:
                    # Approve and deduct stock atomically
                    product.stock_quantity -= order.quantity
                    product.save()
                    order.status = 'approved'
                    logger.info(f"Order {order.reference_code} approved. Stock deducted: {order.quantity}")
                else:
                    # Insufficient stock
                    order.status = 'failed'
                    logger.warning(f"Order {order.reference_code} failed due to insufficient stock")
        else:
            # Random failure
            order.status = 'failed'
            logger.warning(f"Order {order.reference_code} failed (simulated failure)")

        # Mark as processed
        order.has_been_processed = True
        order.save()
        
        logger.info(f"Order {order.reference_code} processing complete. Final status: {order.status}")
        
        return f"Order {order.reference_code} processed with status: {order.status}"

    except Order.DoesNotExist:
        logger.error(f"Order with ID {order_id} not found")
        return f"Order {order_id} not found"
    except Exception as e:
        logger.error(f"Error processing order {order_id}: {str(e)}")
        return f"Error: {str(e)}"


@shared_task
def generate_export(export_id, order_ids):
    """
    Generate CSV export for selected orders.
    """
    try:
        export = Export.objects.get(id=export_id)
        
        # Get orders
        orders = Order.objects.filter(id__in=order_ids).select_related('product', 'created_by__user', 'product__company')
        
        # Generate CSV
        csv_content = []
        csv_content.append(['Reference Code', 'Product', 'SKU', 'Quantity', 'Status', 'Created By', 'Company', 'Created At'])
        
        for order in orders:
            csv_content.append([
                order.reference_code,
                order.product.name,
                order.product.sku,
                order.quantity,
                order.status,
                order.created_by.user.username,
                order.product.company.name,
                order.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        # Create CSV file
        csv_buffer = []
        for row in csv_content:
            csv_buffer.append(','.join([f'"{str(cell)}"' for cell in row]))
        csv_string = '\n'.join(csv_buffer)
        
        # Save to Export model
        filename = f'export_{export_id}.csv'
        export.file.save(filename, ContentFile(csv_string.encode('utf-8')), save=False)
        export.status = 'ready'
        export.save()
        
        logger.info(f"Export {export_id} generated successfully with {len(orders)} orders")
        
        # Simulate notification
        print(f"[NOTIFICATION] Export {export_id} is ready for download by {export.requested_by.user.username}")
        logger.info(f"Notification sent for export {export_id}")
        
        return f"Export {export_id} generated successfully"

    except Export.DoesNotExist:
        logger.error(f"Export with ID {export_id} not found")
        return f"Export {export_id} not found"
    except Exception as e:
        logger.error(f"Error generating export {export_id}: {str(e)}")
        try:
            export = Export.objects.get(id=export_id)
            export.status = 'failed'
            export.note = str(e)
            export.save()
        except:
            pass
        return f"Error: {str(e)}"


@shared_task
def process_product_upload(upload_id):
    """
    Process CSV product upload.
    Expected CSV format: SKU, Name, Stock Quantity
    """
    try:
        upload = ProductUpload.objects.get(id=upload_id)
        upload.status = 'processing'
        upload.save()
        
        logger.info(f"Processing product upload {upload_id}")
        
        # Read CSV file
        file_content = upload.file.read().decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(file_content))
        
        processed_count = 0
        error_count = 0
        errors = []
        
        for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 (1 is header)
            try:
                # Validate required fields
                sku = row.get('SKU', '').strip()
                name = row.get('Name', '').strip()
                stock_quantity_str = row.get('Stock Quantity', '').strip()
                
                if not sku:
                    raise ValueError("SKU is required")
                if not name:
                    raise ValueError("Name is required")
                if not stock_quantity_str:
                    raise ValueError("Stock Quantity is required")
                
                # Parse stock quantity
                try:
                    stock_quantity = int(stock_quantity_str)
                    if stock_quantity < 0:
                        raise ValueError("Stock Quantity must be non-negative")
                except ValueError as e:
                    raise ValueError(f"Invalid Stock Quantity: {stock_quantity_str}")
                
                # Create or update product
                product, created = Product.objects.update_or_create(
                    sku=sku,
                    defaults={
                        'name': name,
                        'stock_quantity': stock_quantity,
                        'company': upload.company,
                        'is_active': True
                    }
                )
                
                processed_count += 1
                action = "created" if created else "updated"
                logger.info(f"Product {sku} {action} successfully")
                
            except Exception as e:
                error_count += 1
                error_msg = f"Row {row_num}: {str(e)}"
                errors.append(error_msg)
                logger.warning(f"Error processing row {row_num}: {str(e)}")
        
        # Update upload record
        upload.processed_count = processed_count
        upload.error_count = error_count
        upload.errors_log = '\n'.join(errors) if errors else ''
        upload.status = 'completed' if error_count == 0 else 'completed'  # Still completed even with errors
        upload.save()
        
        logger.info(f"Product upload {upload_id} completed. Processed: {processed_count}, Errors: {error_count}")
        
        # Simulate notification
        print(f"[NOTIFICATION] Product upload {upload_id} completed. {processed_count} products processed, {error_count} errors.")
        
        return f"Upload {upload_id} completed: {processed_count} processed, {error_count} errors"
        
    except ProductUpload.DoesNotExist:
        logger.error(f"ProductUpload with ID {upload_id} not found")
        return f"Upload {upload_id} not found"
    except Exception as e:
        logger.error(f"Error processing product upload {upload_id}: {str(e)}")
        try:
            upload = ProductUpload.objects.get(id=upload_id)
            upload.status = 'failed'
            upload.errors_log = str(e)
            upload.save()
        except:
            pass
        return f"Error: {str(e)}"
