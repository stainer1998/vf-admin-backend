import hashlib
import json

from django.db import IntegrityError, transaction
from pydantic import ValidationError

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


def _valor(campo) -> str:
    """Extrae el valor de un CampoManual (dict con 'valor') o string directo."""
    if campo is None:
        return ""
    if isinstance(campo, dict):
        return campo.get("valor", "") or ""
    return str(campo)


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
