from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
    # Главная и административные разделы
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('apps.products.urls')),  # Главная страница через URLs приложения products
    
    # Приложение core
    path('core/', include('apps.core.urls', namespace='core')),
    
    # API endpoints
    path('api/roles/', include('apps.roles.urls', namespace='api_roles')),
    path('api/users/', include('apps.users.urls', namespace='api_users')),
    path('api/products/', include('apps.products.urls', namespace='api_products')),
    path('api/seo/', include('apps.seo.urls', namespace='api_seo')),
    
    # Apps frontend routes (кроме products, которое уже включено выше)
    path('users/', include('apps.users.urls', namespace='users')),
    path('roles/', include('apps.roles.urls', namespace='roles')),
    path('seo/', include('apps.seo.urls', namespace='seo')),
    
    # Role-specific dashboards
    path('seller/', lambda request: redirect('roles:seller_dashboard'), name='seller_home'),
    path('manager/', lambda request: redirect('roles:manager_dashboard'), name='manager_home'),
    path('user/', lambda request: redirect('roles:user_dashboard'), name='user_home'),
]

# Добавляем URLs для работы с статическими и медиа-файлами в режиме разработки
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Debug toolbar (только в режиме отладки)
    try:
        import debug_toolbar
        urlpatterns.append(path('__debug__/', include(debug_toolbar.urls)))
    except ImportError:
        pass 