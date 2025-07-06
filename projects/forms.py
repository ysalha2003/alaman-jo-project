# Fixed forms.py for projects app - Domain Change Form

from django import forms
from django.core.validators import URLValidator
from .models import Project, DomainChange
import json

class ProjectForm(forms.ModelForm):
    """Enhanced project form with Firebase support"""

    firebase_project_id = forms.CharField(
        max_length=100,
        required=False,
        help_text="Firebase project ID (will be auto-extracted from service account if not provided)",
        widget=forms.TextInput(attrs={'class': 'input input-bordered w-full'})
    )

    class Meta:
        model = Project
        fields = [
            'user', 'app_name', 'description', 'url', 'service_account_data', 
            'status', 'tags', 'firebase_project_id'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'textarea textarea-bordered w-full'}),
            'service_account_data': forms.Textarea(attrs={
                'rows': 12, 
                'class': 'textarea textarea-bordered w-full font-mono',
                'placeholder': 'Paste your Firebase service account JSON here...'
            }),
            'tags': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'tag1, tag2, tag3'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'checkbox'
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'select select-bordered w-full'
            elif field_name not in ['description', 'service_account_data', 'tags', 'firebase_project_id']:
                field.widget.attrs['class'] = 'input input-bordered w-full'

    def clean_service_account_data(self):
        data = self.cleaned_data['service_account_data']
        if isinstance(data, str) and data.strip():
            try:
                parsed_data = json.loads(data)
                # Validate required Firebase service account fields
                required_fields = ['type', 'project_id', 'private_key', 'client_email']
                missing_fields = [field for field in required_fields if field not in parsed_data]
                
                if missing_fields:
                    raise forms.ValidationError(
                        f"Missing required Firebase service account fields: {', '.join(missing_fields)}"
                    )
                
                if parsed_data.get('type') != 'service_account':
                    raise forms.ValidationError("Invalid service account type. Must be 'service_account'.")
                
                return parsed_data
            except json.JSONDecodeError as e:
                raise forms.ValidationError(f"Invalid JSON format: {str(e)}")
        elif isinstance(data, dict):
            return data
        else:
            return {}


class DomainChangeForm(forms.Form):
    """
    Fixed domain change form that matches Flask app behavior
    
    Key Changes:
    - Auto-populates current URL 
    - Shows Firebase vs Local status
    - Clear about what user needs to input
    """
    
    new_url = forms.URLField(
        label="New Domain URL",
        help_text="Enter the new URL you want to set for this project. This will update both local database and Firebase Remote Config.",
        widget=forms.URLInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'https://example.com'
        })
    )
    
    reason = forms.CharField(
        required=False,
        label="Reason for Change",
        help_text="Optional: Explain why you're changing the domain",
        widget=forms.Textarea(attrs={
            'rows': 3, 
            'class': 'textarea textarea-bordered w-full',
            'placeholder': 'Reason for domain change...'
        })
    )

    def __init__(self, *args, **kwargs):
        self.project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)
        
        # Pre-populate with current effective URL if no initial data
        if self.project and not self.initial.get('new_url'):
            # Get the effective URL (Firebase if available, otherwise local)
            current_url = getattr(self.project, 'effective_url', self.project.url)
            self.fields['new_url'].initial = current_url

    def clean_new_url(self):
        url = self.cleaned_data['new_url']
        validator = URLValidator()
        validator(url)
        
        # Check if the URL is different from current project URL
        if self.project:
            current_url = getattr(self.project, 'effective_url', self.project.url)
            if url == current_url:
                raise forms.ValidationError("New URL must be different from the current URL.")
        
        return url


class FirebaseTestForm(forms.Form):
    """Form for testing Firebase connection"""
    
    action = forms.ChoiceField(
        choices=[
            ('test', 'Test Connection'),
            ('get_config', 'Get Current Config'),
            ('sync', 'Sync with Firebase'),
        ],
        widget=forms.Select(attrs={'class': 'select select-bordered w-full'})
    )


class BulkProjectActionForm(forms.Form):
    """Form for bulk actions on projects"""
    
    ACTION_CHOICES = [
        ('activate', 'Activate Projects'),
        ('deactivate', 'Deactivate Projects'),
        ('archive', 'Archive Projects'),
        ('sync_firebase', 'Sync with Firebase'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'select select-bordered w-full'})
    )
    
    project_ids = forms.CharField(
        widget=forms.HiddenInput()
    )
    
    def clean_project_ids(self):
        project_ids = self.cleaned_data['project_ids']
        try:
            ids = [int(id.strip()) for id in project_ids.split(',') if id.strip()]
            return ids
        except ValueError:
            raise forms.ValidationError("Invalid project IDs format.")


class UserLevelForm(forms.Form):
    """Form for changing user levels (similar to Flask app)"""
    
    LEVEL_CHOICES = [
        (1, 'Administrator'),
        (2, 'Regular User'),
        (3, 'Viewer'),
    ]
    
    user_level = forms.ChoiceField(
        choices=LEVEL_CHOICES,
        widget=forms.Select(attrs={'class': 'select select-bordered w-full'})
    )


class ProjectFilterForm(forms.Form):
    """Form for filtering projects"""
    
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + Project.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'select select-bordered w-full'})
    )
    
    user = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__
        required=False,
        empty_label="All Users",
        widget=forms.Select(attrs={'class': 'select select-bordered w-full'})
    )
    
    firebase_enabled = forms.ChoiceField(
        choices=[
            ('', 'All Projects'),
            ('yes', 'Firebase Enabled'),
            ('no', 'Firebase Disabled'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'select select-bordered w-full'})
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'Search projects...'
        })
    )
    
    def __init__(self, *args, **kwargs):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        super().__init__(*args, **kwargs)
        self.fields['user'].queryset = User.objects.filter(projects__isnull=False).distinct()