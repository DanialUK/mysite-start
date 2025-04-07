import os
import logging
from celery import Celery
from celery.signals import task_failure, worker_ready, worker_shutdown
from django.conf import settings

# Set up logging
logger = logging.getLogger(__name__)

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('marketplace')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

# Define broker connection retry behavior
app.conf.broker_connection_retry = True
app.conf.broker_connection_retry_on_startup = True
app.conf.broker_connection_max_retries = 10
app.conf.broker_connection_timeout = 5  # seconds

# Task execution settings
app.conf.task_time_limit = 1800  # 30 minutes max runtime
app.conf.task_soft_time_limit = 1500  # soft limit 25 minutes
app.conf.worker_concurrency = os.cpu_count() or 4
app.conf.worker_max_tasks_per_child = 1000  # Prevent memory leaks
app.conf.worker_prefetch_multiplier = 4  # Reduces chance of broker pool exhaustion

# Task serialization - security best practice
app.conf.accept_content = ['json']
app.conf.task_serializer = 'json'
app.conf.result_serializer = 'json'

# Task failure handling
app.conf.task_acks_late = True  # tasks acknowledged after execution, not when received
app.conf.task_reject_on_worker_lost = True  # tasks requeued if worker disconnects

# Result backend settings
app.conf.result_expires = 60 * 60 * 24  # 24 hours, prevents backend DB growing indefinitely
app.conf.result_persistent = True  # Keep results even after worker restart

# Logging configuration
app.conf.worker_log_format = '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'
app.conf.worker_task_log_format = '[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s'

# Настройка периодических задач
app.conf.beat_schedule = {
    'clean-old-export-files': {
        'task': 'apps.products.tasks.clean_old_export_files',
        'schedule': 86400.0,  # раз в день
    },
}

# Configure retry policy defaults
app.conf.task_default_retry_delay = 3 * 60  # 3 minutes
app.conf.task_max_retries = 5  # 5 retries

# Signal handlers
@task_failure.connect
def handle_task_failure(task_id, exception, traceback, einfo, *args, **kwargs):
    """Log task failures with additional context"""
    logger.error(
        f"Task {task_id} failed: {exception}\n{traceback}",
        exc_info=True,
        extra={'task_id': task_id}
    )

@worker_ready.connect
def worker_ready_handler(**kwargs):
    """Log when a worker is ready"""
    logger.info("Celery worker is ready.")

@worker_shutdown.connect
def worker_shutdown_handler(**kwargs):
    """Log when a worker is shutting down"""
    logger.info("Celery worker is shutting down.")

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Task for debugging Celery worker connectivity"""
    logger.info(f'Request: {self.request!r}')
    print(f'Debug task executed with request: {self.request!r}')
    return "Debug task successfully executed" 