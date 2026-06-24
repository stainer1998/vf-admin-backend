from django.db import migrations

COMPONENT_CATEGORIES = [
    (
        "Procesador",
        [
            {"key": "marca",   "label": "Marca",            "type": "select", "options": ["Intel", "AMD", "Apple"], "required": False},
            {"key": "modelo",  "label": "Modelo",            "type": "text",   "required": False},
            {"key": "nucleos", "label": "Núcleos físicos",   "type": "number", "required": False},
            {"key": "ghz",     "label": "Frecuencia (GHz)",  "type": "number", "required": False},
        ],
    ),
    (
        "Memoria RAM",
        [
            {"key": "capacidad_gb",  "label": "Capacidad (GB)",  "type": "number", "required": True},
            {"key": "tipo",          "label": "Tipo",            "type": "select", "options": ["DDR3", "DDR4", "DDR5"], "required": False},
            {"key": "velocidad_mhz", "label": "Velocidad (MHz)", "type": "number", "required": False},
            {"key": "formato",       "label": "Formato",         "type": "select", "options": ["DIMM", "SO-DIMM"], "required": False},
        ],
    ),
    (
        "Almacenamiento",
        [
            {"key": "capacidad_gb", "label": "Capacidad (GB)",  "type": "number", "required": True},
            {"key": "tipo",         "label": "Tipo",            "type": "select", "options": ["HDD", "SSD", "NVMe"], "required": True},
            {"key": "interfaz",     "label": "Interfaz",        "type": "select", "options": ["SATA", "NVMe (M.2)", "IDE", "USB"], "required": False},
            {"key": "marca",        "label": "Marca",           "type": "text",   "required": False},
            {"key": "modelo",       "label": "Modelo",          "type": "text",   "required": False},
            {"key": "rpm",          "label": "RPM (HDD)",       "type": "select", "options": ["5400", "7200"], "required": False},
            {"key": "factor_forma", "label": "Factor de forma", "type": "select", "options": ['2.5"', '3.5"', "M.2 2280", "M.2 2242"], "required": False},
        ],
    ),
    (
        "Tarjeta Gráfica",
        [
            {"key": "marca",   "label": "Marca",     "type": "select", "options": ["NVIDIA", "AMD", "Intel"], "required": False},
            {"key": "modelo",  "label": "Modelo",    "type": "text",   "required": False},
            {"key": "vram_gb", "label": "VRAM (GB)", "type": "number", "required": False},
        ],
    ),
    (
        "Sistema Operativo",
        [
            {"key": "nombre",  "label": "Nombre del SO", "type": "text", "required": False},
            {"key": "version", "label": "Versión",       "type": "text", "required": False},
        ],
    ),
    (
        "Batería",
        [
            {"key": "capacidad_mah",  "label": "Capacidad (mAh)",  "type": "number", "required": False},
            {"key": "voltaje",        "label": "Voltaje (V)",      "type": "number", "required": False},
            {"key": "celdas",         "label": "Número de celdas", "type": "number", "required": False},
            {"key": "compatibilidad", "label": "Compatibilidad",   "type": "text",   "required": False},
        ],
    ),
]


def seed_categories(apps, schema_editor):
    ProductCategory = apps.get_model("inventario", "ProductCategory")
    for name, spec_schema in COMPONENT_CATEGORIES:
        cat, created = ProductCategory.objects.get_or_create(
            name=name,
            defaults={
                "is_equipment_component": True,
                "spec_schema": spec_schema,
            },
        )
        if not created:
            update_fields = []
            if not cat.is_equipment_component:
                cat.is_equipment_component = True
                update_fields.append("is_equipment_component")
            if not cat.spec_schema:
                cat.spec_schema = spec_schema
                update_fields.append("spec_schema")
            if update_fields:
                cat.save(update_fields=update_fields)


def unseed_categories(apps, schema_editor):
    # Solo desmarca el flag; no elimina las categorías (pueden tener productos asociados)
    ProductCategory = apps.get_model("inventario", "ProductCategory")
    names = [name for name, _ in COMPONENT_CATEGORIES]
    ProductCategory.objects.filter(name__in=names).update(is_equipment_component=False)


class Migration(migrations.Migration):

    dependencies = [
        ("inventario", "0010_productcategory_is_equipment_component"),
    ]

    operations = [
        migrations.RunPython(seed_categories, reverse_code=unseed_categories),
    ]
