from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden

# Временно уберем login_required для тестирования
def manager_dashboard(request):
    """Manager dashboard view."""
    # Для тестирования не проверяем роль
    return render(request, 'roles/manager.html')

def seller_dashboard(request):
    """Seller dashboard view."""
    # Для тестирования не проверяем роль
    return render(request, 'roles/seller.html')

def user_dashboard(request):
    """User dashboard view."""
    # Для тестирования не проверяем роль
    return render(request, 'roles/user.html') 