#!/usr/bin/env python
"""
Test script to verify Celery and Redis configuration.
This script helps verify that:
1. Redis connection works
2. Celery tasks can be created and executed
3. Results can be stored and retrieved
"""
import os
import sys
import time
import django
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Import Celery app
from config.celery import app

# Create a test task
@app.task
def test_task(message):
    """Test task that returns a message with timestamp"""
    time.sleep(2)  # Simulate work
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"Task completed at {now}: {message}"

def main():
    """Run test to verify Celery and Redis configuration"""
    print("Testing Celery and Redis configuration...")
    
    # Test Redis connection
    try:
        from redis import Redis
        from django.conf import settings
        
        redis_url = settings.CELERY_BROKER_URL
        print(f"Connecting to Redis at: {redis_url}")
        
        if redis_url.startswith('redis://'):
            # Extract host, port, db from redis URL
            # Format: redis://[:password@]host[:port][/db-number]
            parts = redis_url.replace('redis://', '').split('@')
            if len(parts) > 1:
                # Password included
                password = parts[0]
                host_port_db = parts[1]
            else:
                password = None
                host_port_db = parts[0]
            
            # Split host, port, db
            host_port, *db_parts = host_port_db.split('/')
            host_parts = host_port.split(':')
            
            host = host_parts[0]
            port = int(host_parts[1]) if len(host_parts) > 1 else 6379
            db = int(db_parts[0]) if db_parts else 0
            
            # Connect to Redis
            redis_client = Redis(host=host, port=port, db=db, password=password)
        else:
            # Use URL directly
            redis_client = Redis.from_url(redis_url)
        
        # Test Redis connection
        redis_client.ping()
        print("✅ Redis connection successful!")
        
        # Test Redis write/read
        test_key = "celery_test_key"
        test_value = f"Test value at {datetime.now()}"
        redis_client.set(test_key, test_value)
        retrieved_value = redis_client.get(test_key)
        
        if retrieved_value.decode('utf-8') == test_value:
            print("✅ Redis write/read test successful!")
        else:
            print("❌ Redis write/read test failed!")
        
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return
    
    # Test Celery task execution
    try:
        print("\nSending test task to Celery...")
        result = test_task.delay("Hello from test script")
        
        print("Waiting for task result...")
        task_id = result.id
        print(f"Task ID: {task_id}")
        
        # Wait for the task to complete (with timeout)
        timeout = 10
        start_time = time.time()
        while not result.ready():
            if time.time() - start_time > timeout:
                print("❌ Task execution timed out!")
                return
            print(".", end="", flush=True)
            time.sleep(0.5)
        
        print("\n")
        if result.successful():
            print(f"✅ Task executed successfully!")
            print(f"Result: {result.get()}")
        else:
            print("❌ Task execution failed!")
            try:
                result.get()  # This will re-raise the exception
            except Exception as e:
                print(f"Error: {e}")
        
    except Exception as e:
        print(f"❌ Celery task test failed: {e}")
        return
    
    print("\n🎉 Celery and Redis configuration is working correctly!")

if __name__ == "__main__":
    main() 