# Simple fix for projects/admin.py - keeps existing field names

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Q
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display
import json

from .models import Project, DomainChange, UserSession


class DomainChangeInline(TabularInline):
    model = DomainChange
    extra = 0
    readonly_fields = ('etag', 'changed_at', 'changed_by')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('changed_by')


@admin.register(Project)
class ProjectAdmin(ModelAdmin):
    inlines = [DomainChangeInline]
    list_display = [
        'app_name',
        'project_id',
        'user_link',
        'status_badge',
        'url_link',
        'firebase_status',
        'last_deployed',
        'created_at'
    ]
    list_filter = ['status', 'created_at', 'user__user_level']
    search_fields = ['app_name', 'project_id', 'user__username', 'user__email', 'firebase_project_id']
    readonly_fields = ['project_id', 'created_at', 'updated_at', 'formatted_service_display', 'firebase_project_id']

    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'app_name', 'project_id', 'status', 'description')
        }),
        ('Configuration', {
            'fields': ('url', 'service_account_data', 'formatted_service_display'),
            'description': 'Project configuration and service settings'
        }),
        ('Firebase Configuration', {
            'fields': ('firebase_project_id', 'firebase_current_url', 'last_firebase_sync', 'firebase_etag'),
            'classes': ('collapse',),
            'description': 'Firebase Remote Config integration'
        }),
        ('Metadata', {
            'fields': ('tags', 'last_deployed', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['activate_projects', 'deactivate_projects', 'archive_projects', 'sync_firebase']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user').annotate(
            domain_changes_count=Count('domain_changes')
        )

    @display(description="User", ordering="user__username")
    def user_link(self, obj):
        url = reverse('admin:accounts_customuser_change', args=[obj.user.pk])
        if hasattr(obj.user, 'user_level'):
            level_badge = self._get_level_badge(obj.user.user_level)
        else:
            level_badge = self._get_level_badge(2)  # Default to regular user
        return format_html(
            '<a href="{}">{}</a> {}',
            url, obj.user.username, level_badge
        )

    @display(description="Status")
    def status_badge(self, obj):
        colors = {
            'active': 'success',
            'inactive': 'warning',
            'maintenance': 'info',
            'archived': 'secondary'
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge badge-{}">{}</span>',
            color, obj.get_status_display()
        )

    @display(description="URL")
    def url_link(self, obj):
        return format_html('<a href="{}" target="_blank">{}</a>', obj.url, obj.url)

    @display(description="Firebase Status")
    def firebase_status(self, obj):
        if not obj.firebase_project_id:
            return format_html('<span class="text-gray-400">Not configured</span>')
        
        if hasattr(obj, 'firebase_current_url') and obj.firebase_current_url:
            return format_html('<span class="text-green-600">✅ Synced</span>')
        else:
            return format_html('<span class="text-yellow-600">⚠️ Not synced</span>')

    @display(description="Service Account Data")
    def formatted_service_display(self, obj):
        try:
            formatted = json.dumps(obj.service_account_data, indent=2)
            return format_html('<pre style="background: #f8f9fa; padding: 10px; border-radius: 4px;">{}</pre>', formatted)
        except:
            return str(obj.service_account_data)

    def _get_level_badge(self, level):
        colors = {1: 'danger', 2: 'primary', 3: 'info'}
        labels = {1: 'Admin', 2: 'User', 3: 'Viewer'}
        color = colors.get(level, 'secondary')
        label = labels.get(level, 'Unknown')
        return format_html('<span class="badge badge-{}">{}</span>', color, label)

    def activate_projects(self, request, queryset):
        updated = queryset.update(status='active')
        self.message_user(request, f'{updated} projects activated.')
    activate_projects.short_description = "Activate selected projects"

    def deactivate_projects(self, request, queryset):
        updated = queryset.update(status='inactive')
        self.message_user(request, f'{updated} projects deactivated.')
    deactivate_projects.short_description = "Deactivate selected projects"

    def archive_projects(self, request, queryset):
        updated = queryset.update(status='archived')
        self.message_user(request, f'{updated} projects archived.')
    archive_projects.short_description = "Archive selected projects"

    def sync_firebase(self, request, queryset):
        """Sync projects with Firebase Remote Config"""
        synced = 0
        for project in queryset:
            if hasattr(project, 'sync_from_firebase'):
                try:
                    if project.sync_from_firebase():
                        synced += 1
                except:
                    pass
        self.message_user(request, f'Synced {synced} projects from Firebase.')
    sync_firebase.short_description = "Sync from Firebase Remote Config"


@admin.register(DomainChange)
class DomainChangeAdmin(ModelAdmin):
    list_display = ['project_link', 'old_url', 'new_url', 'firebase_status_display', 'changed_by_link', 'etag', 'changed_at']
    list_filter = ['changed_at', 'project__status', 'firebase_updated']
    search_fields = ['project__app_name', 'old_url', 'new_url', 'etag']
    readonly_fields = ['etag', 'changed_at']

    fieldsets = (
        ('Change Information', {
            'fields': ('project', 'old_url', 'new_url', 'reason')
        }),
        ('Firebase Tracking', {
            'fields': ('firebase_updated', 'firebase_error', 'firebase_old_value', 'firebase_new_value'),
            'classes': ('collapse',)
        }),
        ('Tracking', {
            'fields': ('etag', 'changed_by', 'changed_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('project', 'changed_by')

    @display(description="Project", ordering="project__app_name")
    def project_link(self, obj):
        url = reverse('admin:projects_project_change', args=[obj.project.pk])
        return format_html('<a href="{}">{}</a>', url, obj.project.app_name)

    @display(description="Firebase Status")
    def firebase_status_display(self, obj):
        if hasattr(obj, 'firebase_updated') and obj.firebase_updated:
            return format_html('<span class="text-green-600">✅ Success</span>')
        elif hasattr(obj, 'firebase_error') and obj.firebase_error:
            return format_html('<span class="text-red-600">❌ Failed</span>')
        else:
            return format_html('<span class="text-gray-400">No Firebase</span>')

    @display(description="Changed By", ordering="changed_by__username")
    def changed_by_link(self, obj):
        if obj.changed_by:
            url = reverse('admin:accounts_customuser_change', args=[obj.changed_by.pk])
            return format_html('<a href="{}">{}</a>', url, obj.changed_by.username)
        return "System"


# Only register UserSession if the model exists
try:
    @admin.register(UserSession)
    class UserSessionAdmin(ModelAdmin):
        list_display = ['user_link', 'ip_address', 'login_time', 'logout_time', 'duration_display', 'is_active']
        list_filter = ['is_active', 'login_time']
        search_fields = ['user__username', 'ip_address', 'user_agent']
        readonly_fields = ['login_time', 'duration_display']

        fieldsets = (
            ('Session Information', {
                'fields': ('user', 'ip_address', 'is_active')
            }),
            ('Timing', {
                'fields': ('login_time', 'logout_time', 'duration_display')
            }),
            ('Technical Details', {
                'fields': ('user_agent',),
                'classes': ('collapse',)
            }),
        )

        def get_queryset(self, request):
            return super().get_queryset(request).select_related('user')

        @display(description="User", ordering="user__username")
        def user_link(self, obj):
            url = reverse('admin:accounts_customuser_change', args=[obj.user.pk])
            if hasattr(obj.user, 'user_level'):
                level_badge = self._get_level_badge(obj.user.user_level)
            else:
                level_badge = ''
            return format_html('<a href="{}">{}</a> {}', url, obj.user.username, level_badge)

        @display(description="Duration")
        def duration_display(self, obj):
            if hasattr(obj, 'duration_display'):
                return obj.duration_display
            return "Unknown"

        def _get_level_badge(self, level):
            colors = {1: 'danger', 2: 'primary', 3: 'info'}
            labels = {1: 'Admin', 2: 'User', 3: 'Viewer'}
            color = colors.get(level, 'secondary')
            label = labels.get(level, 'Unknown')
            return format_html('<span class="badge badge-{}">{}</span>', color, label)

except:
    # UserSession doesn't exist yet
    pass