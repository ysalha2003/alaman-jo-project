# Fixed views.py compatible with existing model structure

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
import json
import logging

from .models import Project, DomainChange
from .forms import ProjectForm, DomainChangeForm

# Import utils with fallback
try:
    from .utils import get_client_ip, calculate_elapsed_time_ago, get_user_agent
except ImportError:
    def get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')
    
    def get_user_agent(request):
        return request.META.get('HTTP_USER_AGENT', '')
    
    def calculate_elapsed_time_ago(date):
        if not date:
            return "N/A"
        from django.utils import timezone
        now = timezone.now()
        if hasattr(date, 'replace'):
            if timezone.is_naive(date):
                date = timezone.make_aware(date)
            delta = now - date
            seconds = int(delta.total_seconds())
            if seconds < 60:
                return f"{seconds} seconds ago"
            elif seconds < 3600:
                return f"{seconds // 60} minutes ago"
            elif seconds < 86400:
                return f"{seconds // 3600} hours ago"
            else:
                return f"{seconds // 86400} days ago"
        return "Unknown"

# Try to import UserSession model
try:
    from .models import UserSession
    USERSESSION_AVAILABLE = True
except ImportError:
    USERSESSION_AVAILABLE = False

User = get_user_model()
logger = logging.getLogger(__name__)

@staff_member_required
def dashboard_view(request):
    """Enhanced dashboard matching Flask app functionality"""

    # User statistics (matches Flask structure)
    total_users = User.objects.count()
    admin_users = User.objects.filter(user_level=1).count() if hasattr(User.objects.first(), 'user_level') else 0
    active_sessions = UserSession.objects.filter(is_active=True).count() if USERSESSION_AVAILABLE else 0
    recent_users = User.objects.order_by('-date_joined')[:5]

    # Project statistics
    total_projects = Project.objects.count()
    active_projects = Project.objects.filter(status='active').count()
    
    # Firebase-enabled projects (those with Firebase project ID)
    firebase_enabled_projects = Project.objects.exclude(firebase_project_id='').count()
    
    # Projects with Firebase sync issues
    firebase_sync_issues = Project.objects.filter(
        firebase_project_id__isnull=False
    ).exclude(
        firebase_project_id=''
    ).filter(
        Q(last_firebase_sync__isnull=True) | 
        Q(firebase_current_url='') |
        Q(firebase_current_url__isnull=True)
    ).count()
    
    recent_projects = Project.objects.select_related('user').order_by('-created_at')[:5]

    # Recent domain changes (critical for this app!)
    recent_domain_changes = DomainChange.objects.select_related(
        'project', 'changed_by'
    ).order_by('-changed_at')[:5]

    # Calculate "ago" time for user's last login
    ago = calculate_elapsed_time_ago(request.user.last_login)

    context = {
        'total_users': total_users,
        'admin_users': admin_users,
        'active_sessions': active_sessions,
        'recent_users': recent_users,
        'total_projects': total_projects,
        'active_projects': active_projects,
        'firebase_enabled_projects': firebase_enabled_projects,
        'firebase_sync_issues': firebase_sync_issues,
        'recent_projects': recent_projects,
        'recent_domain_changes': recent_domain_changes,
        'user_ip': get_client_ip(request),
        'user_agent': get_user_agent(request),
        'ago': ago,
    }

    return render(request, 'projects/dashboard.html', context)

@staff_member_required  
def project_list_view(request):
    """
    Project listing with Firebase sync status
    Matches Flask app permissions: Level 1 sees all, Level 2 sees only their own
    """
    
    # Permission check (matches Flask logic)
    if hasattr(request.user, 'user_level') and request.user.user_level == 2:
        # Level 2 users see only their projects (matches Flask)
        projects = Project.objects.filter(user=request.user)
    else:
        # Admins see all projects
        projects = Project.objects.all()
    
    projects = projects.select_related('user').annotate(
        domain_changes_count=Count('domain_changes')
    ).order_by('-created_at')

    # Add pagination
    paginator = Paginator(projects, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'projects/project_list.html', {
        'projects': page_obj,
        'page_obj': page_obj,
    })

@staff_member_required
def project_detail_view(request, project_id):
    """Enhanced project detail with Firebase Remote Config sync"""
    project = get_object_or_404(Project, id=project_id)
    
    # Permission check (matches Flask: users can only see their own projects unless admin)
    if (hasattr(request.user, 'user_level') and 
        request.user.user_level != 1 and 
        project.user != request.user):
        messages.error(request, "Error: This project is not accessible to you!")
        return redirect('projects:project_list')
    
    domain_changes = project.domain_changes.select_related('changed_by').order_by('-changed_at')
    
    # Get Firebase status and sync current URL
    firebase_status = {
        'enabled': project.can_use_firebase() if hasattr(project, 'can_use_firebase') else False,
        'firebase_project_id': getattr(project, 'firebase_project_id', ''),
        'project_id': project.project_id,  # Use existing field name
        'last_sync': getattr(project, 'last_firebase_sync', None),
        'current_value': None,
        'cached_url': project.url,
        'firebase_url': getattr(project, 'firebase_current_url', ''),
        'effective_url': getattr(project, 'effective_url', project.url) if hasattr(project, 'effective_url') else project.url,
        'url_source': getattr(project, 'url_source', 'Local Database') if hasattr(project, 'url_source') else 'Local Database',
        'error': None
    }
    
    # Try to sync from Firebase (get the REAL current URL)
    if hasattr(project, 'can_use_firebase') and project.can_use_firebase():
        try:
            current_firebase_url = project.sync_from_firebase() if hasattr(project, 'sync_from_firebase') else None
            if current_firebase_url:
                firebase_status['current_value'] = current_firebase_url
                firebase_status['firebase_url'] = current_firebase_url
                firebase_status['effective_url'] = current_firebase_url
                firebase_status['url_source'] = "Firebase Remote Config (Live)"
        except Exception as e:
            firebase_status['error'] = str(e)
            logger.error(f"Firebase sync error for project {project_id}: {e}")

    context = {
        'project': project,
        'domain_changes': domain_changes,
        'firebase_status': firebase_status,
    }

    return render(request, 'projects/project_detail.html', context)

@login_required
def change_domain_view(request, project_id):
    """
    Fixed domain change view that matches Flask app behavior
    """
    project = get_object_or_404(Project, id=project_id)
    
    # Permission check (matches Flask logic exactly)
    if (hasattr(request.user, 'user_level') and 
        request.user.user_level != 1 and 
        project.user != request.user):
        messages.error(request, "Error: This Project is not for you!!!!")
        return redirect('projects:project_list')

    # Get current URL status from both local DB and Firebase
    current_status = {
        'local_url': project.url,
        'firebase_url': None,
        'effective_url': project.url,  # Default to local
        'firebase_project_id': getattr(project, 'firebase_project_id', ''),
        'firebase_enabled': False,
        'firebase_error': None,
        'firebase_etag': None,
        'last_sync': getattr(project, 'last_firebase_sync', None)
    }
    
    # Try to get current URL from Firebase
    firebase_manager = None
    if hasattr(project, 'can_use_firebase') and project.can_use_firebase():
        current_status['firebase_enabled'] = True
        try:
            firebase_manager = project.get_firebase_manager()
            if firebase_manager and firebase_manager._get():
                firebase_url = firebase_manager.get_default_value()
                if firebase_url:
                    current_status['firebase_url'] = firebase_url
                    current_status['effective_url'] = firebase_url  # Firebase takes priority
                    current_status['firebase_etag'] = firebase_manager.etag
                    
                    # Update our local cache
                    if hasattr(project, 'firebase_current_url'):
                        project.firebase_current_url = firebase_url
                        project.last_firebase_sync = timezone.now()
                        project.save(update_fields=['firebase_current_url', 'last_firebase_sync'])
        except Exception as e:
            current_status['firebase_error'] = str(e)
            logger.error(f"Firebase get error for project {project_id}: {e}")

    if request.method == 'POST':
        form = DomainChangeForm(request.POST, project=project)
        if form.is_valid():
            new_url = form.cleaned_data['new_url']
            reason = form.cleaned_data['reason']
            
            # Track what we're changing from
            old_local_url = project.url
            old_firebase_url = current_status['firebase_url'] or project.url
            
            # Create domain change record
            domain_change = DomainChange.objects.create(
                project=project,
                old_url=old_local_url,  # Local DB old URL
                new_url=new_url,
                reason=reason,
                changed_by=request.user,
            )
            
            # Add Firebase tracking if available
            if hasattr(domain_change, 'firebase_old_value'):
                domain_change.firebase_old_value = old_firebase_url
                domain_change.firebase_new_value = new_url

            # Step 1: Update local database (cache/reference)
            project.url = new_url
            project.save(update_fields=['url', 'updated_at'])

            # Step 2: Update Firebase Remote Config (THE CRITICAL PART!)
            firebase_success = False
            if firebase_manager:
                try:
                    success, message = firebase_manager.update_remote_config(new_url)
                    if success:
                        firebase_success = True
                        if hasattr(domain_change, 'firebase_updated'):
                            domain_change.firebase_updated = True
                        if hasattr(domain_change, 'firebase_etag'):
                            domain_change.firebase_etag = firebase_manager.etag
                        
                        # Update project Firebase tracking
                        if hasattr(project, 'firebase_etag'):
                            project.firebase_etag = firebase_manager.etag
                        if hasattr(project, 'last_firebase_sync'):
                            project.last_firebase_sync = timezone.now()
                        if hasattr(project, 'firebase_current_url'):
                            project.firebase_current_url = new_url  # Update our cache
                        project.save()
                        
                        messages.success(request, 
                            f'✅ Success! Domain changed for {project.app_name}!\n'
                            f'• Local Database: Updated to {new_url}\n'
                            f'• Firebase Remote Config: Updated to {new_url}\n'
                            f'• Mobile apps will now use: {new_url}'
                        )
                    else:
                        if hasattr(domain_change, 'firebase_error'):
                            domain_change.firebase_error = message
                        messages.error(request, 
                            f'❌ Critical Error!\n'
                            f'• Local Database: ✅ Updated to {new_url}\n'
                            f'• Firebase Remote Config: ❌ FAILED to update!\n'
                            f'• Mobile apps are still using: {old_firebase_url}\n'
                            f'• Error: {message}'
                        )
                except Exception as e:
                    error_msg = str(e)
                    if hasattr(domain_change, 'firebase_error'):
                        domain_change.firebase_error = error_msg
                    logger.error(f"Firebase update error for project {project_id}: {e}")
                    messages.error(request, 
                        f'❌ Critical Error!\n'
                        f'• Local Database: ✅ Updated to {new_url}\n'
                        f'• Firebase Remote Config: ❌ FAILED to update!\n'
                        f'• Mobile apps are still using: {old_firebase_url}\n'
                        f'• Error: {error_msg}'
                    )
            else:
                messages.warning(request, 
                    f'⚠️ Partial Success!\n'
                    f'• Local Database: ✅ Updated to {new_url}\n'
                    f'• Firebase Remote Config: ⚠️ Not configured\n'
                    f'• Mobile apps may not get the update!'
                )
            
            domain_change.save()
            return redirect('projects:project_detail', project_id=project.id)
            
    else:
        # Initialize form (don't pre-fill new_url, let user decide)
        form = DomainChangeForm(project=project)

    context = {
        'project': project,
        'form': form,
        'current_status': current_status,
    }

    return render(request, 'projects/change_domain.html', context)

@require_http_methods(["GET"])
def api_stats(request):
    """Enhanced API endpoint for dashboard stats"""
    stats = {
        'users': {
            'total': User.objects.count(),
            'admins': User.objects.filter(user_level=1).count() if hasattr(User.objects.first(), 'user_level') else 0,
            'regular': User.objects.filter(user_level=2).count() if hasattr(User.objects.first(), 'user_level') else 0,
            'viewers': User.objects.filter(user_level=3).count() if hasattr(User.objects.first(), 'user_level') else 0,
            'active_sessions': UserSession.objects.filter(is_active=True).count() if USERSESSION_AVAILABLE else 0,
        },
        'projects': {
            'total': Project.objects.count(),
            'active': Project.objects.filter(status='active').count(),
            'inactive': Project.objects.filter(status='inactive').count(),
            'maintenance': Project.objects.filter(status='maintenance').count(),
            'archived': Project.objects.filter(status='archived').count(),
            'firebase_enabled': Project.objects.exclude(firebase_project_id='').count(),
            'firebase_sync_issues': Project.objects.filter(
                firebase_project_id__isnull=False
            ).exclude(firebase_project_id='').filter(
                Q(firebase_current_url='') | Q(firebase_current_url__isnull=True)
            ).count(),
        },
        'domain_changes': {
            'total': DomainChange.objects.count(),
            'today': DomainChange.objects.filter(changed_at__date=timezone.now().date()).count(),
            'firebase_successful': DomainChange.objects.filter(firebase_updated=True).count() if hasattr(DomainChange.objects.first(), 'firebase_updated') else 0,
            'firebase_failed': DomainChange.objects.filter(firebase_updated=False).exclude(firebase_error='').count() if hasattr(DomainChange.objects.first(), 'firebase_updated') else 0,
        }
    }
    
    return JsonResponse(stats)

@login_required
@require_http_methods(["POST"])
def sync_firebase_url(request, project_id):
    """Sync current URL from Firebase Remote Config"""
    project = get_object_or_404(Project, id=project_id)
    
    # Permission check
    if (hasattr(request.user, 'user_level') and 
        request.user.user_level != 1 and 
        project.user != request.user):
        return JsonResponse({'success': False, 'message': 'Permission denied'})
    
    if not hasattr(project, 'can_use_firebase') or not project.can_use_firebase():
        return JsonResponse({
            'success': False, 
            'message': 'Firebase configuration is incomplete'
        })
    
    try:
        current_url = project.sync_from_firebase() if hasattr(project, 'sync_from_firebase') else None
        if current_url:
            return JsonResponse({
                'success': True,
                'message': 'Successfully synced from Firebase',
                'current_url': current_url,
                'local_cached_url': project.url,
                'firebase_url': getattr(project, 'firebase_current_url', ''),
                'url_source': getattr(project, 'url_source', 'Firebase Remote Config') if hasattr(project, 'url_source') else 'Firebase Remote Config'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Failed to retrieve URL from Firebase'
            })
    except Exception as e:
        logger.error(f"Firebase sync error: {e}")
        return JsonResponse({
            'success': False,
            'message': f'Firebase sync error: {str(e)}'
        })

@login_required
@require_http_methods(["POST"])
def test_firebase_connection(request, project_id):
    """Test Firebase connection for a project"""
    project = get_object_or_404(Project, id=project_id)
    
    # Permission check
    if (hasattr(request.user, 'user_level') and 
        request.user.user_level != 1 and 
        project.user != request.user):
        return JsonResponse({'success': False, 'message': 'Permission denied'})
    
    if not hasattr(project, 'can_use_firebase') or not project.can_use_firebase():
        return JsonResponse({
            'success': False, 
            'message': 'Firebase configuration is incomplete'
        })
    
    try:
        firebase_manager = project.get_firebase_manager()
        if not firebase_manager:
            return JsonResponse({
                'success': False, 
                'message': 'Failed to create Firebase manager'
            })
        
        if firebase_manager._get():
            current_value = firebase_manager.get_default_value()
            return JsonResponse({
                'success': True,
                'message': 'Firebase connection successful',
                'firebase_project_id': getattr(project, 'firebase_project_id', ''),
                'current_firebase_url': current_value,
                'local_cached_url': project.url,
                'etag': firebase_manager.etag
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Failed to retrieve Firebase config'
            })
    except Exception as e:
        logger.error(f"Firebase test connection error: {e}")
        return JsonResponse({
            'success': False,
            'message': f'Firebase connection error: {str(e)}'
        })

@staff_member_required
def firebase_projects_view(request):
    """View for managing Firebase-enabled projects"""
    try:
        firebase_projects = Project.objects.exclude(firebase_project_id='').select_related('user')
        
        # Add Firebase sync status
        for project in firebase_projects:
            try:
                if hasattr(project, 'sync_from_firebase'):
                    project.current_firebase_url = project.sync_from_firebase()
                else:
                    project.current_firebase_url = None
            except:
                project.current_firebase_url = None
                
    except:
        firebase_projects = Project.objects.none()
    
    context = {
        'firebase_projects': firebase_projects,
    }
    
    return render(request, 'projects/firebase_projects.html', context)