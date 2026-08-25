from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('login/', views.TrackerLoginView.as_view(), name='login'),
    path('signup/', views.signup, name='signup'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('site-admin/', views.admin_dashboard, name='admin_dashboard'),
    path('site-admin/products/create/', views.admin_create_product, name='admin_create_product'),
    path('site-admin/products/<int:product_id>/edit/', views.admin_edit_product, name='admin_edit_product'),
    path('site-admin/products/<int:product_id>/delete/', views.admin_delete_product, name='admin_delete_product'),
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

    # AI & ML API Endpoints
    path('api/ai/products/<int:product_id>/analysis/', views.api_ai_product_analysis, name='api_ai_product_analysis'),
    path('api/ai/products/<int:product_id>/prediction/', views.api_ai_product_prediction, name='api_ai_product_prediction'),
    path('api/ai/products/<int:product_id>/recommendation/', views.api_ai_product_recommendation, name='api_ai_product_recommendation'),
    path('api/ai/products/<int:product_id>/anomaly/', views.api_ai_product_anomaly, name='api_ai_product_anomaly'),
    path('api/ai/metrics/', views.api_ai_metrics, name='api_ai_metrics'),
]

