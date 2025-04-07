from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
import os
import logging
import tempfile
import time
from datetime import datetime, timedelta

from .utils import (
    export_products_to_csv, export_products_to_json, export_products_to_xml,
    import_products_from_csv, import_products_from_json, import_products_from_xml
)
from .models import Product, Category

logger = logging.getLogger(__name__)
User = get_user_model()

@shared_task
def process_product_import(file_path, file_format, user_id):
    """
    Асинхронная обработка импорта товаров
    """
    try:
        user = User.objects.get(id=user_id)
        
        with open(file_path, 'rb') as file:
            if file_format == 'csv':
                results = import_products_from_csv(file)
            elif file_format == 'json':
                results = import_products_from_json(file)
            elif file_format == 'xml':
                results = import_products_from_xml(file)
        
        # Отправляем уведомление пользователю
        subject = 'Импорт товаров завершен'
        message = f"""Ваш импорт товаров завершен.
        
        Результаты:
        - Создано: {results['created']}
        - Обновлено: {results['updated']}
        - Ошибки: {len(results['errors'])}
        
        {'Первые 5 ошибок:' if results['errors'] else ''}
        {chr(10).join(results['errors'][:5])}
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        
        # Логируем результаты
        logger.info(
            f"Import completed by user {user.username}. "
            f"Created: {results['created']}, Updated: {results['updated']}, "
            f"Errors: {len(results['errors'])}"
        )
        
        # Удаляем временный файл
        try:
            os.unlink(file_path)
        except Exception as e:
            logger.warning(f"Failed to delete temporary file {file_path}: {str(e)}")
        
        return results
        
    except Exception as e:
        logger.error(f"Error processing import: {str(e)}")
        
        # Пытаемся отправить уведомление об ошибке
        try:
            user = User.objects.get(id=user_id)
            send_mail(
                subject='Ошибка импорта товаров',
                message=f"При импорте товаров произошла ошибка: {str(e)}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception as mail_error:
            logger.error(f"Failed to send error notification: {str(mail_error)}")
        
        # Пытаемся удалить временный файл
        try:
            os.unlink(file_path)
        except:
            pass
        
        return {'created': 0, 'updated': 0, 'errors': [str(e)]}

@shared_task
def process_product_export(file_format, category_id, user_id):
    """
    Асинхронная обработка экспорта товаров
    """
    try:
        user = User.objects.get(id=user_id)
        
        # Фильтруем товары по категории, если указана
        products = Product.objects.all()
        if category_id:
            category = Category.objects.get(id=category_id)
            products = products.filter(category=category)
            category_name = category.name
        else:
            category_name = "All"
        
        # Создаем временный файл
        now = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            if file_format == 'csv':
                filename = f'products_export_{category_name}_{now}.csv'
                filepath = export_products_to_csv(products, temp_file.name)
                content_type = 'text/csv'
            elif file_format == 'json':
                filename = f'products_export_{category_name}_{now}.json'
                filepath = export_products_to_json(products, temp_file.name)
                content_type = 'application/json'
            elif file_format == 'xml':
                filename = f'products_export_{category_name}_{now}.xml'
                filepath = export_products_to_xml(products, temp_file.name)
                content_type = 'application/xml'
        
        # Сохраняем файл в медиа-директорию
        export_dir = os.path.join(settings.MEDIA_ROOT, 'exports')
        os.makedirs(export_dir, exist_ok=True)
        
        target_file = os.path.join(export_dir, filename)
        os.rename(filepath, target_file)
        
        download_url = f"{settings.MEDIA_URL}exports/{filename}"
        
        # Отправляем уведомление пользователю
        subject = f'Экспорт товаров {category_name} завершен'
        message = f"""Ваш экспорт товаров завершен.
        
        Информация:
        - Категория: {category_name}
        - Формат: {file_format.upper()}
        - Количество товаров: {products.count()}
        
        Скачать файл: {settings.BASE_URL}{download_url}
        
        Файл будет доступен в течение 48 часов.
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        
        # Логируем результаты
        logger.info(
            f"Export completed by user {user.username}. "
            f"Format: {file_format}, Category: {category_name}, "
            f"Products: {products.count()}"
        )
        
        return {'success': True, 'download_url': download_url, 'filename': filename}
        
    except Exception as e:
        logger.error(f"Error processing export: {str(e)}")
        
        # Пытаемся отправить уведомление об ошибке
        try:
            user = User.objects.get(id=user_id)
            send_mail(
                subject='Ошибка экспорта товаров',
                message=f"При экспорте товаров произошла ошибка: {str(e)}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception as mail_error:
            logger.error(f"Failed to send error notification: {str(mail_error)}")
        
        return {'success': False, 'error': str(e)}

@shared_task
def clean_old_export_files():
    """
    Периодическая задача для удаления старых экспортированных файлов (старше 48 часов)
    """
    try:
        export_dir = os.path.join(settings.MEDIA_ROOT, 'exports')
        
        if not os.path.exists(export_dir):
            return {'message': 'Exports directory does not exist', 'deleted': 0}
        
        now = time.time()
        deleted_count = 0
        
        # Ищем файлы старше 48 часов
        max_age = 48 * 3600  # 48 часов в секундах
        
        for file_name in os.listdir(export_dir):
            file_path = os.path.join(export_dir, file_name)
            
            if os.path.isfile(file_path):
                # Получаем время последнего изменения файла
                file_time = os.path.getmtime(file_path)
                
                # Если файл старше 48 часов, удаляем его
                if now - file_time > max_age:
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                    except Exception as e:
                        logger.error(f"Failed to delete old export file {file_path}: {str(e)}")
        
        logger.info(f"Cleaned up old export files. Deleted: {deleted_count}")
        return {'message': 'Cleanup completed', 'deleted': deleted_count}
        
    except Exception as e:
        logger.error(f"Error cleaning old export files: {str(e)}")
        return {'success': False, 'error': str(e)} 