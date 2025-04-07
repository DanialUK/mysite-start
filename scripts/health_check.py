#!/usr/bin/env python
"""
Health check script for Redis and Celery.
Run this script to verify the health of Redis and Celery services.

Usage:
    python health_check.py [--celery] [--redis] [--quiet]

Options:
    --celery  Check Celery worker health
    --redis   Check Redis connection
    --quiet   Only output errors (for use in scripts)
"""
import os
import sys
import time
import argparse
import django
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from config.celery import app as celery_app
from apps.core.utils.redis_connection import get_redis_client, RedisConnectionError

HEALTH_CHECK_KEY = "health_check"
HEALTH_CHECK_TIMEOUT = 10  # seconds

def check_redis(verbose=True):
    """
    Check Redis connection health
    
    Args:
        verbose (bool): Whether to print status messages
        
    Returns:
        bool: True if Redis is healthy, False otherwise
    """
    try:
        if verbose:
            print("Checking Redis connection...")
        
        # Get Redis client
        redis_client = get_redis_client()
        
        # Ping Redis
        start_time = time.time()
        redis_client.ping()
        ping_time = time.time() - start_time
        
        # Write and read test data
        test_value = f"health_check_{datetime.now().isoformat()}"
        redis_client.set(HEALTH_CHECK_KEY, test_value, ex=60)
        retrieved = redis_client.get(HEALTH_CHECK_KEY)
        
        if retrieved and retrieved.decode('utf-8') == test_value:
            if verbose:
                print(f"✅ Redis is healthy (ping: {ping_time:.3f}s)")
                
                # Get Redis info
                info = redis_client.info()
                print(f"  • Redis version: {info.get('redis_version', 'unknown')}")
                print(f"  • Connected clients: {info.get('connected_clients', 'unknown')}")
                print(f"  • Used memory: {info.get('used_memory_human', 'unknown')}")
                print(f"  • Used memory peak: {info.get('used_memory_peak_human', 'unknown')}")
                print(f"  • Total connections received: {info.get('total_connections_received', 'unknown')}")
                print(f"  • Total commands processed: {info.get('total_commands_processed', 'unknown')}")
            return True
        else:
            if verbose:
                print("❌ Redis read/write test failed")
            return False
            
    except RedisConnectionError as e:
        print(f"❌ Redis connection error: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Redis check failed: {str(e)}")
        return False

def check_celery(verbose=True):
    """
    Check Celery worker health
    
    Args:
        verbose (bool): Whether to print status messages
        
    Returns:
        bool: True if Celery is healthy, False otherwise
    """
    try:
        if verbose:
            print("Checking Celery worker health...")
        
        # Check if there are active workers
        workers = celery_app.control.inspect().active_queues()
        
        if not workers:
            print("❌ No Celery workers are running")
            return False
        
        if verbose:
            print(f"✅ Found {len(workers)} Celery workers")
            for worker_name, queues in workers.items():
                print(f"  • Worker: {worker_name}")
                print(f"    - Queues: {', '.join(q['name'] for q in queues)}")
        
        # Send a ping to all workers
        ping = celery_app.control.ping()
        
        if not ping:
            print("❌ No response from Celery workers")
            return False
        
        # Execute a simple task and wait for result
        if verbose:
            print("Executing test task...")
        
        result = celery_app.send_task('config.celery.debug_task')
        
        start_time = time.time()
        while not result.ready():
            if time.time() - start_time > HEALTH_CHECK_TIMEOUT:
                if verbose:
                    print("❌ Task execution timed out")
                return False
            time.sleep(0.5)
        
        # If we got here, the task completed
        if verbose:
            print(f"✅ Test task completed successfully in {time.time() - start_time:.2f}s")
        
        return True
    except Exception as e:
        print(f"❌ Celery check failed: {str(e)}")
        return False

def main():
    """
    Main health check function
    """
    parser = argparse.ArgumentParser(description="Health check for Redis and Celery")
    parser.add_argument("--celery", action="store_true", help="Check Celery worker health")
    parser.add_argument("--redis", action="store_true", help="Check Redis connection")
    parser.add_argument("--quiet", action="store_true", help="Only output errors")
    args = parser.parse_args()
    
    # If no specific checks are requested, check both
    if not args.celery and not args.redis:
        args.celery = True
        args.redis = True
    
    verbose = not args.quiet
    redis_healthy = True
    celery_healthy = True
    
    if verbose:
        print("=" * 50)
        print(f"HEALTH CHECK - {datetime.now().isoformat()}")
        print("=" * 50)
    
    if args.redis:
        redis_healthy = check_redis(verbose)
        
    if args.celery:
        celery_healthy = check_celery(verbose)
    
    if verbose:
        print("=" * 50)
        print("Health Check Summary:")
        print(f"Redis: {'HEALTHY' if redis_healthy else 'UNHEALTHY'}")
        print(f"Celery: {'HEALTHY' if celery_healthy else 'UNHEALTHY'}")
        print("=" * 50)
    
    # Exit with appropriate status code
    if redis_healthy and celery_healthy:
        if verbose:
            print("All services are healthy! 🎉")
        sys.exit(0)
    else:
        if verbose:
            print("Some services are unhealthy! 🚨")
        sys.exit(1)

if __name__ == "__main__":
    main() 