from django import forms
from django.contrib.auth.forms import (
    UserCreationForm,
    AuthenticationForm,
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm,
)
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    """Registration form with styled widgets."""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-input-modern',
            'placeholder': 'your@email.com'
        })
    )
    
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('email', 'username', 'first_name', 'last_name')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-input-modern'
            if 'password' in field_name:
                field.help_text = None
            if field.required:
                field.label = f"{field.label} *"
        
        self.fields['email'].label = "Email Address"
        self.fields['username'].label = "Username"
        self.fields['first_name'].label = "First Name"
        self.fields['last_name'].label = "Last Name"

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user

class CustomAuthenticationForm(AuthenticationForm):
    """Login form that accepts both email and username."""
    username = forms.CharField(
        label="Username or Email",
        widget=forms.TextInput(attrs={
            'class': 'form-input-modern',
            'placeholder': 'Enter your username or email',
            'autocomplete': 'username'
        })
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-input-modern',
            'placeholder': 'Password',
            'autocomplete': 'current-password'
        })
    )

class UserProfileForm(forms.ModelForm):
    """Profile editing form."""
    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'last_name', 'bio', 'profile_picture', 'location', 'website']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.Textarea):
                 field.widget.attrs['class'] = 'form-textarea-modern'
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500'
            elif isinstance(field.widget, forms.FileInput):
                field.widget.attrs['class'] = 'block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100'
            else:
                field.widget.attrs['class'] = 'form-input-modern'

class CustomPasswordChangeForm(PasswordChangeForm):
    """Styled password change form."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-input-modern'

class CustomPasswordResetForm(PasswordResetForm):
    """Styled password reset form."""
    email = forms.EmailField(
        label="Email",
        max_length=254,
        widget=forms.EmailInput(attrs={
            'autocomplete': 'email',
            'class': 'form-input-modern'
        }),
    )

class CustomSetPasswordForm(SetPasswordForm):
    """Styled set password form."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-input-modern'
