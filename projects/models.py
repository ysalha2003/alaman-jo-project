# Minimal update to existing projects/models.py
# This approach keeps your existing fields and just adds Firebase functionality

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import URLValidator
import json
import uuid

User = get_user_model()

class Project(models.Model):
    """
    Enhanced Project model - keeping existing structure, adding Firebase features
    """

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('maintenance', 'Maintenance'),
        ('archived', 'Archived'),
    ]

    # ===== EXISTING FIELDS (keep as is) =====
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    app_name = models.CharField(max_length=100, help_text="Application name")
    project_id = models.CharField(max_length=50, unique=True, help_text="Unique project identifier")
    service_account_data = models.JSONField(default=dict, help_text="Service account configuration in JSON format")
    url = models.URLField(help_text="Project URL")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_deployed = models.DateTimeField(null=True, blank=True)
    description = models.TextField(blank=True)
    tags = models.CharField(max_length=200, blank=True, help_text="Comma-separated tags")

    # ===== NEW FIREBASE FIELDS (add these) =====
    firebase_project_id = models.CharField(
        max_length=100, 
        blank=True, 
        help_text="Firebase project ID from service account JSON (e.g., 'royaltv-1b482')"
    )
    last_firebase_sync = models.DateTimeField(null=True, blank=True)
    firebase_etag = models.CharField(max_length=100, blank=True, help_text="Last Firebase etag")
    firebase_current_url = models.URLField(
        blank=True, 
        help_text="Current URL from Firebase Remote Config 'activity' parameter (source of truth)"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Project'
        verbose_name_plural = 'Projects'

    def __str__(self):
        return f"{self.app_name} ({self.project_id})"

    def save(self, *args, **kwargs):
        if not self.project_id:
            self.project_id = f"{self.app_name.lower()}-{str(uuid.uuid4())[:8]}"
        
        # Extract Firebase project ID from service account data if not set
        if not self.firebase_project_id and self.service_account_data:
            self.firebase_project_id = self._extract_firebase_project_id()
        
        super().save(*args, **kwargs)

    def _extract_firebase_project_id(self):
        """Extract Firebase project ID from service account JSON"""
        try:
            if isinstance(self.service_account_data, dict):
                return self.service_account_data.get('project_id', '')
            elif isinstance(self.service_account_data, str):
                data = json.loads(self.service_account_data)
                return data.get('project_id', '')
        except (json.JSONDecodeError, KeyError):
            pass
        return ''

    @property
    def formatted_service_data(self):
        """Return formatted JSON for display."""
        try:
            if isinstance(self.service_account_data, dict):
                return json.dumps(self.service_account_data, indent=2)
            elif isinstance(self.service_account_data, str):
                data = json.loads(self.service_account_data)
                return json.dumps(data, indent=2)
            else:
                return str(self.service_account_data)
        except:
            return str(self.service_account_data)

    @property
    def service_account_json(self):
        """Get service account data as JSON string for Firebase manager"""
        if isinstance(self.service_account_data, dict):
            return json.dumps(self.service_account_data)
        elif isinstance(self.service_account_data, str):
            try:
                json.loads(self.service_account_data)
                return self.service_account_data
            except json.JSONDecodeError:
                return None
        return None

    def can_use_firebase(self):
        """Check if project has valid Firebase configuration"""
        return bool(self.firebase_project_id and self.service_account_json)

    def get_firebase_manager(self):
        """Get Firebase Remote Config Manager instance"""
        if not self.can_use_firebase():
            return None
        
        try:
            from .firebase_manager import FirebaseRemoteConfigManager
            return FirebaseRemoteConfigManager(self.firebase_project_id, self.service_account_json)
        except Exception:
            return None

    def sync_from_firebase(self):
        """
        Sync the current URL from Firebase Remote Config
        This gets the REAL active URL from Firebase 'activity' parameter
        """
        firebase_manager = self.get_firebase_manager()
        if firebase_manager:
            try:
                if firebase_manager._get():
                    current_firebase_url = firebase_manager.get_default_value()
                    if current_firebase_url:
                        self.firebase_current_url = current_firebase_url
                        self.last_firebase_sync = timezone.now()
                        self.firebase_etag = firebase_manager.etag
                        self.save(update_fields=['firebase_current_url', 'last_firebase_sync', 'firebase_etag'])
                        return current_firebase_url
            except Exception as e:
                print(f"Firebase sync error: {e}")
        return None

    @property
    def effective_url(self):
        """
        Get the effective URL - Firebase if available, otherwise local cached URL
        This represents what the apps are actually using
        """
        return self.firebase_current_url or self.url

    @property 
    def url_source(self):
        """Indicate where the effective URL comes from"""
        if self.firebase_current_url:
            return "Firebase Remote Config (Live)"
        return "Local Database (Cached)"


class DomainChange(models.Model):
    """Track domain changes for projects."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='domain_changes')
    old_url = models.URLField()
    new_url = models.URLField()
    etag = models.CharField(max_length=100, help_text="Change tracking etag")
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True)
    
    # ===== NEW FIREBASE TRACKING FIELDS =====
    firebase_updated = models.BooleanField(default=False, help_text="Whether Firebase Remote Config was updated")
    firebase_etag = models.CharField(max_length=100, blank=True, help_text="Firebase etag after update")
    firebase_error = models.TextField(blank=True, help_text="Firebase update error if any")
    firebase_old_value = models.URLField(blank=True, help_text="Previous value from Firebase")
    firebase_new_value = models.URLField(blank=True, help_text="New value in Firebase")

    class Meta:
        ordering = ['-changed_at']
        verbose_name = 'Domain Change'
        verbose_name_plural = 'Domain Changes'

    def __str__(self):
        status = "✅ Success" if self.firebase_updated else "❌ Failed"
        return f"{self.project.app_name}: {self.old_url} → {self.new_url} ({status})"

    def save(self, *args, **kwargs):
        if not self.etag:
            self.etag = f"etag-{int(timezone.now().timestamp())}-{uuid.uuid4().hex[:6]}"
        super().save(*args, **kwargs)

    @property
    def is_successful(self):
        """Domain change is successful if Firebase was updated"""
        return self.firebase_updated


class UserSession(models.Model):
    """Track user sessions for dashboard analytics."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=40, blank=True, help_text="Django session key")
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    login_time = models.DateTimeField(auto_now_add=True)
    logout_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    last_activity = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-login_time']
        verbose_name = 'User Session'
        verbose_name_plural = 'User Sessions'

    def __str__(self):
        return f"{self.user.username} - {self.ip_address} ({self.login_time})"

    @property
    def duration(self):
        end_time = self.logout_time if self.logout_time else timezone.now()
        return end_time - self.login_time

    @property
    def duration_display(self):
        """Human readable duration"""
        duration = self.duration
        hours = duration.total_seconds() // 3600
        minutes = (duration.total_seconds() % 3600) // 60
        return f"{int(hours)}h {int(minutes)}m"