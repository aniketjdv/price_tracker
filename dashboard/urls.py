from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='dashboard_home'),
    path('products/', views.products, name='products'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('alerts/', views.price_alerts, name='price_alerts'),
    path('wishlist/', views.wishlist, name='wishlist'),
    path('analytics/', views.analytics, name='analytics'),
    path('notifications/', views.notifications, name='notifications'),
    path('settings/', views.settings_page, name='settings'),
    path('add-product/', views.add_product, name='add_product'),
    path('track-new/', views.track_new, name='track_new'),
]
