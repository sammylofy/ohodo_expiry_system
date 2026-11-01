from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, F, Q, DecimalField, ExpressionWrapper
from django.utils import timezone

from .models import Category, Supplier, Product, AlertLog, StoreProfile, Sale
from .forms import (
    LoginForm, CategoryForm, SupplierForm,
    ProductForm, StoreProfileForm, SaleForm
)
from .alert_service import send_all_alerts
from .jobs import check_expiry_job


# ==========================================
# AUTHENTICATION VIEWS (FBV ONLY)
# ==========================================

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            next_url = request.GET.get('next') or 'dashboard'
            return redirect(next_url)
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm(request)

    return render(request, 'inventory/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out safely.")
    return redirect('login')


# ==========================================
# DASHBOARD VIEW
# ==========================================

@login_required
def dashboard_view(request):
    today = timezone.localdate()
    critical_date = today + timedelta(days=7)
    warning_date = today + timedelta(days=30)

    # Trigger instant expiry scan if requested via button
    if request.method == 'POST' and 'trigger_alerts' in request.POST:
        count = check_expiry_job()
        messages.success(
            request,
            f"Expiry alert scan completed! Dispatched notifications for {count} at-risk product(s)."
        )
        return redirect('dashboard')

    all_products = Product.objects.select_related('category', 'supplier').all()
    total_products = all_products.count()
    total_stock_units = all_products.aggregate(total=Sum('quantity'))['total'] or 0

    stock_value_expr = ExpressionWrapper(
        F('quantity') * F('selling_price'),
        output_field=DecimalField(max_digits=14, decimal_places=2)
    )
    total_inventory_value = all_products.aggregate(val=Sum(stock_value_expr))['val'] or 0

    expired_count = all_products.filter(expiry_date__lt=today, quantity__gt=0).count()
    critical_count = all_products.filter(
        expiry_date__gte=today,
        expiry_date__lte=critical_date,
        quantity__gt=0
    ).count()
    warning_count = all_products.filter(
        expiry_date__gt=critical_date,
        expiry_date__lte=warning_date,
        quantity__gt=0
    ).count()
    safe_count = all_products.filter(expiry_date__gt=warning_date, quantity__gt=0).count()

    urgent_products = all_products.filter(
        expiry_date__lte=warning_date,
        quantity__gt=0
    ).order_by('expiry_date')[:8]

    recent_alerts = AlertLog.objects.select_related('product').all()[:6]
    recent_sales = Sale.objects.select_related('product', 'sold_by').all()[:6]

    context = {
        'total_products': total_products,
        'total_stock_units': total_stock_units,
        'total_inventory_value': total_inventory_value,
        'expired_count': expired_count,
        'critical_count': critical_count,
        'warning_count': warning_count,
        'safe_count': safe_count,
        'urgent_products': urgent_products,
        'recent_alerts': recent_alerts,
        'recent_sales': recent_sales,
    }
    return render(request, 'inventory/dashboard.html', context)


# ==========================================
# PRODUCT CRUD VIEWS
# ==========================================

@login_required
def product_list_view(request):
    today = timezone.localdate()
    products = Product.objects.select_related('category', 'supplier').all()

    search_query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '').strip()
    status_filter = request.GET.get('status', '').strip()

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(batch_number__icontains=search_query) |
            Q(barcode__icontains=search_query)
        )

    if category_id:
        products = products.filter(category_id=category_id)

    if status_filter == 'expired':
        products = products.filter(expiry_date__lt=today)
    elif status_filter == 'critical':
        products = products.filter(expiry_date__gte=today, expiry_date__lte=today + timedelta(days=7))
    elif status_filter == 'warning':
        products = products.filter(
            expiry_date__gt=today + timedelta(days=7),
            expiry_date__lte=today + timedelta(days=30)
        )
    elif status_filter == 'safe':
        products = products.filter(expiry_date__gt=today + timedelta(days=30))

    categories = Category.objects.all()
    context = {
        'products': products,
        'categories': categories,
        'search_query': search_query,
        'selected_category': category_id,
        'selected_status': status_filter,
    }
    return render(request, 'inventory/product_list.html', context)


@login_required
def product_create_view(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            messages.success(request, f"Product '{product.name}' added successfully.")
            return redirect('product_list')
    else:
        form = ProductForm()

    return render(request, 'inventory/product_form.html', {
        'form': form,
        'page_title': 'Add New Product',
        'is_edit': False,
    })


@login_required
def product_update_view(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f"Product '{product.name}' updated successfully.")
            return redirect('product_detail', pk=product.pk)
    else:
        form = ProductForm(instance=product)

    return render(request, 'inventory/product_form.html', {
        'form': form,
        'product': product,
        'page_title': f'Edit Product: {product.name}',
        'is_edit': True,
    })


@login_required
def product_delete_view(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        name = product.name
        product.delete()
        messages.warning(request, f"Product '{name}' has been deleted.")
        return redirect('product_list')

    return render(request, 'inventory/product_confirm_delete.html', {'product': product})


@login_required
def product_detail_view(request, pk):
    product = get_object_or_404(Product.objects.select_related('category', 'supplier'), pk=pk)

    if request.method == 'POST' and 'send_product_alert' in request.POST:
        result = send_all_alerts(product)
        sent_channels = [k.upper() for k, v in result.items() if v]
        if sent_channels:
            messages.success(request, f"Alert dispatched via {', '.join(sent_channels)} for {product.name}.")
        else:
            messages.warning(
                request,
                f"Alert logged for {product.name} (check API/SMTP credentials in .env for external delivery)."
            )
        return redirect('product_detail', pk=product.pk)

    product_alerts = product.alerts.all()[:10]
    product_sales = product.sales.select_related('sold_by').all()[:10]

    return render(request, 'inventory/product_detail.html', {
        'product': product,
        'product_alerts': product_alerts,
        'product_sales': product_sales,
    })


# ==========================================
# CATEGORY CRUD VIEWS
# ==========================================

@login_required
def category_list_view(request):
    categories = Category.objects.all()
    return render(request, 'inventory/category_list.html', {'categories': categories})


@login_required
def category_create_view(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f"Category '{category.name}' created.")
            return redirect('category_list')
    else:
        form = CategoryForm()

    return render(request, 'inventory/category_form.html', {
        'form': form,
        'page_title': 'Create Category',
    })


@login_required
def category_update_view(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f"Category '{category.name}' updated.")
            return redirect('category_list')
    else:
        form = CategoryForm(instance=category)

    return render(request, 'inventory/category_form.html', {
        'form': form,
        'category': category,
        'page_title': f'Edit Category: {category.name}',
    })


@login_required
def category_delete_view(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        name = category.name
        category.delete()
        messages.warning(request, f"Category '{name}' deleted.")
        return redirect('category_list')

    return render(request, 'inventory/category_confirm_delete.html', {'category': category})


# ==========================================
# SUPPLIER CRUD VIEWS
# ==========================================

@login_required
def supplier_list_view(request):
    suppliers = Supplier.objects.all()
    return render(request, 'inventory/supplier_list.html', {'suppliers': suppliers})


@login_required
def supplier_create_view(request):
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier = form.save()
            messages.success(request, f"Supplier '{supplier.name}' added.")
            return redirect('supplier_list')
    else:
        form = SupplierForm()

    return render(request, 'inventory/supplier_form.html', {
        'form': form,
        'page_title': 'Add Supplier',
    })


@login_required
def supplier_update_view(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, f"Supplier '{supplier.name}' updated.")
            return redirect('supplier_list')
    else:
        form = SupplierForm(instance=supplier)

    return render(request, 'inventory/supplier_form.html', {
        'form': form,
        'supplier': supplier,
        'page_title': f'Edit Supplier: {supplier.name}',
    })


@login_required
def supplier_delete_view(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        name = supplier.name
        supplier.delete()
        messages.warning(request, f"Supplier '{name}' deleted.")
        return redirect('supplier_list')

    return render(request, 'inventory/supplier_confirm_delete.html', {'supplier': supplier})


# ==========================================
# POS SALES & HISTORY VIEWS
# ==========================================

@login_required
def sales_view(request):
    if request.method == 'POST':
        form = SaleForm(request.POST)
        if form.is_valid():
            product = form.cleaned_data['product']
            quantity_sold = form.cleaned_data['quantity_sold']

            # Reduce stock safely
            product.quantity -= quantity_sold
            product.save(update_fields=['quantity', 'updated_at'])

            sale = Sale.objects.create(
                product=product,
                quantity_sold=quantity_sold,
                sold_by=request.user
            )
            messages.success(
                request,
                f"Sale recorded: {quantity_sold} x {product.name} (Total: ₦{sale.total_amount:,.2f})."
            )
            return redirect('sales')
    else:
        form = SaleForm()

    recent_sales = Sale.objects.select_related('product', 'sold_by').all()[:8]
    return render(request, 'inventory/sales.html', {
        'form': form,
        'recent_sales': recent_sales,
    })


@login_required
def sales_history_view(request):
    sales = Sale.objects.select_related('product', 'sold_by').all()
    total_revenue = sum(sale.total_amount for sale in sales)
    total_units_sold = sales.aggregate(units=Sum('quantity_sold'))['units'] or 0

    return render(request, 'inventory/sales_history.html', {
        'sales': sales,
        'total_revenue': total_revenue,
        'total_units_sold': total_units_sold,
    })


# ==========================================
# REPORTS & ALERT LOG VIEWS
# ==========================================

@login_required
def reports_view(request):
    today = timezone.localdate()
    critical_date = today + timedelta(days=7)
    warning_date = today + timedelta(days=30)

    products = Product.objects.select_related('category', 'supplier').all()

    expired_products = products.filter(expiry_date__lt=today)
    critical_products = products.filter(expiry_date__gte=today, expiry_date__lte=critical_date)
    warning_products = products.filter(expiry_date__gt=critical_date, expiry_date__lte=warning_date)
    safe_products = products.filter(expiry_date__gt=warning_date)

    loss_expr = ExpressionWrapper(
        F('quantity') * F('cost_price'),
        output_field=DecimalField(max_digits=14, decimal_places=2)
    )
    expired_loss_value = expired_products.aggregate(loss=Sum(loss_expr))['loss'] or 0
    at_risk_value = products.filter(
        expiry_date__gte=today,
        expiry_date__lte=warning_date
    ).aggregate(risk=Sum(loss_expr))['risk'] or 0

    context = {
        'expired_count': expired_products.count(),
        'critical_count': critical_products.count(),
        'warning_count': warning_products.count(),
        'safe_count': safe_products.count(),
        'expired_loss_value': expired_loss_value,
        'at_risk_value': at_risk_value,
        'total_alerts_sent': AlertLog.objects.filter(status='sent').count(),
        'total_alerts_failed': AlertLog.objects.filter(status='failed').count(),
    }
    return render(request, 'inventory/reports.html', context)


@login_required
def expired_report_view(request):
    today = timezone.localdate()
    expired_products = Product.objects.select_related('category', 'supplier').filter(
        expiry_date__lt=today
    ).order_by('expiry_date')

    loss_expr = ExpressionWrapper(
        F('quantity') * F('cost_price'),
        output_field=DecimalField(max_digits=14, decimal_places=2)
    )
    total_expired_loss = expired_products.aggregate(loss=Sum(loss_expr))['loss'] or 0

    return render(request, 'inventory/expired_report.html', {
        'expired_products': expired_products,
        'total_expired_loss': total_expired_loss,
    })


@login_required
def expiring_soon_report_view(request):
    today = timezone.localdate()
    warning_date = today + timedelta(days=30)

    expiring_products = Product.objects.select_related('category', 'supplier').filter(
        expiry_date__gte=today,
        expiry_date__lte=warning_date
    ).order_by('expiry_date')

    return render(request, 'inventory/expiring_soon_report.html', {
        'expiring_products': expiring_products,
    })


@login_required
def alert_log_view(request):
    if request.method == 'POST' and 'run_manual_check' in request.POST:
        count = check_expiry_job()
        messages.success(request, f"Manual expiry check finished. Dispatched alerts for {count} product(s).")
        return redirect('alert_log')

    alert_type_filter = request.GET.get('type', '').strip()
    status_filter = request.GET.get('status', '').strip()

    logs = AlertLog.objects.select_related('product').all()
    if alert_type_filter:
        logs = logs.filter(alert_type=alert_type_filter)
    if status_filter:
        logs = logs.filter(status=status_filter)

    return render(request, 'inventory/alert_log.html', {
        'logs': logs,
        'selected_type': alert_type_filter,
        'selected_status': status_filter,
    })


# ==========================================
# STORE SETTINGS VIEW
# ==========================================

@login_required
def store_settings_view(request):
    profile = StoreProfile.get_solo()
    if request.method == 'POST':
        form = StoreProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Store profile and notification contacts updated successfully.")
            return redirect('store_settings')
    else:
        form = StoreProfileForm(instance=profile)

    return render(request, 'inventory/store_settings.html', {
        'form': form,
        'profile': profile,
    })