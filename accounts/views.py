from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect
from .forms import CustomUserCreationForm, CustomAuthenticationForm, UserProfileForm

def register_view(request):
    """User registration view."""
    if request.user.is_authenticated:
        return redirect('accounts:profile')

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Authenticate the user to set the backend attribute
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password1')
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome, {user.username}! Your account has been created.')
                return redirect('accounts:profile')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form})

class CustomLoginView(LoginView):
    """Custom login view with styled form."""
    form_class = CustomAuthenticationForm
    template_name = 'registration/login.html'

@login_required
def profile_view(request):
    """User profile view."""
    return render(request, 'accounts/profile.html', {'user': request.user})

@login_required
def profile_edit_view(request):
    """Profile editing view."""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    return render(request, 'accounts/profile_edit.html', {'form': form})
