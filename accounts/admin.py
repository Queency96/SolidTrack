from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):

    ordering = ("id",)

    list_display = (
        "id",
        "email",
        "first_name",
        "last_name",
        "role",
        "is_email_verified",
        "is_phone_verified",
        "is_staff",
        "is_active",
    )

    list_filter = (
        "role",
        "is_staff",
        "is_active",
        "is_email_verified",
        "is_phone_verified",
    )

    search_fields = (
        "email",
        "phone_number",
        "first_name",
        "last_name",
    )

    fieldsets = (

        ("Authentication", {
            "fields": (
                "email",
                "password",
            )
        }),

        ("Personal Information", {
            "fields": (
                "first_name",
                "last_name",
                "phone_number",
                "profile_picture",
            )
        }),

        ("Verification", {
            "fields": (
                "is_email_verified",
                "is_phone_verified",
            )
        }),

        ("Role", {
            "fields": (
                "role",
            )
        }),

        ("Permissions", {
            "fields": (
                "is_active",
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            )
        }),

        ("Important Dates", {
            "fields": (
                "last_login",
                "date_joined",
            )
        }),
    )

    add_fieldsets = (

        (
            None,
            {
                "classes": ("wide",),

                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "phone_number",
                    "password1",
                    "password2",
                    "role",
                ),
            },
        ),
    )