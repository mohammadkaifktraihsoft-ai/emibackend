from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import UserProfile, Customer, EMI, Payment, BalanceKey, Device


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'


class CustomUserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'get_phone_number', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'userprofile__phone_number')

    def get_phone_number(self, obj):
        return obj.profile.phone_number if hasattr(obj, 'profile') else '-'
    get_phone_number.short_description = 'Phone Number'


# Re-register User with the custom admin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

admin.site.register(Customer)
admin.site.register(EMI)
admin.site.register(Payment)


# ========================
# BALANCE KEY ADMIN
# ========================
class BalanceKeyAdmin(admin.ModelAdmin):
    list_display = ('key_short', 'admin_user', 'is_used', 'used_by', 'created_at', 'used_at')
    list_filter = ('is_used', 'admin_user', 'created_at')
    search_fields = ('key', 'admin_user__username', 'used_by__name')
    readonly_fields = ('key', 'is_used', 'used_by', 'used_at', 'qr_image', 'created_at')
    
    fieldsets = (
        ('Key Information', {
            'fields': ('key', 'qr_image')
        }),
        ('Admin Assignment', {
            'fields': ('admin_user',)
        }),
        ('Usage Tracking', {
            'fields': ('is_used', 'used_by', 'created_at', 'used_at'),
            'description': 'These fields are automatically updated when the key is used.'
        }),
    )
    
    def key_short(self, obj):
        return str(obj.key)[:12] + '...'
    key_short.short_description = 'Key'
    
    def has_delete_permission(self, request, obj=None):
        # Only superusers can delete balance keys
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        # Only superusers can edit balance keys
        return request.user.is_superuser

    def has_add_permission(self, request):
        # Allow custom user assignment by superuser only, staff can also create if desired
        return request.user.is_superuser or request.user.is_staff
    
    def get_queryset(self, request):
        # Superusers see all keys, staff see only their own
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(admin_user=request.user)


admin.site.register(BalanceKey, BalanceKeyAdmin)
admin.site.register(Device)
