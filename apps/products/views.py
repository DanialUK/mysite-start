from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q, Avg
from django.core.paginator import Paginator
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, FileResponse
from django.conf import settings
from django.utils.text import slugify
from django.utils.translation import gettext as _
import os
import tempfile
import json
from datetime import datetime

from .models import Category, Product, AttributeValue, Review
from .forms import (
    ProductImportForm, ProductExportForm, 
    ProductAPIImportForm, ProductScrapingForm
)
from .utils import (
    export_products_to_csv, export_products_to_json, export_products_to_xml,
    import_products_from_csv, import_products_from_json, import_products_from_xml,
    import_products_from_yaml, import_products_from_api, import_products_via_scraping
)
from .tasks import process_product_import, process_product_export

def product_list(request, category_slug=None):
    """
    Отображение списка продуктов с возможностью фильтрации по категории
    """
    category = None
    categories = Category.objects.filter(is_active=True)
    products = Product.objects.filter(is_active=True)
    
    # Фильтрация по категории
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug, is_active=True)
        products = products.filter(category=category)
    
    # Поиск
    search_query = request.GET.get('q')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    # Фильтрация по атрибутам
    attribute_filters = {}
    for key, value in request.GET.items():
        if key.startswith('attr_') and value:
            attr_id = key.replace('attr_', '')
            try:
                attribute_filters[int(attr_id)] = value
            except ValueError:
                pass
    
    if attribute_filters:
        attr_queries = Q()
        for attr_id, value in attribute_filters.items():
            attr_queries |= Q(attributes__attribute__id=attr_id, attributes__value=value)
        products = products.filter(attr_queries).distinct()
    
    # Сортировка
    sort_by = request.GET.get('sort')
    if sort_by == 'price-low':
        products = products.order_by('price')
    elif sort_by == 'price-high':
        products = products.order_by('-price')
    elif sort_by == 'name':
        products = products.order_by('name')
    elif sort_by == 'rating':
        products = products.annotate(avg_rating=Avg('reviews__rating')).order_by('-avg_rating')
    else:
        products = products.order_by('-created_at')
    
    # Пагинация
    paginator = Paginator(products, 12)  # 12 продуктов на страницу
    page_number = request.GET.get('page')
    products_page = paginator.get_page(page_number)
    
    # Доступные атрибуты для фильтрации
    attribute_values = AttributeValue.objects.filter(
        products__in=products
    ).select_related('attribute').distinct()
    
    # Группируем значения атрибутов по атрибутам
    attributes = {}
    for av in attribute_values:
        if av.attribute.id not in attributes:
            attributes[av.attribute.id] = {
                'name': av.attribute.name,
                'values': []
            }
        if av.value not in attributes[av.attribute.id]['values']:
            attributes[av.attribute.id]['values'].append(av.value)
    
    context = {
        'categories': categories,
        'category': category,
        'products': products_page,
        'attributes': attributes,
        'selected_attributes': attribute_filters,
        'search_query': search_query,
        'sort_by': sort_by,
    }
    return render(request, 'products/product_list.html', context)

def product_detail(request, slug):
    """
    Отображение детальной информации о продукте
    """
    product = get_object_or_404(Product, slug=slug, is_active=True)
    
    # Получаем все отзывы для продукта
    reviews = product.reviews.filter(is_approved=True).select_related('user')
    
    # Подсчитываем среднюю оценку
    avg_rating = product.get_average_rating()
    
    # Получаем связанные продукты из той же категории
    related_products = Product.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(id=product.id)[:4]
    
    context = {
        'product': product,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'related_products': related_products,
    }
    return render(request, 'products/product_detail.html', context)

@login_required
def add_review(request, product_id):
    """
    Добавление отзыва к продукту
    """
    product = get_object_or_404(Product, id=product_id, is_active=True)
    
    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        
        if not rating or not comment:
            messages.error(request, _('Пожалуйста, заполните все поля'))
            return redirect('products:product_detail', slug=product.slug)
        
        # Проверяем, оставлял ли пользователь уже отзыв
        existing_review = Review.objects.filter(product=product, user=request.user).first()
        
        if existing_review:
            existing_review.rating = rating
            existing_review.comment = comment
            existing_review.save()
            messages.success(request, _('Ваш отзыв был обновлен и будет опубликован после модерации'))
        else:
            Review.objects.create(
                product=product,
                user=request.user,
                rating=rating,
                comment=comment,
                is_approved=False
            )
            messages.success(request, _('Спасибо за ваш отзыв! Он будет опубликован после модерации'))
    
    return redirect('products:product_detail', slug=product.slug)

def category_list(request):
    """
    Отображение списка категорий
    """
    categories = Category.objects.filter(parent=None, is_active=True)
    context = {
        'categories': categories
    }
    return render(request, 'products/category_list.html', context)

def quick_view(request, product_id):
    """
    Быстрый просмотр продукта через AJAX
    """
    product = get_object_or_404(Product, id=product_id, is_active=True)
    
    data = {
        'id': product.id,
        'name': product.name,
        'price': float(product.price),
        'description': product.description,
        'avg_rating': product.get_average_rating(),
        'review_count': product.get_review_count(),
        'in_stock': product.stock > 0,
        'stock': product.stock,
        'images': [
            {
                'url': img.image.url,
                'alt': img.alt_text
            } for img in product.images.all()
        ]
    }
    
    return JsonResponse(data)

# ----- Функционал импорта/экспорта -----

@login_required
@permission_required('products.add_product')
def import_products(request):
    """
    Импорт товаров из файла
    """
    if request.method == 'POST':
        form = ProductImportForm(request.POST, request.FILES)
        if form.is_valid():
            file_format = form.cleaned_data['file_format']
            file = request.FILES['file']
            
            # Определяем, использовать ли асинхронную обработку
            file_size = file.size
            is_large_file = file_size > 1024 * 1024  # Более 1MB
            
            if is_large_file and hasattr(request.user, 'email') and request.user.email:
                # Для больших файлов используем асинхронную обработку
                try:
                    # Сохраняем файл во временную директорию
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_format}') as temp_file:
                        for chunk in file.chunks():
                            temp_file.write(chunk)
                        temp_path = temp_file.name
                    
                    # Запускаем асинхронную задачу
                    process_product_import.delay(temp_path, file_format, request.user.id)
                    
                    messages.success(
                        request, 
                        _(f"Файл принят в обработку ({file_size/1024:.1f} КБ). "
                          f"Результаты будут отправлены на ваш email: {request.user.email}")
                    )
                    return redirect('products:product_list')
                except Exception as e:
                    messages.error(request, f"Ошибка при загрузке файла: {str(e)}")
            else:
                # Для небольших файлов используем синхронную обработку
                try:
                    if file_format == 'csv':
                        results = import_products_from_csv(file)
                    elif file_format == 'json':
                        results = import_products_from_json(file)
                    elif file_format == 'xml':
                        results = import_products_from_xml(file)
                    elif file_format == 'yaml':
                        results = import_products_from_yaml(file)
                    
                    messages.success(
                        request, 
                        f"Импорт завершен. Создано: {results['created']}, обновлено: {results['updated']}"
                    )
                    
                    if results['errors']:
                        for error in results['errors'][:5]:  # Показываем только первые 5 ошибок
                            messages.warning(request, error)
                        
                        if len(results['errors']) > 5:
                            messages.warning(
                                request, 
                                f"И еще {len(results['errors']) - 5} ошибок. Проверьте логи для деталей."
                            )
                    
                    return redirect('products:product_list')
                
                except Exception as e:
                    messages.error(request, f"Ошибка при импорте: {str(e)}")
    else:
        form = ProductImportForm()
    
    return render(request, 'products/import.html', {'form': form})

@login_required
@permission_required('products.add_product')
def import_api(request):
    """
    Импорт товаров через API
    """
    if request.method == 'POST':
        form = ProductAPIImportForm(request.POST)
        if form.is_valid():
            try:
                api_url = form.cleaned_data['api_url']
                api_key = form.cleaned_data['api_key']
                method = form.cleaned_data['method']
                params = form.cleaned_data['params']
                headers = form.cleaned_data['headers']
                data = form.cleaned_data['data']
                
                # Запускаем импорт через API
                results = import_products_from_api(
                    api_url=api_url,
                    api_key=api_key,
                    method=method,
                    params=params,
                    headers=headers,
                    data=data
                )
                
                messages.success(
                    request, 
                    f"Импорт через API завершен. Создано: {results['created']}, обновлено: {results['updated']}"
                )
                
                if results['errors']:
                    for error in results['errors'][:5]:  # Показываем только первые 5 ошибок
                        messages.warning(request, error)
                    
                    if len(results['errors']) > 5:
                        messages.warning(
                            request, 
                            f"И еще {len(results['errors']) - 5} ошибок. Проверьте логи для деталей."
                        )
                
                return redirect('products:product_list')
                
            except Exception as e:
                messages.error(request, f"Ошибка при импорте через API: {str(e)}")
    else:
        form = ProductAPIImportForm()
    
    return render(request, 'products/import_api.html', {'form': form})

@login_required
@permission_required('products.add_product')
def import_scraping(request):
    """
    Импорт товаров через веб-скрапинг
    """
    if request.method == 'POST':
        form = ProductScrapingForm(request.POST)
        if form.is_valid():
            try:
                url = form.cleaned_data['url']
                config = form.get_config()
                
                # Уведомляем пользователя, что процесс запущен
                messages.info(request, _(
                    "Начат процесс скрапинга данных. "
                    "Это может занять некоторое время, особенно при использовании пагинации."
                ))
                
                # Запускаем скрапинг
                results = import_products_via_scraping(url, config)
                
                messages.success(
                    request, 
                    f"Импорт через скрапинг завершен. Создано: {results['created']}, обновлено: {results['updated']}"
                )
                
                if results['errors']:
                    for error in results['errors'][:5]:  # Показываем только первые 5 ошибок
                        messages.warning(request, error)
                    
                    if len(results['errors']) > 5:
                        messages.warning(
                            request, 
                            f"И еще {len(results['errors']) - 5} ошибок. Проверьте логи для деталей."
                        )
                
                return redirect('products:product_list')
                
            except Exception as e:
                messages.error(request, f"Ошибка при скрапинге: {str(e)}")
    else:
        form = ProductScrapingForm()
    
    return render(request, 'products/import_scraping.html', {'form': form})

@login_required
@permission_required('products.view_product')
def export_products(request):
    """
    Экспорт товаров в файл
    """
    if request.method == 'POST':
        form = ProductExportForm(request.POST)
        if form.is_valid():
            file_format = form.cleaned_data['file_format']
            category = form.cleaned_data['category']
            
            # Определяем id категории для задачи
            category_id = category.id if category else None
            
            # Фильтруем товары по категории, если выбрана
            products = Product.objects.all()
            if category:
                products = products.filter(category=category)
            
            # Определяем, использовать ли асинхронную обработку
            products_count = products.count()
            is_large_export = products_count > 100  # Более 100 товаров
            
            if is_large_export and hasattr(request.user, 'email') and request.user.email:
                # Для большого количества товаров используем асинхронную обработку
                try:
                    # Запускаем асинхронную задачу
                    process_product_export.delay(file_format, category_id, request.user.id)
                    
                    messages.success(
                        request, 
                        _(f"Экспорт {products_count} товаров запущен. "
                          f"Ссылка для скачивания будет отправлена на ваш email: {request.user.email}")
                    )
                    return redirect('products:product_list')
                except Exception as e:
                    messages.error(request, f"Ошибка при запуске экспорта: {str(e)}")
            else:
                # Для небольшого количества товаров используем синхронную обработку
                try:
                    # Создаем временный файл
                    now = datetime.now().strftime('%Y%m%d_%H%M%S')
                    
                    if file_format == 'csv':
                        filename = f'products_export_{now}.csv'
                        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_file:
                            filepath = export_products_to_csv(products, temp_file.name)
                            response = FileResponse(
                                open(filepath, 'rb'),
                                content_type='text/csv'
                            )
                    
                    elif file_format == 'json':
                        filename = f'products_export_{now}.json'
                        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as temp_file:
                            filepath = export_products_to_json(products, temp_file.name)
                            response = FileResponse(
                                open(filepath, 'rb'),
                                content_type='application/json'
                            )
                    
                    elif file_format == 'xml':
                        filename = f'products_export_{now}.xml'
                        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as temp_file:
                            filepath = export_products_to_xml(products, temp_file.name)
                            response = FileResponse(
                                open(filepath, 'rb'),
                                content_type='application/xml'
                            )
                    
                    response['Content-Disposition'] = f'attachment; filename="{filename}"'
                    
                    # Отложенное удаление временного файла
                    def del_file():
                        try:
                            os.unlink(filepath)
                        except:
                            pass
                    
                    import threading
                    threading.Timer(60, del_file).start()  # Удаляем через 60 секунд
                    
                    return response
                except Exception as e:
                    messages.error(request, f"Ошибка при экспорте: {str(e)}")
    else:
        form = ProductExportForm()
    
    return render(request, 'products/export.html', {'form': form}) 