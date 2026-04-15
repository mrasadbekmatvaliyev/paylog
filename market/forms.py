from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

from .models import Product


class ImageURLsWidget(forms.Widget):
    template_name = "market/widgets/image_urls_widget.html"

    class Media:
        css = {"all": ("market/admin/image-urls-widget.css",)}
        js = ("market/admin/image-urls-widget.js",)

    def format_value(self, value):
        if not value:
            return []
        if isinstance(value, (list, tuple)):
            return [str(item) for item in value if item]
        return [str(value)]

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["items"] = self.format_value(value)
        context["widget"]["input_name"] = f"{name}_items"
        return context

    def value_from_datadict(self, data, files, name):
        return [item.strip() for item in data.getlist(f"{name}_items") if item.strip()]


class ProductAdminForm(forms.ModelForm):
    image_urls = forms.Field(label="Image url", required=False, widget=ImageURLsWidget())

    class Meta:
        model = Product
        exclude = ["image_url"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.initial["image_urls"] = self.instance.image_urls or ([self.instance.image_url] if self.instance.image_url else [])

    def clean_image_urls(self):
        urls = self.cleaned_data.get("image_urls") or []
        validator = URLValidator()
        cleaned_urls = []

        for url in urls:
            try:
                validator(url)
            except ValidationError as exc:
                raise ValidationError(f"Invalid URL: {url}") from exc
            if url not in cleaned_urls:
                cleaned_urls.append(url)

        return cleaned_urls

    def save(self, commit=True):
        instance = super().save(commit=False)
        image_urls = self.cleaned_data.get("image_urls") or []
        instance.image_urls = image_urls
        instance.image_url = image_urls[0] if image_urls else None
        if commit:
            instance.save()
            self.save_m2m()
        return instance
