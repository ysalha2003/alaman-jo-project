from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.contrib.auth.admin import GroupAdmin as DefaultGroupAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from unfold.admin import ModelAdmin
from unfold.forms import UserCreationForm as UnfoldUserCreationForm
from unfold.forms import UserChangeForm as UnfoldUserChangeForm
from unfold.decorators import display
from .models import CustomUser

class CustomUserAdminCreationForm(UnfoldUserCreationForm):
    class Meta(UnfoldUserCreationForm.Meta):
        model = CustomUser
        fields = ("username", "email")

class CustomUserAdminChangeForm(UnfoldUserChangeForm):
    class Meta(UnfoldUserChangeForm.Meta):
        model = CustomUser
        fields = "__all__"

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin, ModelAdmin):
    form = CustomUserAdminChangeForm
    add_form = CustomUserAdminCreationForm
    
    compressed_fields = False
    
    model = CustomUser
    list_display = (
        'username', 'email', 'level_badge', 'last_login_info', 
        'orders_count', 'is_active_session', 'date_joined'
    )
    list_filter = ('user_level', 'is_staff', 'is_superuser', 'is_active', 'groups', 'is_active_session')
    search_fields = ('email', 'username', 'first_name', 'last_name', 'last_login_ip')
    ordering = ('-date_joined',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('Profile Information', {
            'fields': ('bio', 'profile_picture', 'location', 'website'), 
            'classes': ('collapse',)
        }),
        ('Access Level', {
            'fields': ('user_level',),
            'description': 'User permission level in the system'
        }),
        ('Session Tracking', {
            'fields': ('last_login_ip', 'last_user_agent', 'login_count', 'is_active_session'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Profile Information', {
            'fields': ('first_name', 'last_name', 'email', 'user_level', 'bio', 'profile_picture', 'location', 'website')
        }),
    )
    
    actions = ['promote_to_admin', 'demote_to_user', 'end_sessions']
    
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            orders_count=Count('orders')
        )
    
    @display(description="Level", ordering="user_level")
    def level_badge(self, obj):
        colors = {1: 'danger', 2: 'primary', 3: 'info'}
        color = colors.get(obj.user_level, 'secondary')
        return format_html(
            '<span class="badge badge-{}">{}</span>',
            color, obj.level_display
        )
    
    @display(description="Last Login", ordering="last_login")
    def last_login_info(self, obj):
        if obj.last_login and obj.last_login_ip:
            return format_html(
                '{}<br><small class="text-muted">{}</small>',
                obj.last_login.strftime('%Y-%m-%d %H:%M'),
                obj.last_login_ip
            )
        return "Never"
    
    @display(description="Orders", ordering="orders_count")
    def orders_count(self, obj):
        count = obj.orders_count
        if count > 0:
            url = reverse('admin:shop_order_changelist') + f'?user__id__exact={obj.id}'
            return format_html('<a href="{}">{} orders</a>', url, count)
        return "No orders"
    
    def get_readonly_fields(self, request, obj=None):
        readonly = ['last_login_ip', 'last_user_agent', 'login_count']
        if obj:
            readonly.append('email')
        return readonly
    
    def promote_to_admin(self, request, queryset):
        updated = queryset.update(user_level=1)
        self.message_user(request, f'{updated} users promoted to admin.')
    promote_to_admin.short_description = "Promote to admin level"
    
    def demote_to_user(self, request, queryset):
        updated = queryset.update(user_level=2)
        self.message_user(request, f'{updated} users set to regular user level.')
    demote_to_user.short_description = "Set to regular user level"
    
    def end_sessions(self, request, queryset):
        updated = queryset.update(is_active_session=False)
        self.message_user(request, f'Ended sessions for {updated} users.')
    end_sessions.short_description = "End active sessions"

admin.site.unregister(Group)

@admin.register(Group)
class CustomGroupAdmin(DefaultGroupAdmin, ModelAdmin):
    pass
