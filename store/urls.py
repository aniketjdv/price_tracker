from django.urls import path

from . import views

app_name = "store"

urlpatterns = [
    path("", views.home, name="home"),
    path("product/<slug:slug>/", views.product_detail, name="product_detail"),
    path("cart/", views.cart, name="cart"),
    path("cart/add/<int:product_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/remove/<int:product_id>/", views.remove_from_cart, name="remove_from_cart"),
    path("wishlist/toggle/<int:product_id>/", views.toggle_wishlist, name="toggle_wishlist"),
    path("api/products/", views.api_products, name="api_products"),
    path("api/products/search/", views.api_search, name="api_search"),
    path("api/products/<str:product_id>/", views.api_product, name="api_product"),
    path("api/products/<str:product_id>/price/", views.api_price, name="api_price"),
    path("api/products/<str:product_id>/price-history/", views.api_price_history, name="api_price_history"),
]
