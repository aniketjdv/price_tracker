from django import forms

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import PriceAlert, Product


class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["first_name", "email", "username", "password1", "password2"]


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name",
            "category",
            "platform",
            "current_price",
            "original_price",
            "lowest_price",
            "discount",
            "trend",
            "trend_pct",
            "stock",
            "rating",
            "reviews",
            "image_url",
            "url",
            "description",
            "prediction",
            "wishlisted",
            "tracked",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
            "prediction": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "platform": forms.Select(attrs={"class": "form-select"}),
            "trend": forms.Select(attrs={"class": "form-select"}),
            "stock": forms.Select(attrs={"class": "form-select"}),
            "wishlisted": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "tracked": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "current_price": forms.NumberInput(attrs={"class": "form-control"}),
            "original_price": forms.NumberInput(attrs={"class": "form-control"}),
            "lowest_price": forms.NumberInput(attrs={"class": "form-control"}),
            "discount": forms.NumberInput(attrs={"class": "form-control"}),
            "trend_pct": forms.NumberInput(attrs={"class": "form-control"}),
            "rating": forms.NumberInput(attrs={"class": "form-control"}),
            "reviews": forms.NumberInput(attrs={"class": "form-control"}),
            "image_url": forms.URLInput(attrs={"class": "form-control"}),
            "url": forms.URLInput(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name not in ["description", "prediction", "category", "platform", "trend", "stock", "wishlisted", "tracked", "current_price", "original_price", "lowest_price", "discount", "trend_pct", "rating", "reviews", "image_url", "url", "name"]:
                field.widget.attrs.setdefault("class", "form-control")


class PriceAlertForm(forms.ModelForm):
    class Meta:
        model = PriceAlert
        fields = ["product", "target_price", "email_on", "sms_on"]
        widgets = {
            "product": forms.Select(attrs={"class": "form-select"}),
            "target_price": forms.NumberInput(attrs={"class": "form-control"}),
        }
