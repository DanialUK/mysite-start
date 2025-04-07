from django import forms
from .models import Product, Category, Attribute, AttributeValue

class ProductImportForm(forms.Form):
    """Форма для импорта товаров из файла"""
    FILE_FORMATS = (
        ('csv', 'CSV'),
        ('json', 'JSON'),
        ('xml', 'XML'),
        ('yaml', 'YAML'),
    )
    
    file_format = forms.ChoiceField(
        choices=FILE_FORMATS,
        label='Формат файла',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    file = forms.FileField(
        label='Файл',
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )
    
    def clean_file(self):
        file = self.cleaned_data['file']
        file_format = self.cleaned_data['file_format']
        
        # Проверка соответствия формата файла
        if file_format == 'csv' and not file.name.endswith('.csv'):
            raise forms.ValidationError('Файл должен иметь расширение .csv')
        elif file_format == 'json' and not file.name.endswith('.json'):
            raise forms.ValidationError('Файл должен иметь расширение .json')
        elif file_format == 'xml' and not file.name.endswith('.xml'):
            raise forms.ValidationError('Файл должен иметь расширение .xml')
        elif file_format == 'yaml' and not (file.name.endswith('.yaml') or file.name.endswith('.yml')):
            raise forms.ValidationError('Файл должен иметь расширение .yaml или .yml')
            
        return file

class ProductExportForm(forms.Form):
    """Форма для экспорта товаров в файл"""
    FILE_FORMATS = (
        ('csv', 'CSV'),
        ('json', 'JSON'),
        ('xml', 'XML'),
    )
    
    file_format = forms.ChoiceField(
        choices=FILE_FORMATS,
        label='Формат файла',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        label='Категория',
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.filter(is_active=True)
        # Добавляем пустое значение для выбора всех категорий
        self.fields['category'].empty_label = "Все категории"

class ProductAPIImportForm(forms.Form):
    """Форма для импорта товаров из API"""
    api_url = forms.URLField(
        label='URL API',
        widget=forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://api.example.com/products'})
    )
    
    api_key = forms.CharField(
        label='API ключ',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Оставьте пустым, если API не требует авторизации'})
    )
    
    METHOD_CHOICES = (
        ('GET', 'GET'),
        ('POST', 'POST'),
    )
    method = forms.ChoiceField(
        label='HTTP метод',
        choices=METHOD_CHOICES,
        initial='GET',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    params = forms.CharField(
        label='Дополнительные параметры (JSON)',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 3, 
            'placeholder': '{"limit": 100, "offset": 0}'
        })
    )
    
    headers = forms.CharField(
        label='HTTP заголовки (JSON)',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 3, 
            'placeholder': '{"Content-Type": "application/json", "Accept": "application/json"}'
        })
    )
    
    data = forms.CharField(
        label='Данные запроса (JSON)',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 3, 
            'placeholder': '{"query": "product", "fields": ["id", "name", "price"]}'
        })
    )
    
    def clean_params(self):
        params = self.cleaned_data.get('params')
        if not params:
            return None
        
        import json
        try:
            return json.loads(params)
        except json.JSONDecodeError:
            raise forms.ValidationError('Параметры должны быть в формате JSON')
    
    def clean_headers(self):
        headers = self.cleaned_data.get('headers')
        if not headers:
            return None
        
        import json
        try:
            return json.loads(headers)
        except json.JSONDecodeError:
            raise forms.ValidationError('Заголовки должны быть в формате JSON')
    
    def clean_data(self):
        data = self.cleaned_data.get('data')
        if not data:
            return None
        
        import json
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            raise forms.ValidationError('Данные должны быть в формате JSON')

class ProductScrapingForm(forms.Form):
    """Форма для импорта товаров через веб-скрапинг"""
    url = forms.URLField(
        label='URL страницы',
        widget=forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://example.com/products'})
    )
    
    product_selector = forms.CharField(
        label='CSS селектор товара',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '.product-item'})
    )
    
    name_selector = forms.CharField(
        label='CSS селектор названия',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '.product-title'})
    )
    
    price_selector = forms.CharField(
        label='CSS селектор цены',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '.product-price'})
    )
    
    description_selector = forms.CharField(
        label='CSS селектор описания',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '.product-description'})
    )
    
    category_selector = forms.CharField(
        label='CSS селектор категории',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '.product-category'})
    )
    
    default_category = forms.CharField(
        label='Категория по умолчанию',
        initial='Импорт',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    use_pagination = forms.BooleanField(
        label='Использовать пагинацию',
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    pagination_type = forms.ChoiceField(
        label='Тип пагинации',
        choices=(
            ('next_button', 'Кнопка "Следующая"'),
            ('last_page_number', 'Номер последней страницы'),
        ),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    pagination_selector = forms.CharField(
        label='CSS селектор пагинации',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '.pagination .last-page'})
    )
    
    next_button_selector = forms.CharField(
        label='CSS селектор кнопки "Следующая"',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '.pagination .next'})
    )
    
    url_template = forms.CharField(
        label='Шаблон URL для страниц',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'https://example.com/products?page={page}'
        })
    )
    
    get_details = forms.BooleanField(
        label='Получать детальную информацию о товаре',
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    link_selector = forms.CharField(
        label='CSS селектор ссылки на товар',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '.product-link'})
    )
    
    detailed_description_selector = forms.CharField(
        label='CSS селектор детального описания',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '.product-full-description'})
    )
    
    attributes_selector = forms.CharField(
        label='CSS селектор блока атрибутов',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '.product-attributes li'})
    )
    
    attribute_name_selector = forms.CharField(
        label='CSS селектор имени атрибута',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '.attr-name'})
    )
    
    attribute_value_selector = forms.CharField(
        label='CSS селектор значения атрибута',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '.attr-value'})
    )
    
    delay_between_pages = forms.IntegerField(
        label='Задержка между страницами (сек)',
        min_value=1,
        max_value=10,
        initial=2,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        use_pagination = cleaned_data.get('use_pagination')
        
        if use_pagination:
            pagination_type = cleaned_data.get('pagination_type')
            pagination_selector = cleaned_data.get('pagination_selector')
            
            if not pagination_type:
                self.add_error('pagination_type', 'Выберите тип пагинации')
            
            if not pagination_selector:
                self.add_error('pagination_selector', 'Укажите селектор пагинации')
            
            if pagination_type == 'next_button' and not cleaned_data.get('next_button_selector'):
                self.add_error('next_button_selector', 'Укажите селектор кнопки "Следующая"')
            
            if pagination_type == 'last_page_number' and not cleaned_data.get('url_template'):
                self.add_error('url_template', 'Укажите шаблон URL для страниц')
        
        get_details = cleaned_data.get('get_details')
        if get_details and not cleaned_data.get('link_selector'):
            self.add_error('link_selector', 'Укажите селектор ссылки на товар')
        
        return cleaned_data
    
    def get_config(self):
        """Создает конфигурацию для скрапинга на основе данных формы"""
        config = {
            'product_selector': self.cleaned_data['product_selector'],
            'name_selector': self.cleaned_data['name_selector'],
            'price_selector': self.cleaned_data['price_selector'],
            'default_category': self.cleaned_data['default_category'],
            'delay_between_pages': self.cleaned_data['delay_between_pages'],
        }
        
        # Добавляем опциональные селекторы
        if self.cleaned_data.get('description_selector'):
            config['description_selector'] = self.cleaned_data['description_selector']
        
        if self.cleaned_data.get('category_selector'):
            config['category_selector'] = self.cleaned_data['category_selector']
        
        # Настройки пагинации
        if self.cleaned_data.get('use_pagination'):
            config['pagination'] = {
                'type': self.cleaned_data['pagination_type'],
                'selector': self.cleaned_data['pagination_selector'],
            }
            
            if self.cleaned_data['pagination_type'] == 'next_button':
                config['pagination']['next_button_selector'] = self.cleaned_data['next_button_selector']
            elif self.cleaned_data['pagination_type'] == 'last_page_number':
                config['pagination']['url_template'] = self.cleaned_data['url_template']
        
        # Настройки детальной страницы
        if self.cleaned_data.get('get_details'):
            config['details_page'] = {
                'link_selector': self.cleaned_data['link_selector'],
            }
            
            if self.cleaned_data.get('detailed_description_selector'):
                config['details_page']['detailed_description_selector'] = self.cleaned_data['detailed_description_selector']
            
            if self.cleaned_data.get('attributes_selector'):
                config['details_page']['attributes_selector'] = self.cleaned_data['attributes_selector']
                
                if self.cleaned_data.get('attribute_name_selector') and self.cleaned_data.get('attribute_value_selector'):
                    config['details_page']['attribute_name_selector'] = self.cleaned_data['attribute_name_selector']
                    config['details_page']['attribute_value_selector'] = self.cleaned_data['attribute_value_selector']
        
        return config 