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
        "",
        PublicProductCategoryListView.as_view(),
        name="category-list",
    ),

    path(
        "detail/<slug:slug>/",
        PublicProductCategoryDetailView.as_view(),
        name="category-detail",
    ),

    # ==================================================
    # Admin
    # ==================================================

    path(
        "admin/",
        AdminProductCategoryListCreateView.as_view(),
        name="admin-category-list-create",
    ),

    path(
        "admin/<int:pk>/",
        AdminProductCategoryDetailView.as_view(),
        name="admin-category-detail",
    ),
]