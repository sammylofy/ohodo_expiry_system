from django.contrib import admin
from .models import Category, Supplier, Product, AlertLog, StoreProfile, Sale


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name',)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'created_at')
    search_fields = ('name', 'phone', 'email')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'batch_number', 'category', 'quantity', 'expiry_date', 'selling_price')
    list_filter = ('category', 'supplier', 'expiry_date')
    search_fields = ('name', 'batch_number', 'barcode')


@admin.register(AlertLog)
class AlertLogAdmin(admin.ModelAdmin):
    list_display = ('product', 'alert_type', 'status', 'created_at')
    list_filter = ('alert_type', 'status', 'created_at')


@admin.register(StoreProfile)
class StoreProfileAdmin(admin.ModelAdmin):
    list_display = ('store_name', 'owner_email', 'owner_phone', 'updated_at')


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity_sold', 'sold_by', 'sold_at')
    list_filter = ('sold_at', 'sold_by')