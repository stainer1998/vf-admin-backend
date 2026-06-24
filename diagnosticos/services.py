import hashlib
import json

from django.db import IntegrityError, transaction

from clientes.models import Client
from equipos.models import Equipment
from vf_core.normalize import normalize
from vf_core.schemas.diagnostico import DiagnosticoLookout

from .models import DetectedSpecification, Diagnosis, StorageDevice

EQUIPO_TYPE_MAP = {
    "notebook": Equipment.NOTEBOOK,
    "desktop_marca": Equipment.DESKTOP,
    "desktop_ensamblado": Equipment.DESKTOP,
    "aio": Equipment.AIO,
    "minipc": Equipment.MINIPC,
}

DISCO_CATEGORY_MAP = {
    "disco_interno": StorageDevice.INTERNAL_DISK,
    "lector_optico": StorageDevice.OPTICAL_DRIVE,
}

DISCO_TYPE_MAP = {
    "SSD": StorageDevice.SSD,
    "HDD": StorageDevice.HDD,
}

INTERFACE_MAP = {
    "sata": StorageDevice.SATA,
    "nvme": StorageDevice.NVME,
    "usb": StorageDevice.USB,
    "ide": StorageDevice.IDE,
}

_KNOWN_STORAGE_BRANDS = [
    "Samsung", "Seagate", "WD", "Western Digital", "Kingston",
    "Crucial", "Toshiba", "Hitachi", "SanDisk", "Micron", "HGST",
]

_CATEGORY_SPECS = {
    "CPU": [
        {"key": "marca",   "label": "Marca",            "type": "select", "options": ["Intel", "AMD", "Apple"], "required": False},
        {"key": "modelo",  "label": "Modelo",            "type": "text",   "required": False},
        {"key": "nucleos", "label": "Núcleos físicos",   "type": "number", "required": False},
        {"key": "ghz",     "label": "Frecuencia (GHz)",  "type": "number", "required": False},
    ],
    "RAM": [
        {"key": "capacidad_gb",  "label": "Capacidad (GB)",  "type": "number", "required": True},
        {"key": "tipo",          "label": "Tipo",            "type": "select", "options": ["DDR3", "DDR4", "DDR5"], "required": False},
        {"key": "velocidad_mhz", "label": "Velocidad (MHz)", "type": "number", "required": False},
        {"key": "formato",       "label": "Formato",         "type": "select", "options": ["DIMM", "SO-DIMM"], "required": False},
    ],
    "STORAGE": [
        {"key": "capacidad_gb", "label": "Capacidad (GB)",  "type": "number", "required": True},
        {"key": "tipo",         "label": "Tipo",            "type": "select", "options": ["HDD", "SSD", "NVMe"], "required": True},
        {"key": "interfaz",     "label": "Interfaz",        "type": "select", "options": ["SATA", "NVMe (M.2)", "IDE", "USB"], "required": False},
        {"key": "marca",        "label": "Marca",           "type": "text",   "required": False},
        {"key": "modelo",       "label": "Modelo",          "type": "text",   "required": False},
        {"key": "rpm",          "label": "RPM (HDD)",       "type": "select", "options": ["5400", "7200"], "required": False},
        {"key": "factor_forma", "label": "Factor de forma", "type": "select", "options": ['2.5"', '3.5"', "M.2 2280", "M.2 2242"], "required": False},
    ],
    "GPU": [
        {"key": "marca",   "label": "Marca",    "type": "select", "options": ["NVIDIA", "AMD", "Intel"], "required": False},
        {"key": "modelo",  "label": "Modelo",   "type": "text",   "required": False},
        {"key": "vram_gb", "label": "VRAM (GB)", "type": "number", "required": False},
    ],
    "OS": [
        {"key": "nombre",  "label": "Nombre del SO", "type": "text", "required": False},
        {"key": "version", "label": "Versión",       "type": "text", "required": False},
    ],
    "BATTERY": [
        {"key": "capacidad_mah",  "label": "Capacidad (mAh)",  "type": "number", "required": False},
        {"key": "voltaje",        "label": "Voltaje (V)",      "type": "number", "required": False},
        {"key": "celdas",         "label": "Número de celdas", "type": "number", "required": False},
        {"key": "compatibilidad", "label": "Compatibilidad",   "type": "text",   "required": False},
    ],
}


def _detect_brand(nombre: str, brands: list) -> str:
    nombre_up = nombre.upper()
    for b in brands:
        if b.upper() in nombre_up:
            return b
    return ""


def _valor(campo) -> str:
    """Extrae el valor de un CampoManual (dict con 'valor') o string directo."""
    if campo is None:
        return ""
    if isinstance(campo, dict):
        return campo.get("valor", "") or ""
    return str(campo)


def _ensure_categories(specs: dict, equip_type: str) -> dict:
    """
    Crea las categorías de componentes de equipo si no existen.
    Devuelve un dict {spec_key: ProductCategory} para su uso en auto-populate.
    """
    from inventario.models import ProductCategory

    ram = specs.get("ram") or {}
    first_slot = (ram.get("slots") or [{}])[0]
    ram_tipo = (first_slot.get("tipo") or "").upper()

    to_create = [
        ("Procesador", "CPU"),
        ("Memoria RAM", "RAM"),
        ("Almacenamiento", "STORAGE"),
        ("Tarjeta Gráfica", "GPU"),
        ("Sistema Operativo", "OS"),
    ]
    if equip_type == Equipment.NOTEBOOK:
        to_create.append(("Batería", "BATTERY"))

    result = {}
    for name, spec_key in to_create:
        cat, _ = ProductCategory.objects.get_or_create(
            name=name,
            defaults={
                "spec_schema": _CATEGORY_SPECS[spec_key],
                "is_equipment_component": True,
            },
        )
        # Marcar como componente si fue creada manualmente sin el flag
        if not cat.is_equipment_component:
            cat.is_equipment_component = True
            cat.save(update_fields=["is_equipment_component"])
        result[spec_key] = cat

    return result


def _populate_specs(equipment, specs: dict, equip_type: str, cat_map: dict) -> None:
    """
    Rellena equipment.specifications con datos del JSON de lookout.
    Solo rellena claves que no existan (fill-in: preserva edición manual).
    """
    existing = dict(equipment.specifications or {})

    ram = specs.get("ram") or {}
    cpu = specs.get("cpu") or {}
    gpu = specs.get("gpu") or {}
    so = specs.get("sistema_operativo") or {}
    first_slot = (ram.get("slots") or [{}])[0]
    ram_tipo = (first_slot.get("tipo") or "").upper()

    primary_disk = next(
        (d for d in specs.get("almacenamiento", [])
         if d.get("categoria") == "disco_interno" and d.get("capacidad_nominal_gb")),
        None,
    )

    updates = {}

    # CPU
    if "CPU" in cat_map:
        cat_id = str(cat_map["CPU"].id)
        if cat_id not in existing:
            cpu_nombre = cpu.get("nombre", "")
            freq = cpu.get("frecuencia_mhz")
            updates[cat_id] = {
                "marca":   _detect_brand(cpu_nombre, ["Intel", "AMD", "Apple"]),
                "modelo":  cpu_nombre,
                "nucleos": int(cpu["nucleos_fisicos"]) if cpu.get("nucleos_fisicos") else None,
                "ghz":     round(freq / 1000, 2) if freq else None,
            }

    # RAM
    if "RAM" in cat_map:
        cat_id = str(cat_map["RAM"].id)
        if cat_id not in existing:
            total = ram.get("total_gb")
            updates[cat_id] = {
                "capacidad_gb":  int(total) if total is not None else None,
                "tipo":          ram_tipo if ram_tipo in ("DDR3", "DDR4", "DDR5") else None,
                "velocidad_mhz": int(first_slot["velocidad_mhz"]) if first_slot.get("velocidad_mhz") else None,
            }

    # Almacenamiento
    if "STORAGE" in cat_map and primary_disk:
        cat_id = str(cat_map["STORAGE"].id)
        if cat_id not in existing:
            raw_modelo = primary_disk.get("modelo_crudo", "")
            interfaz = primary_disk.get("interfaz", "").lower()
            raw_tipo = primary_disk.get("tipo", "")
            disk_tipo = "NVMe" if interfaz == "nvme" else {"SSD": "SSD", "HDD": "HDD"}.get(raw_tipo, "")
            updates[cat_id] = {
                "capacidad_gb": int(primary_disk["capacidad_nominal_gb"]),
                "tipo":         disk_tipo or None,
                "interfaz":     primary_disk.get("interfaz", "").upper() or None,
                "marca":        _detect_brand(raw_modelo, _KNOWN_STORAGE_BRANDS) or None,
                "modelo":       raw_modelo or None,
            }

    # GPU
    if "GPU" in cat_map:
        cat_id = str(cat_map["GPU"].id)
        if cat_id not in existing:
            gpu_nombre = gpu.get("nombre", "") if gpu else ""
            if gpu_nombre:
                updates[cat_id] = {
                    "marca":   _detect_brand(gpu_nombre, ["NVIDIA", "AMD", "Intel"]),
                    "modelo":  gpu_nombre,
                    "vram_gb": int(gpu["vram_gb"]) if gpu and gpu.get("vram_gb") else None,
                }

    # Sistema Operativo
    if "OS" in cat_map:
        cat_id = str(cat_map["OS"].id)
        if cat_id not in existing:
            nombre_so = so.get("nombre", "")
            if nombre_so:
                updates[cat_id] = {
                    "nombre":  nombre_so,
                    "version": so.get("version", ""),
                }

    if updates:
        equipment.specifications = {**existing, **updates}
        equipment.save(update_fields=["specifications"])


def import_lookout_json(data: dict, user) -> tuple[Diagnosis, bool]:
    """
    Importa un JSON generado por vf-lookout.

    Hace find-or-create de Client y Equipment usando identity_key,
    crea el Diagnosis con su DetectedSpecification y StorageDevices.

    Returns (diagnosis, created) — created=False si el content_hash ya existía.
    Raises pydantic.ValidationError si el JSON no cumple el schema.
    """
    DiagnosticoLookout.model_validate(data)

    cliente_data = data["cliente"]
    equipo_data = data["equipo"]
    specs = data.get("specs", {})

    # --- Client ---
    tipo = cliente_data.get("tipo", "persona")
    client_type = Client.PERSON if tipo == "persona" else Client.COMPANY

    first_name = _valor(cliente_data.get("nombre"))
    last_name = _valor(cliente_data.get("primer_apellido"))
    second_last_name = _valor(cliente_data.get("segundo_apellido"))
    phone = _valor(cliente_data.get("telefono"))
    email = cliente_data.get("email") or ""
    rut = cliente_data.get("rut") or ""
    company_name = cliente_data.get("razon_social") or ""
    address = cliente_data.get("direccion") or ""
    notes = cliente_data.get("observaciones") or ""

    if client_type == Client.COMPANY:
        client_key = rut.strip() if rut else normalize(company_name)
    else:
        client_key = normalize(f"{first_name} {last_name} {second_last_name}")

    client, _ = Client.all_objects.get_or_create(
        identity_key=client_key,
        defaults={
            "type": client_type,
            "first_name": first_name,
            "last_name": last_name,
            "second_last_name": second_last_name,
            "phone": phone,
            "email": email,
            "rut": rut,
            "company_name": company_name,
            "address": address,
            "notes": notes,
            "source": Client.LOOKOUT,
        },
    )

    # --- Equipment ---
    equipo_tipo = equipo_data.get("tipo", "notebook")
    equip_type = EQUIPO_TYPE_MAP.get(equipo_tipo, Equipment.DESKTOP)

    if equipo_tipo == "desktop_ensamblado":
        brand = "Ensamblado"
        model = _valor(equipo_data.get("placa_madre")) or "Ensamblado"
        serial_number = ""
        year = None
        desktop_subtype = Equipment.ASSEMBLED
    else:
        brand = _valor(equipo_data.get("marca"))
        model = _valor(equipo_data.get("modelo"))
        serial_number = _valor(equipo_data.get("numero_serie"))
        ano_campo = equipo_data.get("ano")
        ano_str = _valor(ano_campo)
        year = int(ano_str) if ano_str and ano_str.isdigit() else None
        desktop_subtype = Equipment.BRAND if equipo_tipo == "desktop_marca" else ""

    equip_key = normalize(serial_number) if serial_number else normalize(f"{brand} {model}")

    equipment, _ = Equipment.all_objects.get_or_create(
        identity_key=equip_key,
        defaults={
            "client": client,
            "type": equip_type,
            "desktop_subtype": desktop_subtype,
            "brand": brand,
            "model": model,
            "serial_number": serial_number,
            "year": year,
        },
    )

    # --- Diagnosis (savepoint anidado — captura hash duplicado sin romper la tx) ---
    content_hash = hashlib.sha256(
        json.dumps(data, sort_keys=True).encode()
    ).hexdigest()

    with transaction.atomic():
        try:
            with transaction.atomic():  # savepoint: si falla, solo revierte esto
                diagnosis = Diagnosis.objects.create(
                    equipment=equipment,
                    timestamp=data.get("timestamp_inicio"),
                    source_file=data.get("archivo_origen", ""),
                    schema_version=data.get("version_schema", ""),
                    raw_json=data,
                    ingress_source=Diagnosis.LOOKOUT,
                    imported_by=user,
                )
        except IntegrityError:
            existing = Diagnosis.objects.get(content_hash=content_hash)
            return existing, False

        # --- DetectedSpecification ---
        so = specs.get("sistema_operativo") or {}
        cpu = specs.get("cpu") or {}
        ram = specs.get("ram") or {}
        gpu = specs.get("gpu") or {}

        DetectedSpecification.objects.create(
            diagnosis=diagnosis,
            os_name=so.get("nombre", ""),
            os_version=so.get("version", ""),
            cpu_model=cpu.get("nombre", ""),
            ram_total_gb=ram.get("total_gb"),
            gpu_model=gpu.get("nombre", "") if gpu else "",
        )

        # --- Auto-create component categories + populate equipment specs ---
        cat_map = _ensure_categories(specs, equip_type)
        _populate_specs(equipment, specs, equip_type, cat_map)

        # --- StorageDevices ---
        for disco in specs.get("almacenamiento", []):
            categoria = disco.get("categoria", "disco_interno")
            es_interno = categoria == "disco_interno"
            StorageDevice.objects.create(
                diagnosis=diagnosis,
                category=DISCO_CATEGORY_MAP.get(categoria, StorageDevice.INTERNAL_DISK),
                disk_type=DISCO_TYPE_MAP.get(disco.get("tipo", ""), StorageDevice.DISK_OTHER) if es_interno else "",
                interface=INTERFACE_MAP.get(disco.get("interfaz", ""), StorageDevice.INTERFACE_OTHER) if es_interno else "",
                capacity_gb=disco.get("capacidad_nominal_gb"),
                raw_model=disco.get("modelo_crudo", ""),
            )

        return diagnosis, True
