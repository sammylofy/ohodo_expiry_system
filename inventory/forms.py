from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import Category, Supplier, Product, StoreProfile


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter username',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter password'
        })
    )


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Beverages & Dairy'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional category notes...'}),
        }


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'phone', 'email', 'address']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company or Distributor Name'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 08031234567'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'supplier@example.com'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Distributor warehouse address'}),
        }


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'category', 'supplier', 'batch_number', 'barcode',
            'quantity', 'cost_price', 'selling_price',
            'manufacturing_date', 'expiry_date'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Peak Evaporated Milk 160g'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'batch_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. BCH-2026-089'}),
            'barcode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional barcode digits'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'cost_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'selling_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'manufacturing_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        mfg_date = cleaned_data.get('manufacturing_date')
        exp_date = cleaned_data.get('expiry_date')
        if mfg_date and exp_date and exp_date <= mfg_date:
            self.add_error('expiry_date', 'Expiry date must be later than the manufacturing date.')
        return cleaned_data


class StoreProfileForm(forms.ModelForm):
    class Meta:
        model = StoreProfile
        fields = ['store_name', 'owner_email', 'owner_phone', 'address']
        widgets = {
            'store_name': forms.TextInput(attrs={'class': 'form-control'}),
            'owner_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'owner_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '2348031234567'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class SaleForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Only in-stock products (Qty > 0) are listed."
    )
    quantity_sold = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': 'Enter quantity'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].queryset = Product.objects.filter(quantity__gt=0).order_by('expiry_date', 'name')
        self.fields['product'].label_from_instance = (
            lambda obj: f"{obj.name} (Batch: {obj.batch_number} | Stock: {obj.quantity} | ₦{obj.selling_price} | {obj.status})"
        )

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        quantity_sold = cleaned_data.get('quantity_sold')

        if product and quantity_sold:
            if quantity_sold > product.quantity:
                self.add_error(
                    'quantity_sold',
                    f"Cannot sell {quantity_sold} units. Only {product.quantity} units available in stock."
                )
        return cleaned_data