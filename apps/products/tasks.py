"""
Asynchronous tasks for handling product operations like import/export and data processing.
"""
import os
import logging
import tempfile
from datetime import datetime, timedelta
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _
from celery.utils.log import get_task_logger
from celery import shared_task

from apps.core.tasks import BaseTask, atomic_task, long_running_task
from apps.core.utils.redis_connection import get_redis_client
from .utils import (
    export_products_to_csv, export_products_to_json, export_products_to_xml,
    import_products_from_csv, import_products_from_json, import_products_from_xml
)
from .models import Product, Category

User = get_user_model()
logger = get_task_logger(__name__)

# Task status constants
TASK_STATUS_PENDING = 'pending'
TASK_STATUS_PROCESSING = 'processing'
TASK_STATUS_COMPLETE = 'complete'
TASK_STATUS_FAILED = 'failed'

class ProductImportTask(BaseTask):
    """Base task for product import operations with enhanced error handling"""
    name = 'products.import'
    
    def cleanup_on_failure(self, task_id, args, kwargs):
        """Clean up any temporary files or resources on failure"""
        file_path = kwargs.get('file_path')
        if file_path and os.path.exists(file_path):
            try:
                logger.info(f"Cleaning up temporary file: {file_path}")
                os.unlink(file_path)
            except OSError as e:
                logger.error(f"Failed to clean up temporary file {file_path}: {e}")
        
        # Store task status in Redis
        redis_client = get_redis_client()
        redis_client.hset(f"task_status:{task_id}", "status", TASK_STATUS_FAILED)
        
        # Notify user if possible
        user_id = kwargs.get('user_id')
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                if user.email:
                    send_mail(
                        _('Product Import Failed'),
                        _('Your product import task has failed. Please check the logs for details.'),
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                        fail_silently=True,
                    )
            except User.DoesNotExist:
                logger.error(f"User with ID {user_id} not found for notification")
            except Exception as e:
                logger.error(f"Failed to send failure notification: {e}")

@shared_task(base=ProductImportTask, bind=True)
def process_product_import(self, file_path, file_format, user_id=None):
    """
    Process product import from a file asynchronously.
    
    Args:
        file_path: Path to the file to import
        file_format: Format of the file (csv, json, xml)
        user_id: ID of the user who initiated the import
        
    Returns:
        dict: Import results with counts of products created/updated/failed
    """
    task_id = self.request.id
    redis_client = get_redis_client()
    
    # Store task status in Redis
    redis_client.hset(f"task_status:{task_id}", mapping={
        "status": TASK_STATUS_PROCESSING,
        "file_format": file_format,
        "started_at": datetime.now().isoformat(),
        "user_id": str(user_id) if user_id else "unknown",
    })
    
    try:
        logger.info(f"Starting product import from {file_format} file: {file_path}")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Import file not found: {file_path}")
        
        # Process the file based on format
        if file_format == 'csv':
            with open(file_path, 'rb') as f:
                results = import_products_from_csv(f)
        elif file_format == 'json':
            with open(file_path, 'rb') as f:
                results = import_products_from_json(f)
        elif file_format == 'xml':
            with open(file_path, 'rb') as f:
                results = import_products_from_xml(f)
        else:
            raise ValueError(f"Unsupported file format: {file_format}")
        
        # Store results in Redis (for later retrieval)
        redis_client.hset(f"task_status:{task_id}", mapping={
            "status": TASK_STATUS_COMPLETE,
            "completed_at": datetime.now().isoformat(),
            "created": str(results.get('created', 0)),
            "updated": str(results.get('updated', 0)),
            "failed": str(results.get('failed', 0)),
            "total": str(results.get('total', 0)),
        })
        
        # Send notification email if user_id is provided
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                if user.email:
                    send_mail(
                        _('Product Import Complete'),
                        _(f'Your product import has been completed.\n\n'
                          f'Total: {results.get("total", 0)}\n'
                          f'Created: {results.get("created", 0)}\n'
                          f'Updated: {results.get("updated", 0)}\n'
                          f'Failed: {results.get("failed", 0)}'),
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                        fail_silently=True,
                    )
            except User.DoesNotExist:
                logger.error(f"User with ID {user_id} not found for notification")
            except Exception as e:
                logger.error(f"Failed to send completion notification: {e}")
        
        # Clean up temporary file
        try:
            os.unlink(file_path)
            logger.info(f"Temporary file removed: {file_path}")
        except OSError as e:
            logger.error(f"Failed to remove temporary file {file_path}: {e}")
        
        logger.info(f"Product import completed: {results}")
        return results
        
    except Exception as e:
        logger.error(f"Product import failed: {str(e)}", exc_info=True)
        
        # Update status in Redis
        redis_client.hset(f"task_status:{task_id}", mapping={
            "status": TASK_STATUS_FAILED,
            "error": str(e),
            "completed_at": datetime.now().isoformat(),
        })
        
        # Re-raise for retry handling by Celery
        raise

class ProductExportTask(BaseTask):
    """Base task for product export operations with enhanced error handling"""
    name = 'products.export'
    
    def cleanup_on_failure(self, task_id, args, kwargs):
        """Clean up any temporary files or resources on failure"""
        # Similar logic to import task cleanup
        export_path = kwargs.get('export_path')
        if export_path and os.path.exists(export_path):
            try:
                logger.info(f"Cleaning up temporary export file: {export_path}")
                os.unlink(export_path)
            except OSError as e:
                logger.error(f"Failed to clean up temporary export file {export_path}: {e}")
        
        # Store task status in Redis
        redis_client = get_redis_client()
        redis_client.hset(f"task_status:{task_id}", "status", TASK_STATUS_FAILED)
        
        # Notify user if possible
        user_id = kwargs.get('user_id')
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                if user.email:
                    send_mail(
                        _('Product Export Failed'),
                        _('Your product export task has failed. Please check the logs for details.'),
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                        fail_silently=True,
                    )
            except User.DoesNotExist:
                logger.error(f"User with ID {user_id} not found for notification")
            except Exception as e:
                logger.error(f"Failed to send failure notification: {e}")

@shared_task(base=ProductExportTask, bind=True)
def process_product_export(self, category_id=None, file_format='csv', user_id=None):
    """
    Process product export to a file asynchronously.
    
    Args:
        category_id: Optional category ID to filter products
        file_format: Format for the export (csv, json, xml)
        user_id: ID of the user who initiated the export
        
    Returns:
        dict: Export results with counts and download URL
    """
    task_id = self.request.id
    redis_client = get_redis_client()
    
    # Create exports directory if it doesn't exist
    exports_dir = os.path.join(settings.MEDIA_ROOT, 'exports')
    os.makedirs(exports_dir, exist_ok=True)
    
    # Generate unique filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"products_export_{timestamp}.{file_format}"
    export_path = os.path.join(exports_dir, filename)
    
    # Store task status in Redis
    redis_client.hset(f"task_status:{task_id}", mapping={
        "status": TASK_STATUS_PROCESSING,
        "file_format": file_format,
        "started_at": datetime.now().isoformat(),
        "user_id": str(user_id) if user_id else "unknown",
    })
    
    try:
        # Get products, optionally filtered by category
        products = Product.objects.filter(is_active=True)
        
        if category_id:
            try:
                category = Category.objects.get(id=category_id)
                products = products.filter(category=category)
                category_name = category.name
            except Category.DoesNotExist:
                logger.warning(f"Category with ID {category_id} not found, exporting all products")
                category_name = "All Categories"
        else:
            category_name = "All Categories"
        
        # Count of products to export
        count = products.count()
        logger.info(f"Exporting {count} products from {category_name} in {file_format} format")
        
        # Export based on format
        if file_format == 'csv':
            with open(export_path, 'wb') as f:
                export_products_to_csv(products, f)
        elif file_format == 'json':
            with open(export_path, 'wb') as f:
                export_products_to_json(products, f)
        elif file_format == 'xml':
            with open(export_path, 'wb') as f:
                export_products_to_xml(products, f)
        else:
            raise ValueError(f"Unsupported export format: {file_format}")
        
        # Generate download URL
        download_url = f"{settings.BASE_URL}{settings.MEDIA_URL}exports/{filename}"
        
        # Store results in Redis
        redis_client.hset(f"task_status:{task_id}", mapping={
            "status": TASK_STATUS_COMPLETE,
            "completed_at": datetime.now().isoformat(),
            "count": str(count),
            "download_url": download_url,
            "filename": filename,
        })
        
        # Set expiration for the task status (1 week)
        redis_client.expire(f"task_status:{task_id}", 60 * 60 * 24 * 7)
        
        # Send notification email
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                if user.email:
                    send_mail(
                        _('Product Export Complete'),
                        _(f'Your product export has been completed.\n\n'
                          f'Category: {category_name}\n'
                          f'Format: {file_format}\n'
                          f'Products: {count}\n\n'
                          f'Download: {download_url}\n\n'
                          f'The download link will be available for 7 days.'),
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                        fail_silently=True,
                    )
            except User.DoesNotExist:
                logger.error(f"User with ID {user_id} not found for notification")
            except Exception as e:
                logger.error(f"Failed to send completion notification: {e}")
        
        results = {
            'count': count,
            'category': category_name,
            'format': file_format,
            'download_url': download_url,
            'filename': filename,
        }
        
        logger.info(f"Product export completed: {results}")
        return results
        
    except Exception as e:
        logger.error(f"Product export failed: {str(e)}", exc_info=True)
        
        # Clean up export file if it exists
        if os.path.exists(export_path):
            try:
                os.unlink(export_path)
            except OSError:
                pass
        
        # Update status in Redis
        redis_client.hset(f"task_status:{task_id}", mapping={
            "status": TASK_STATUS_FAILED,
            "error": str(e),
            "completed_at": datetime.now().isoformat(),
        })
        
        # Re-raise for retry handling
        raise

@shared_task
def clean_old_export_files():
    """
    Clean up old export files (older than 7 days).
    This task is scheduled to run daily.
    """
    exports_dir = os.path.join(settings.MEDIA_ROOT, 'exports')
    if not os.path.exists(exports_dir):
        logger.info("Exports directory does not exist, nothing to clean up")
        return
    
    cutoff_date = datetime.now() - timedelta(days=7)
    deleted_count = 0
    
    for filename in os.listdir(exports_dir):
        file_path = os.path.join(exports_dir, filename)
        
        # Skip if not a file
        if not os.path.isfile(file_path):
            continue
        
        # Get file modification time
        file_modified = datetime.fromtimestamp(os.path.getmtime(file_path))
        
        # Delete if older than cutoff date
        if file_modified < cutoff_date:
            try:
                os.unlink(file_path)
                deleted_count += 1
                logger.info(f"Deleted old export file: {filename}")
            except OSError as e:
                logger.error(f"Failed to delete old export file {filename}: {e}")
    
    logger.info(f"Cleaned up {deleted_count} old export files")
    return {'deleted_count': deleted_count} 