from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('products/', views.product_list, name='products_list'),  # Дублируем для совместимости
    path('categories/', views.category_list, name='category_list'),
    path('category/<slug:category_slug>/', views.product_list, name='product_list_by_category'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('product/<int:product_id>/review/', views.add_review, name='add_review'),
    path('product/<int:product_id>/quick-view/', views.quick_view, name='quick_view'),
    
    # Импорт/экспорт
    path('import/', views.import_products, name='import_products'),
    path('import/api/', views.import_api, name='import_api'),
    path('import/scraping/', views.import_scraping, name='import_scraping'),
    path('export/', views.export_products, name='export_products'),
] 