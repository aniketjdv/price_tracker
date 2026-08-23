from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('login/', views.TrackerLoginView.as_view(), name='login'),
    path('signup/', views.signup, name='signup'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('site-admin/', views.admin_dashboard, name='admin_dashboard'),
    path('', views.dashboard_home, name='dashboard_home'),
    path('products/', views.products, name='products'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('alerts/', views.price_alerts, name='price_alerts'),
    path('alerts/create/', views.create_price_alert, name='create_price_alert'),
    path('alerts/<int:alert_id>/edit/', views.edit_price_alert, name='edit_price_alert'),
    path('alerts/<int:alert_id>/delete/', views.delete_price_alert, name='delete_price_alert'),
    path('alerts/<int:alert_id>/toggle/', views.toggle_alert_status, name='toggle_alert_status'),
    path('wishlist/', views.wishlist, name='wishlist'),
    path('analytics/', views.analytics, name='analytics'),
    path('notifications/', views.notifications, name='notifications'),
    path('settings/', views.settings_page, name='settings'),
    path('add-product/', views.add_product, name='add_product'),
    path('track-new/', views.track_new, name='track_new'),
]
