# boilerplate

Modern Django + Tailwind CSS boilerplate

## Quick Start

1. Activate virtual environment:
   ```bash
   source .venv/bin/activate
   ```

2. Start CSS watcher (in one terminal):
   ```bash
   npm run watch:css
   ```

3. Start Django server (in another terminal):
   ```bash
   uv run python manage.py runserver
   ```

## Features

- Django 5.1+ with custom user model
- Tailwind CSS 3.4+ with DaisyUI
- Dark/Light theme support
- Modern authentication system
- Production-ready configuration
- Custom admin interface with Django Unfold

## Project Structure

```
boilerplate/
├── config/                 # Django settings and configuration
├── core/                   # Core app (homepage, about)
├── accounts/               # User authentication and profiles
├── templates/              # HTML templates
├── static/                 # Static files (CSS, JS, images)
├── media/                  # User uploaded files
└── manage.py              # Django management script
```

Built with ❤️ using the Django + Tailwind CSS Boilerplate.
