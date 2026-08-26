from django.urls import path
from ..views.product_category import (
    PublicProductCategoryListView,
    PublicProductCategoryDetailView,
    AdminProductCategoryListCreateView,
    AdminProductCategoryDetailView,
)


urlpatterns = [

    # ==================================================
    # Public
    # ==================================================

    path(
        "categories/",
        PublicProductCategoryListView.as_view(),
        name="category-list",
    ),

    path(
        "categories/detail/<slug:slug>/",
        PublicProductCategoryDetailView.as_view(),
        name="category-detail",
    ),

    # ==================================================
    # Admin
    # ==================================================

    path(
        "categories/admin/",
        AdminProductCategoryListCreateView.as_view(),
        name="admin-category-list-create",
    ),

    path(
        "categories/admin/<int:pk>/",
        AdminProductCategoryDetailView.as_view(),
        name="admin-category-detail",
    ),
]