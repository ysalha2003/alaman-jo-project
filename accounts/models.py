from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

class CustomUser(AbstractUser):
    """Enhanced user model with tracking capabilities."""
    
    # User levels matching the Flask app
    USER_LEVELS = [
        (1, 'Administrator'),
        (2, 'Regular User'),
        (3, 'Viewer'),
    ]
    
    email = models.EmailField(unique=True)
    bio = models.TextField(max_length=500, blank=True, help_text="Brief bio about yourself.")
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    location = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    date_joined = models.DateTimeField(default=timezone.now)
    
    # Enhanced tracking fields (ADD THESE NEW FIELDS)
    user_level = models.IntegerField(choices=USER_LEVELS, default=2)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    last_user_agent = models.TextField(blank=True)
    login_count = models.PositiveIntegerField(default=0)
    is_active_session = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        ordering = ['-date_joined']
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.username

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def level_display(self):
        return dict(self.USER_LEVELS).get(self.user_level, 'Unknown')
    
    @property
    def is_admin_level(self):
        return self.user_level == 1