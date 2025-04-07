from django.urls import path
from . import views

app_name = 'roles'

urlpatterns = [
    path('manager/', views.manager_dashboard, name='manager_dashboard'),
    path('seller/', views.seller_dashboard, name='seller_dashboard'),
    path('user/', views.user_dashboard, name='user_dashboard'),
] 