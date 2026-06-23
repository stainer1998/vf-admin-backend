from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0007_alter_inventorymovement_unit_cost_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='productcategory',
            name='spec_schema',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='product',
            name='specifications',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
