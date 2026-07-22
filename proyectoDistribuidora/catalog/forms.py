import csv
import io

from django import forms
from accounts.models import Role, User
from .models import Brand, Category, Discount, Product, Store


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class StoreForm(forms.ModelForm):
    class Meta:
        model = Store
        # distributor is set server-side from request.user.distributor, not
        # client-supplied — see catalog/views.py.
        fields = ['name', 'address', 'phone_number', 'owner', 'vendor']

    def __init__(self, *args, distributor=None, **kwargs):
        super().__init__(*args, **kwargs)
        if distributor is not None:
            # Both conditions together — filtering by role alone without
            # distributor= would leak cross-tenant users into the dropdown.
            self.fields['owner'].queryset = User.objects.filter(
                distributor=distributor, role=Role.STORE_OWNER
            )
            self.fields['vendor'].queryset = User.objects.filter(
                distributor=distributor, role=Role.VENDOR
            )


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        # distributor is set server-side — see catalog/views.py.
        fields = ['name']


class BrandForm(forms.ModelForm):
    class Meta:
        model = Brand
        # distributor is set server-side — see catalog/views.py.
        fields = ['name']


class ProductForm(forms.ModelForm):
    # Not model fields — handled manually in the view and written to
    # ProductImage rows, since a single ModelForm can't map one FileField
    # to a one-to-many related model.
    main_image = forms.ImageField(required=False, label='Imagen principal')
    additional_images = forms.FileField(
        required=False,
        label='Imágenes adicionales',
        widget=MultipleFileInput(attrs={'multiple': True}),
    )

    class Meta:
        model = Product
        # distributor is set server-side from request.user.distributor, not
        # client-supplied — see catalog/views.py.
        fields = [
            'name', 'sku', 'barcode', 'category', 'brand',
            'description', 'unit_price', 'unit_of_measure',
            'status', 'low_stock_threshold',
        ]

    def __init__(self, *args, distributor=None, **kwargs):
        super().__init__(*args, **kwargs)
        if distributor is not None:
            self.fields['category'].queryset = Category.objects.filter(distributor=distributor)
            self.fields['brand'].queryset = Brand.objects.filter(distributor=distributor)


class DiscountForm(forms.ModelForm):
    class Meta:
        model = Discount
        fields = ['discount_type', 'discount_value', 'start_date', 'end_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }


# Guardrails (CEO review, Section 3): closes the CSV-upload attack surface
# that doesn't exist anywhere else in this codebase today.
CSV_IMPORT_MAX_BYTES = 2 * 1024 * 1024  # 2 MB
CSV_IMPORT_REQUIRED_COLUMNS = [
    'nombre', 'sku', 'codigo_barras', 'categoria', 'brand',
    'precio', 'unidad_medida', 'stock_minimo',
]


class ProductImportForm(forms.Form):
    archivo_csv = forms.FileField(label='Archivo CSV')

    def clean_archivo_csv(self):
        archivo = self.cleaned_data['archivo_csv']
        if not archivo.name.lower().endswith('.csv'):
            raise forms.ValidationError('El archivo debe tener extensión .csv.')
        if archivo.content_type not in ('text/csv', 'application/vnd.ms-excel', 'application/csv'):
            raise forms.ValidationError('El archivo debe ser de tipo CSV.')
        if archivo.size > CSV_IMPORT_MAX_BYTES:
            raise forms.ValidationError('El archivo es demasiado grande (máximo 2 MB).')
        return archivo
