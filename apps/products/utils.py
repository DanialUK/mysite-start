import csv
import json
import xml.etree.ElementTree as ET
import pandas as pd
from django.core.exceptions import ValidationError
from django.utils.text import slugify
import yaml
import requests
from requests.exceptions import RequestException
import time
import logging
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from .models import Product, Category, Attribute, AttributeValue, ProductAttribute

logger = logging.getLogger(__name__)

def export_products_to_csv(products, filename):
    """Экспорт товаров в CSV формат"""
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'id', 'name', 'slug', 'description', 'price', 'stock', 
            'category', 'sku', 'is_active', 'featured'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for product in products:
            writer.writerow({
                'id': product.id,
                'name': product.name,
                'slug': product.slug,
                'description': product.description,
                'price': product.price,
                'stock': product.stock,
                'category': product.category.name,
                'sku': product.sku,
                'is_active': product.is_active,
                'featured': product.featured
            })
    return filename

def export_products_to_json(products, filename):
    """Экспорт товаров в JSON формат"""
    products_data = []
    
    for product in products:
        attributes = []
        for attr in product.product_attributes.all():
            attributes.append({
                'name': attr.attribute_value.attribute.name,
                'value': attr.attribute_value.value
            })
        
        images = []
        for img in product.images.all():
            images.append({
                'url': img.image.url if img.image else '',
                'alt_text': img.alt_text,
                'is_featured': img.is_featured
            })
        
        product_data = {
            'id': product.id,
            'name': product.name,
            'slug': product.slug,
            'description': product.description,
            'price': float(product.price),
            'stock': product.stock,
            'category': {
                'id': product.category.id,
                'name': product.category.name,
                'slug': product.category.slug
            },
            'sku': product.sku,
            'is_active': product.is_active,
            'featured': product.featured,
            'attributes': attributes,
            'images': images
        }
        products_data.append(product_data)
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(products_data, f, ensure_ascii=False, indent=4)
    
    return filename

def export_products_to_xml(products, filename):
    """Экспорт товаров в XML формат"""
    root = ET.Element('products')
    
    for product in products:
        product_elem = ET.SubElement(root, 'product')
        ET.SubElement(product_elem, 'id').text = str(product.id)
        ET.SubElement(product_elem, 'name').text = product.name
        ET.SubElement(product_elem, 'slug').text = product.slug
        ET.SubElement(product_elem, 'description').text = product.description
        ET.SubElement(product_elem, 'price').text = str(product.price)
        ET.SubElement(product_elem, 'stock').text = str(product.stock)
        
        category = ET.SubElement(product_elem, 'category')
        ET.SubElement(category, 'id').text = str(product.category.id)
        ET.SubElement(category, 'name').text = product.category.name
        ET.SubElement(category, 'slug').text = product.category.slug
        
        ET.SubElement(product_elem, 'sku').text = product.sku
        ET.SubElement(product_elem, 'is_active').text = str(product.is_active)
        ET.SubElement(product_elem, 'featured').text = str(product.featured)
        
        # Атрибуты
        attributes_elem = ET.SubElement(product_elem, 'attributes')
        for attr in product.product_attributes.all():
            attr_elem = ET.SubElement(attributes_elem, 'attribute')
            ET.SubElement(attr_elem, 'name').text = attr.attribute_value.attribute.name
            ET.SubElement(attr_elem, 'value').text = attr.attribute_value.value
        
        # Изображения
        images_elem = ET.SubElement(product_elem, 'images')
        for img in product.images.all():
            img_elem = ET.SubElement(images_elem, 'image')
            ET.SubElement(img_elem, 'url').text = img.image.url if img.image else ''
            ET.SubElement(img_elem, 'alt_text').text = img.alt_text
            ET.SubElement(img_elem, 'is_featured').text = str(img.is_featured)
    
    tree = ET.ElementTree(root)
    tree.write(filename, encoding='utf-8', xml_declaration=True)
    
    return filename

def import_products_from_csv(file):
    """Импорт товаров из CSV файла"""
    try:
        df = pd.read_csv(file)
        results = {'created': 0, 'updated': 0, 'errors': []}
        
        for _, row in df.iterrows():
            try:
                # Получаем или создаем категорию
                category_name = row['category']
                category, _ = Category.objects.get_or_create(
                    name=category_name,
                    defaults={'slug': slugify(category_name)}
                )
                
                # Формируем slug если отсутствует
                slug = row.get('slug') or slugify(row['name'])
                
                # Получаем или создаем товар
                product, created = Product.objects.update_or_create(
                    sku=row['sku'],
                    defaults={
                        'name': row['name'],
                        'slug': slug,
                        'description': row['description'],
                        'price': row['price'],
                        'stock': row['stock'],
                        'category': category,
                        'is_active': row.get('is_active', True),
                        'featured': row.get('featured', False)
                    }
                )
                
                if created:
                    results['created'] += 1
                else:
                    results['updated'] += 1
                    
            except Exception as e:
                results['errors'].append(f"Ошибка в строке {_+1}: {str(e)}")
        
        return results
    except Exception as e:
        raise ValidationError(f"Ошибка импорта CSV: {str(e)}")

def import_products_from_json(file):
    """Импорт товаров из JSON файла"""
    try:
        data = json.load(file)
        results = {'created': 0, 'updated': 0, 'errors': []}
        
        for i, product_data in enumerate(data):
            try:
                # Получаем или создаем категорию
                category_name = product_data['category']['name']
                category_slug = product_data['category'].get('slug') or slugify(category_name)
                
                category, _ = Category.objects.get_or_create(
                    name=category_name,
                    defaults={'slug': category_slug}
                )
                
                # Формируем slug если отсутствует
                slug = product_data.get('slug') or slugify(product_data['name'])
                
                # Получаем или создаем товар
                product, created = Product.objects.update_or_create(
                    sku=product_data['sku'],
                    defaults={
                        'name': product_data['name'],
                        'slug': slug,
                        'description': product_data['description'],
                        'price': product_data['price'],
                        'stock': product_data['stock'],
                        'category': category,
                        'is_active': product_data.get('is_active', True),
                        'featured': product_data.get('featured', False)
                    }
                )
                
                # Добавляем атрибуты
                if 'attributes' in product_data:
                    for attr_data in product_data['attributes']:
                        attribute, _ = Attribute.objects.get_or_create(
                            name=attr_data['name'],
                            defaults={'slug': slugify(attr_data['name'])}
                        )
                        
                        attr_value, _ = AttributeValue.objects.get_or_create(
                            attribute=attribute,
                            value=attr_data['value']
                        )
                        
                        ProductAttribute.objects.get_or_create(
                            product=product,
                            attribute_value=attr_value
                        )
                
                if created:
                    results['created'] += 1
                else:
                    results['updated'] += 1
                    
            except Exception as e:
                results['errors'].append(f"Ошибка в записи {i+1}: {str(e)}")
        
        return results
    except Exception as e:
        raise ValidationError(f"Ошибка импорта JSON: {str(e)}")

def import_products_from_xml(file):
    """Импорт товаров из XML файла"""
    try:
        tree = ET.parse(file)
        root = tree.getroot()
        results = {'created': 0, 'updated': 0, 'errors': []}
        
        for i, product_elem in enumerate(root.findall('product')):
            try:
                # Получаем данные из XML
                name = product_elem.find('name').text
                description = product_elem.find('description').text
                price = float(product_elem.find('price').text)
                stock = int(product_elem.find('stock').text)
                sku = product_elem.find('sku').text
                
                slug_elem = product_elem.find('slug')
                slug = slug_elem.text if slug_elem is not None else slugify(name)
                
                is_active_elem = product_elem.find('is_active')
                is_active = is_active_elem.text.lower() == 'true' if is_active_elem is not None else True
                
                featured_elem = product_elem.find('featured')
                featured = featured_elem.text.lower() == 'true' if featured_elem is not None else False
                
                # Категория
                category_elem = product_elem.find('category')
                category_name = category_elem.find('name').text
                
                category_slug_elem = category_elem.find('slug')
                category_slug = category_slug_elem.text if category_slug_elem is not None else slugify(category_name)
                
                category, _ = Category.objects.get_or_create(
                    name=category_name,
                    defaults={'slug': category_slug}
                )
                
                # Создаем или обновляем товар
                product, created = Product.objects.update_or_create(
                    sku=sku,
                    defaults={
                        'name': name,
                        'slug': slug,
                        'description': description,
                        'price': price,
                        'stock': stock,
                        'category': category,
                        'is_active': is_active,
                        'featured': featured
                    }
                )
                
                # Атрибуты
                attributes_elem = product_elem.find('attributes')
                if attributes_elem is not None:
                    for attr_elem in attributes_elem.findall('attribute'):
                        attr_name = attr_elem.find('name').text
                        attr_value = attr_elem.find('value').text
                        
                        attribute, _ = Attribute.objects.get_or_create(
                            name=attr_name,
                            defaults={'slug': slugify(attr_name)}
                        )
                        
                        attr_value_obj, _ = AttributeValue.objects.get_or_create(
                            attribute=attribute,
                            value=attr_value
                        )
                        
                        ProductAttribute.objects.get_or_create(
                            product=product,
                            attribute_value=attr_value_obj
                        )
                
                if created:
                    results['created'] += 1
                else:
                    results['updated'] += 1
                    
            except Exception as e:
                results['errors'].append(f"Ошибка в записи {i+1}: {str(e)}")
        
        return results
    except Exception as e:
        raise ValidationError(f"Ошибка импорта XML: {str(e)}")

def import_products_from_yaml(file):
    """Импорт товаров из YAML файла"""
    try:
        data = yaml.safe_load(file)
        results = {'created': 0, 'updated': 0, 'errors': []}
        
        for i, product_data in enumerate(data['products']):
            try:
                # Получаем или создаем категорию
                category_name = product_data['category']
                category_slug = slugify(category_name)
                
                category, _ = Category.objects.get_or_create(
                    name=category_name,
                    defaults={'slug': category_slug}
                )
                
                # Формируем slug если отсутствует
                slug = product_data.get('slug') or slugify(product_data['name'])
                
                # Получаем или создаем товар
                product, created = Product.objects.update_or_create(
                    sku=product_data['sku'],
                    defaults={
                        'name': product_data['name'],
                        'slug': slug,
                        'description': product_data.get('description', ''),
                        'price': product_data['price'],
                        'stock': product_data.get('stock', 0),
                        'category': category,
                        'is_active': product_data.get('is_active', True),
                        'featured': product_data.get('featured', False)
                    }
                )
                
                # Добавляем атрибуты
                if 'attributes' in product_data:
                    for attr_name, attr_value in product_data['attributes'].items():
                        attribute, _ = Attribute.objects.get_or_create(
                            name=attr_name,
                            defaults={'slug': slugify(attr_name)}
                        )
                        
                        attr_value_obj, _ = AttributeValue.objects.get_or_create(
                            attribute=attribute,
                            value=str(attr_value)
                        )
                        
                        ProductAttribute.objects.get_or_create(
                            product=product,
                            attribute_value=attr_value_obj
                        )
                
                if created:
                    results['created'] += 1
                else:
                    results['updated'] += 1
                    
            except Exception as e:
                results['errors'].append(f"Ошибка в записи {i+1}: {str(e)}")
        
        return results
    except yaml.YAMLError as e:
        raise ValidationError(f"Ошибка парсинга YAML: {str(e)}")
    except Exception as e:
        raise ValidationError(f"Ошибка импорта YAML: {str(e)}")

def import_products_from_api(api_url, api_key=None, method='GET', params=None, headers=None, data=None):
    """
    Импорт товаров через API
    
    Args:
        api_url (str): URL API-эндпоинта
        api_key (str, optional): API ключ для авторизации
        method (str, optional): HTTP метод (GET, POST и т.д.)
        params (dict, optional): Параметры запроса
        headers (dict, optional): HTTP заголовки
        data (dict, optional): Данные для отправки в теле запроса
    """
    try:
        results = {'created': 0, 'updated': 0, 'errors': []}
        
        # Формируем заголовки
        request_headers = headers or {}
        if api_key:
            request_headers['Authorization'] = f'Bearer {api_key}'
        
        # Выполняем запрос
        response = requests.request(
            method=method, 
            url=api_url,
            params=params,
            headers=request_headers,
            json=data,
            timeout=30
        )
        
        response.raise_for_status()  # Проверяем успешность запроса
        
        # Обрабатываем ответ
        products_data = response.json()
        
        # Определяем, является ли ответ списком или объектом с вложенным списком
        if isinstance(products_data, dict) and 'products' in products_data:
            products_list = products_data['products']
        elif isinstance(products_data, dict) and 'items' in products_data:
            products_list = products_data['items']
        elif isinstance(products_data, dict) and 'results' in products_data:
            products_list = products_data['results']
        elif isinstance(products_data, list):
            products_list = products_data
        else:
            raise ValidationError("Неподдерживаемый формат ответа API")
        
        # Обрабатываем каждый товар
        for i, product_data in enumerate(products_list):
            try:
                # Получаем необходимые поля из API-ответа
                name = product_data.get('name') or product_data.get('title')
                if not name:
                    results['errors'].append(f"Запись {i+1}: Отсутствует обязательное поле 'name'")
                    continue
                    
                sku = product_data.get('sku') or product_data.get('id') or product_data.get('code')
                if not sku:
                    results['errors'].append(f"Запись {i+1}: Отсутствует обязательное поле 'sku'")
                    continue
                    
                description = product_data.get('description') or product_data.get('desc') or ''
                
                # Обрабатываем цену, которая может быть в разных форматах и полях
                price = None
                for price_field in ['price', 'price_amount', 'cost', 'amount']:
                    if price_field in product_data:
                        price_value = product_data[price_field]
                        if isinstance(price_value, (int, float)):
                            price = price_value
                            break
                        elif isinstance(price_value, dict) and 'value' in price_value:
                            price = float(price_value['value'])
                            break
                        elif isinstance(price_value, str) and price_value.replace('.', '', 1).isdigit():
                            price = float(price_value)
                            break
                
                if price is None:
                    results['errors'].append(f"Запись {i+1}: Невозможно определить цену")
                    continue
                
                # Получаем или создаем категорию
                category_name = None
                for cat_field in ['category', 'category_name', 'cat', 'group']:
                    if cat_field in product_data:
                        cat_value = product_data[cat_field]
                        if isinstance(cat_value, str):
                            category_name = cat_value
                            break
                        elif isinstance(cat_value, dict) and 'name' in cat_value:
                            category_name = cat_value['name']
                            break
                
                if not category_name:
                    category_name = "Без категории"
                
                category, _ = Category.objects.get_or_create(
                    name=category_name,
                    defaults={'slug': slugify(category_name)}
                )
                
                # Формируем slug если отсутствует
                slug = product_data.get('slug') or slugify(name)
                
                # Определяем количество на складе
                stock = 0
                for stock_field in ['stock', 'quantity', 'inventory', 'available']:
                    if stock_field in product_data:
                        stock_value = product_data[stock_field]
                        if isinstance(stock_value, (int, float)):
                            stock = int(stock_value)
                            break
                        elif isinstance(stock_value, str) and stock_value.isdigit():
                            stock = int(stock_value)
                            break
                
                # Получаем или создаем товар
                product, created = Product.objects.update_or_create(
                    sku=sku,
                    defaults={
                        'name': name,
                        'slug': slug,
                        'description': description,
                        'price': price,
                        'stock': stock,
                        'category': category,
                        'is_active': True,
                        'featured': False
                    }
                )
                
                # Добавляем атрибуты
                if 'attributes' in product_data and isinstance(product_data['attributes'], dict):
                    for attr_name, attr_value in product_data['attributes'].items():
                        attribute, _ = Attribute.objects.get_or_create(
                            name=attr_name,
                            defaults={'slug': slugify(attr_name)}
                        )
                        
                        attr_value_obj, _ = AttributeValue.objects.get_or_create(
                            attribute=attribute,
                            value=str(attr_value)
                        )
                        
                        ProductAttribute.objects.get_or_create(
                            product=product,
                            attribute_value=attr_value_obj
                        )
                
                if created:
                    results['created'] += 1
                else:
                    results['updated'] += 1
                    
            except Exception as e:
                results['errors'].append(f"Ошибка в записи {i+1}: {str(e)}")
        
        return results
    except RequestException as e:
        raise ValidationError(f"Ошибка HTTP запроса: {str(e)}")
    except json.JSONDecodeError as e:
        raise ValidationError(f"Ошибка декодирования JSON: {str(e)}")
    except Exception as e:
        raise ValidationError(f"Ошибка импорта через API: {str(e)}")

def import_products_via_scraping(url, config):
    """
    Импорт товаров через веб-скрапинг с использованием Selenium
    
    Args:
        url (str): URL-адрес страницы, с которой нужно собрать данные
        config (dict): Конфигурация для скрапинга, содержащая селекторы элементов
    """
    try:
        results = {'created': 0, 'updated': 0, 'errors': []}
        
        # Настройка Chrome в headless режиме
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Настройка и запуск драйвера
        try:
            driver_path = ChromeDriverManager().install()
            service = Service(driver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            logger.error(f"Ошибка инициализации Chrome драйвера: {str(e)}")
            raise ValidationError(f"Ошибка запуска браузера: {str(e)}")
        
        try:
            # Загрузка страницы
            driver.get(url)
            
            # Ожидание загрузки страницы
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Проверяем необходимость пагинации
            page_count = 1
            if config.get('pagination'):
                try:
                    # Ожидаем загрузки элемента пагинации
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, config['pagination']['selector']))
                    )
                    
                    # Определяем количество страниц для обработки
                    if config['pagination']['type'] == 'last_page_number':
                        # Получаем номер последней страницы
                        pagination_element = driver.find_element(By.CSS_SELECTOR, config['pagination']['selector'])
                        page_count = int(pagination_element.text.strip())
                    elif config['pagination']['type'] == 'next_button':
                        # Будем переходить по кнопке "Следующая" пока она существует
                        page_count = 999  # Устанавливаем высокое значение, чтобы использовать цикл
                except (TimeoutException, NoSuchElementException):
                    logger.warning("Элемент пагинации не найден, обрабатываем только первую страницу")
            
            # Обрабатываем каждую страницу
            for page in range(1, page_count + 1):
                if page > 1:
                    # Переходим на следующую страницу
                    if config['pagination']['type'] == 'last_page_number':
                        # Строим URL следующей страницы
                        next_page_url = config['pagination']['url_template'].format(page=page)
                        driver.get(next_page_url)
                    elif config['pagination']['type'] == 'next_button':
                        try:
                            # Пытаемся найти и нажать кнопку "Следующая"
                            next_button = WebDriverWait(driver, 5).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, config['pagination']['next_button_selector']))
                            )
                            next_button.click()
                        except (TimeoutException, NoSuchElementException):
                            logger.info(f"Кнопка следующей страницы не найдена. Обработано страниц: {page-1}")
                            break
                    
                    # Ожидание загрузки страницы
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    time.sleep(2)  # Дополнительная задержка для надежности
                
                # Находим все элементы товаров на странице
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, config['product_selector']))
                    )
                    product_elements = driver.find_elements(By.CSS_SELECTOR, config['product_selector'])
                except (TimeoutException, NoSuchElementException) as e:
                    logger.error(f"Элементы товаров не найдены на странице {page}: {str(e)}")
                    results['errors'].append(f"Ошибка на странице {page}: Элементы товаров не найдены")
                    continue
                
                logger.info(f"Найдено {len(product_elements)} товаров на странице {page}")
                
                # Обрабатываем каждый элемент товара
                for i, product_element in enumerate(product_elements):
                    try:
                        # Извлекаем данные о товаре
                        product_data = {}
                        
                        # Название товара
                        try:
                            name_element = product_element.find_element(By.CSS_SELECTOR, config['name_selector'])
                            product_data['name'] = name_element.text.strip()
                        except NoSuchElementException:
                            results['errors'].append(f"Товар {i+1} на странице {page}: Не найдено название товара")
                            continue
                        
                        # Цена товара
                        try:
                            price_element = product_element.find_element(By.CSS_SELECTOR, config['price_selector'])
                            price_text = price_element.text.strip()
                            # Удаляем символы валюты и разделители тысяч
                            price_numeric = ''.join(c for c in price_text if c.isdigit() or c == '.')
                            product_data['price'] = float(price_numeric)
                        except (NoSuchElementException, ValueError):
                            results['errors'].append(f"Товар {i+1} на странице {page}: Некорректная цена")
                            continue
                        
                        # Описание товара (если есть)
                        if 'description_selector' in config:
                            try:
                                desc_element = product_element.find_element(By.CSS_SELECTOR, config['description_selector'])
                                product_data['description'] = desc_element.text.strip()
                            except NoSuchElementException:
                                product_data['description'] = ""
                        else:
                            product_data['description'] = ""
                        
                        # SKU товара (если есть)
                        if 'sku_selector' in config:
                            try:
                                sku_element = product_element.find_element(By.CSS_SELECTOR, config['sku_selector'])
                                product_data['sku'] = sku_element.text.strip()
                            except NoSuchElementException:
                                # Если SKU не найден, используем хеш от имени и цены
                                product_data['sku'] = f"SCRAPE-{hash(product_data['name'] + str(product_data['price']))}"
                        else:
                            # Если SKU селектор не определен, создаем уникальный SKU
                            product_data['sku'] = f"SCRAPE-{hash(product_data['name'] + str(product_data['price']))}"
                        
                        # Категория товара (если есть)
                        if 'category_selector' in config:
                            try:
                                category_element = product_element.find_element(By.CSS_SELECTOR, config['category_selector'])
                                category_name = category_element.text.strip()
                            except NoSuchElementException:
                                category_name = config.get('default_category', 'Скрапинг')
                        else:
                            category_name = config.get('default_category', 'Скрапинг')
                        
                        # Создаем или получаем категорию
                        category, _ = Category.objects.get_or_create(
                            name=category_name,
                            defaults={'slug': slugify(category_name)}
                        )
                        
                        # Получаем или создаем товар
                        product, created = Product.objects.update_or_create(
                            sku=product_data['sku'],
                            defaults={
                                'name': product_data['name'],
                                'slug': slugify(product_data['name']),
                                'description': product_data['description'],
                                'price': product_data['price'],
                                'stock': 0,  # По умолчанию 0
                                'category': category,
                                'is_active': True,
                                'featured': False
                            }
                        )
                        
                        # Если необходимо извлечь детальную информацию, открываем страницу товара
                        if config.get('details_page'):
                            try:
                                # Находим ссылку на страницу товара
                                link_element = product_element.find_element(By.CSS_SELECTOR, config['details_page']['link_selector'])
                                product_url = link_element.get_attribute('href')
                                
                                # Сохраняем текущее окно
                                original_window = driver.current_window_handle
                                
                                # Открываем новую вкладку для деталей товара
                                driver.execute_script("window.open('');")
                                driver.switch_to.window(driver.window_handles[1])
                                driver.get(product_url)
                                
                                # Ожидание загрузки страницы
                                WebDriverWait(driver, 10).until(
                                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                                )
                                time.sleep(1)  # Дополнительная задержка
                                
                                # Извлекаем более детальное описание
                                if 'detailed_description_selector' in config['details_page']:
                                    try:
                                        detailed_desc_element = driver.find_element(
                                            By.CSS_SELECTOR, config['details_page']['detailed_description_selector']
                                        )
                                        detailed_description = detailed_desc_element.text.strip()
                                        
                                        # Обновляем описание товара
                                        product.description = detailed_description
                                        product.save()
                                    except NoSuchElementException:
                                        logger.warning(f"Детальное описание не найдено для товара {product_data['name']}")
                                
                                # Извлекаем атрибуты товара
                                if 'attributes_selector' in config['details_page']:
                                    try:
                                        attributes_elements = driver.find_elements(
                                            By.CSS_SELECTOR, config['details_page']['attributes_selector']
                                        )
                                        
                                        for attr_element in attributes_elements:
                                            try:
                                                # Извлекаем имя и значение атрибута
                                                attr_name_element = attr_element.find_element(
                                                    By.CSS_SELECTOR, config['details_page']['attribute_name_selector']
                                                )
                                                attr_value_element = attr_element.find_element(
                                                    By.CSS_SELECTOR, config['details_page']['attribute_value_selector']
                                                )
                                                
                                                attr_name = attr_name_element.text.strip()
                                                attr_value = attr_value_element.text.strip()
                                                
                                                if attr_name and attr_value:
                                                    # Создаем или получаем атрибут
                                                    attribute, _ = Attribute.objects.get_or_create(
                                                        name=attr_name,
                                                        defaults={'slug': slugify(attr_name)}
                                                    )
                                                    
                                                    # Создаем или получаем значение атрибута
                                                    attr_value_obj, _ = AttributeValue.objects.get_or_create(
                                                        attribute=attribute,
                                                        value=attr_value
                                                    )
                                                    
                                                    # Связываем атрибут с товаром
                                                    ProductAttribute.objects.get_or_create(
                                                        product=product,
                                                        attribute_value=attr_value_obj
                                                    )
                                            except NoSuchElementException:
                                                continue
                                    except NoSuchElementException:
                                        logger.warning(f"Атрибуты не найдены для товара {product_data['name']}")
                                
                                # Закрываем вкладку и возвращаемся к списку товаров
                                driver.close()
                                driver.switch_to.window(original_window)
                            except Exception as e:
                                logger.error(f"Ошибка при обработке детальной страницы товара: {str(e)}")
                                results['errors'].append(f"Ошибка при обработке детальной страницы для товара {product_data['name']}")
                                
                                # Закрываем лишние вкладки и возвращаемся к основной, если произошла ошибка
                                if len(driver.window_handles) > 1:
                                    driver.close()
                                    driver.switch_to.window(driver.window_handles[0])
                        
                        if created:
                            results['created'] += 1
                        else:
                            results['updated'] += 1
                    except Exception as e:
                        logger.error(f"Ошибка при обработке товара на странице {page}: {str(e)}")
                        results['errors'].append(f"Ошибка в товаре {i+1} на странице {page}: {str(e)}")
                
                # Задержка между страницами для избежания блокировки
                time.sleep(config.get('delay_between_pages', 2))
        
        finally:
            # Закрываем браузер
            driver.quit()
        
        return results
    except Exception as e:
        logger.error(f"Ошибка импорта через скрапинг: {str(e)}")
        raise ValidationError(f"Ошибка импорта через скрапинг: {str(e)}") 