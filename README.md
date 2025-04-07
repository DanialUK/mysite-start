# Marketplace Platform

A Django-based e-commerce platform with:
- Product catalog with categories
- User roles (admin, manager, seller, user)
- Product import/export functionality
- Review system
- Modern UI with TailwindCSS and Bootstrap

## Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run migrations: `python manage.py migrate`
4. Create a superuser: `python manage.py createsuperuser`
5. Start the development server: `python manage.py runserver`

## Features

- Responsive design
- Role-based access control
- Product management
- Async processing of large data operations

## Prerequisites

- Python 3.8+
- PostgreSQL (optional, SQLite used by default)
- Redis (for Celery)
- Node.js and npm (for frontend)

## Project Structure

```
marketplace/
├── apps/
│   ├── core/           # Core functionality
│   ├── users/          # User management
│   ├── roles/          # Role management
│   ├── products/       # Product management
│   └── seo/            # SEO management
├── config/             # Project configuration
├── static/             # Static files
├── templates/          # HTML templates
└── manage.py           # Django management script
```

## Development

- Run tests: `python manage.py test`
- Check code style: `flake8`
- Generate migrations: `python manage.py makemigrations`
- Apply migrations: `python manage.py migrate`

## Deployment

1. Set up production environment variables
2. Configure web server (Nginx/Apache)
3. Set up SSL certificates
4. Configure email service
5. Set up monitoring

## Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create pull request

## License

MIT License 