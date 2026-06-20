import django.db.models.deletion
from django.db import migrations, models


def migrate_supplier_to_m2m(apps, schema_editor):
    Product = apps.get_model("inventario", "Product")
    ProductSupplier = apps.get_model("inventario", "ProductSupplier")
    for product in Product.objects.filter(supplier__isnull=False).select_related("supplier"):
        ProductSupplier.objects.create(
            product=product,
            supplier=product.supplier,
            purchase_price=None,
            is_preferred=True,
        )


def reverse_migrate(apps, schema_editor):
    Product = apps.get_model("inventario", "Product")
    ProductSupplier = apps.get_model("inventario", "ProductSupplier")
    for ps in ProductSupplier.objects.filter(is_preferred=True).select_related("product", "supplier"):
        ps.product.supplier = ps.supplier
        ps.product.save(update_fields=["supplier"])


class Migration(migrations.Migration):

    dependencies = [
        ("inventario", "0004_brand_product_model_product_brand"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductSupplier",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("purchase_price", models.DecimalField(decimal_places=2, max_digits=10, null=True, blank=True)),
                ("is_preferred", models.BooleanField(default=False)),
                ("notes", models.TextField(blank=True)),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="product_suppliers", to="inventario.product")),
                ("supplier", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="product_suppliers", to="inventario.supplier")),
            ],
            options={"unique_together": {("product", "supplier")}},
        ),
        migrations.AddField(
            model_name="product",
            name="suppliers",
            field=models.ManyToManyField(blank=True, related_name="products", through="inventario.ProductSupplier", to="inventario.Supplier"),
        ),
        migrations.RunPython(migrate_supplier_to_m2m, reverse_migrate),
        migrations.RemoveField(
            model_name="product",
            name="supplier",
        ),
    ]
