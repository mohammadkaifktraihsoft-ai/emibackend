from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import UserProfile, Customer, EMI, Payment


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
