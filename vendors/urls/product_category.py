from django.urls import path

from ..views.product_category import (
    PublicProductCategoryListView,
    PublicProductCategoryDetailView,
    AdminProductCategoryListCreateView,
    AdminProductCategoryDetailView,
    CategoryOptionsView,
)


urlpatterns = [
    # ============================================================
    # PUBLIC CATEGORY ENDPOINTS
    # ============================================================

    # List all publicly visible categories
    #
    # GET /categories/
    #
    path(
        "categories/",
        PublicProductCategoryListView.as_view(),
        name="category-list",
    ),

    # Retrieve one public category by slug
    #
    # GET /categories/<slug>/
    #
    path(
        "categories/<slug:slug>/",
        PublicProductCategoryDetailView.as_view(),
        name="category-detail",
    ),

    # Retrieve active options belonging to a public category
    #
    # GET /categories/<slug>/options/
    #
    path(
        "categories/<slug:category_slug>/options/",
        CategoryOptionsView.as_view(),
        name="category-options",
    ),

    # ============================================================
    # ADMIN CATEGORY ENDPOINTS
    # ============================================================

    # List and create categories
    #
    # GET  /categories/admin/
    # POST /categories/admin/
    #
    path(
        "categories/admin/",
        AdminProductCategoryListCreateView.as_view(),
        name="admin-category-list-create",
    ),

    # Retrieve, update, or delete a category
    #
    # GET    /categories/admin/<uuid>/
    # PUT    /categories/admin/<uuid>/
    # PATCH  /categories/admin/<uuid>/
    # DELETE /categories/admin/<uuid>/
    #
    path(
        "categories/admin/<uuid:pk>/",
        AdminProductCategoryDetailView.as_view(),
        name="admin-category-detail",
    ),
]