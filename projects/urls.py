# Updated projects/urls.py

from django.urls import path
from .views import (
    dashboard_view, project_list_view, project_detail_view,
    change_domain_view, api_stats, test_firebase_connection, 
    sync_firebase_url, firebase_projects_view
)

app_name = 'projects'

urlpatterns = [
    path('dashboard/', dashboard_view, name='dashboard'),
    path('projects/', project_list_view, name='project_list'),
    path('projects/<int:project_id>/', project_detail_view, name='project_detail'),
    path('projects/<int:project_id>/change-domain/', change_domain_view, name='change_domain'),
    path('projects/<int:project_id>/test-firebase/', test_firebase_connection, name='test_firebase_connection'),
    path('projects/<int:project_id>/sync-firebase/', sync_firebase_url, name='sync_firebase_url'),
    path('firebase-projects/', firebase_projects_view, name='firebase_projects'),
    path('api/stats/', api_stats, name='api_stats'),
]