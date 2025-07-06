from django.shortcuts import render
from django.contrib.auth import get_user_model
from django.apps import apps

User = get_user_model()

def home_view(request):
    """Homepage with stats and recent members."""
    total_users = User.objects.count()
    recent_users = User.objects.order_by('-date_joined')[:6]
    
    # Try to get project stats if the projects app is available
    active_projects = 0
    total_projects = 0
    try:
        Project = apps.get_model('projects', 'Project')
        total_projects = Project.objects.count()
        active_projects = Project.objects.filter(status='active').count()
    except LookupError:
        # Projects app not available yet
        pass
    
    context = {
        'total_users': total_users,
        'recent_users': recent_users,
        'total_projects': total_projects,
        'active_projects': active_projects,
    }
    return render(request, 'core/home.html', context)

def about_view(request):
    """About page."""
    return render(request, 'core/about.html')