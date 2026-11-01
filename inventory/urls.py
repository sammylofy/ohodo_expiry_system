from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboard
    path('', views.dashboard_view, name='dashboard'),

    # Products
    path('products/', views.product_list_view, name='product_list'),
    path('products/add/', views.product_create_view, name='product_create'),
    path('products/<int:pk>/', views.product_detail_view, name='product_detail'),
    path('products/<int:pk>/edit/', views.product_update_view, name='product_update'),
    path('products/<int:pk>/delete/', views.product_delete_view, name='product_delete'),

    # Categories
    path('categories/', views.category_list_view, name='category_list'),
    path('categories/add/', views.category_create_view, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_update_view, name='category_update'),
    path('categories/<int:pk>/delete/', views.category_delete_view, name='category_delete'),

    # Suppliers
    path('suppliers/', views.supplier_list_view, name='supplier_list'),
    path('suppliers/add/', views.supplier_create_view, name='supplier_create'),
    path('suppliers/<int:pk>/edit/', views.supplier_update_view, name='supplier_update'),
    path('suppliers/<int:pk>/delete/', views.supplier_delete_view, name='supplier_delete'),

    # Sales
    path('sales/', views.sales_view, name='sales'),
    path('sales/history/', views.sales_history_view, name='sales_history'),

    # Reports & Alerts
    path('reports/', views.reports_view, name='reports'),
    path('reports/expired/', views.expired_report_view, name='expired_report'),
    path('reports/expiring-soon/', views.expiring_soon_report_view, name='expiring_soon_report'),
    path('alerts/', views.alert_log_view, name='alert_log'),

    # Store Settings
    path('settings/', views.store_settings_view, name='store_settings'),
]