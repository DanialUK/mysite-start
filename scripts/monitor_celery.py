#!/usr/bin/env python
"""
Monitor Celery tasks and their status.
This script provides basic monitoring capabilities for Celery tasks.
"""
import os
import sys
import time
import django
from datetime import datetime, timedelta
from tabulate import tabulate

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def get_active_tasks():
    """Get currently active Celery tasks"""
    try:
        from celery.task.control import inspect
        
        # Create inspector
        insp = inspect()
        
        # Get active tasks
        active_tasks = insp.active()
        scheduled_tasks = insp.scheduled()
        reserved_tasks = insp.reserved()
        
        return {
            'active': active_tasks or {},
            'scheduled': scheduled_tasks or {},
            'reserved': reserved_tasks or {}
        }
    except Exception as e:
        print(f"Error getting active tasks: {e}")
        return {'active': {}, 'scheduled': {}, 'reserved': {}}

def format_task_info(task_list, task_type):
    """Format task information for display"""
    rows = []
    
    for worker, tasks in task_list.items():
        if not tasks:
            continue
            
        for task in tasks:
            task_id = task.get('id', 'Unknown')
            task_name = task.get('name', 'Unknown')
            task_args = str(task.get('args', []))[:50]
            task_kwargs = str(task.get('kwargs', {}))[:50]
            
            # Get additional info based on task type
            if task_type == 'active':
                time_start = task.get('time_start', 0)
                if time_start:
                    started = datetime.fromtimestamp(time_start)
                    runtime = datetime.now() - started
                    runtime_str = str(runtime).split('.')[0]  # Remove microseconds
                else:
                    runtime_str = 'Unknown'
                
                rows.append([
                    worker,
                    task_id[:8] + '...',
                    task_name,
                    task_args,
                    task_kwargs,
                    runtime_str
                ])
            elif task_type == 'scheduled':
                eta = task.get('eta', 'Unknown')
                priority = task.get('priority', 'Unknown')
                
                rows.append([
                    worker,
                    task_id[:8] + '...',
                    task_name,
                    task_args,
                    task_kwargs,
                    eta,
                    priority
                ])
            elif task_type == 'reserved':
                rows.append([
                    worker,
                    task_id[:8] + '...',
                    task_name,
                    task_args,
                    task_kwargs
                ])
    
    # Define headers based on task type
    if task_type == 'active':
        headers = ['Worker', 'Task ID', 'Name', 'Args', 'Kwargs', 'Runtime']
    elif task_type == 'scheduled':
        headers = ['Worker', 'Task ID', 'Name', 'Args', 'Kwargs', 'ETA', 'Priority']
    elif task_type == 'reserved':
        headers = ['Worker', 'Task ID', 'Name', 'Args', 'Kwargs']
    else:
        headers = []
    
    return tabulate(rows, headers=headers, tablefmt='pretty') if rows else None

def main():
    """Main function to monitor Celery tasks"""
    try:
        import tabulate
    except ImportError:
        print("Please install tabulate: pip install tabulate")
        return
    
    print("Monitoring Celery tasks...")
    print("Press Ctrl+C to exit")
    
    try:
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            
            print(f"Celery Task Monitor - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 80)
            
            tasks = get_active_tasks()
            
            # Display active tasks
            print("\n[Active Tasks]")
            active_table = format_task_info(tasks['active'], 'active')
            if active_table:
                print(active_table)
            else:
                print("No active tasks")
            
            # Display scheduled tasks
            print("\n[Scheduled Tasks]")
            scheduled_table = format_task_info(tasks['scheduled'], 'scheduled')
            if scheduled_table:
                print(scheduled_table)
            else:
                print("No scheduled tasks")
            
            # Display reserved tasks
            print("\n[Reserved Tasks]")
            reserved_table = format_task_info(tasks['reserved'], 'reserved')
            if reserved_table:
                print(reserved_table)
            else:
                print("No reserved tasks")
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\nExiting Celery monitor...")

if __name__ == "__main__":
    main() 