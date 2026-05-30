import argparse
import csv
import hashlib
import json
import re
import shutil
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import pdfplumber
except ImportError:
    pdfplumber = None


MONEDA = "USD"
PROVEEDOR = "CNEL"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_fecha_dd_mm_yyyy(texto: str) -> Optional[str]:
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", texto)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    m = re.search(r"(\d{2})-(\d{2})-(\d{4})", texto)
    if not m:
        return None
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"


def parse_monto(texto: str) -> Optional[float]:
    m = re.search(r"\$\s*(-?[0-9]+(?:[\.,][0-9]{1,2})?)", texto)
    if not m:
        return None
    return float(m.group(1).replace(",", "."))


def parse_cliente_desde_nombre(nombre: str) -> Optional[str]:
    m = re.match(r"Cnel\s+(.+?)\s+\d+\s+\d{4}-\d{2}-\d{2}", nombre, re.IGNORECASE)
    if m:
        return normalizar_texto(m.group(1))

    m = re.match(r"Cnel\s+(.+?)\s+\d{2}-\d{2}-\d{4}", nombre, re.IGNORECASE)
    if not m:
        return None
    return normalizar_texto(m.group(1))


def normalizar_texto(texto: str) -> str:
    texto = re.sub(r"\s+", " ", texto.strip())
    texto = re.sub(r"[\\/:*?\"<>|]", "-", texto)
    return texto


def extraer_texto_pdf(path: Path) -> str:
    if pdfplumber is None:
        return ""
    try:
        with pdfplumber.open(path) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception:
        return ""


def parse_pdf_text(texto: str) -> dict:
    datos = {}

    for pat in [r"Nro\.\s*Factura\s+([\d\-]+)", r"Factura\s+No\.\s+([\d\-]+)"]:
        m = re.search(pat, texto, re.IGNORECASE)
        if m:
            datos["nro_factura"] = m.group(1).strip()
            break

    m = re.search(r"Cuenta\s+contrato[:\s]+([\d]+)", texto, re.IGNORECASE)
    if not m:
        m = re.search(r"CUENTA\s+CONTRATO\s+([\d]+)", texto)
    if m:
        datos["cuenta"] = m.group(1).strip()

    m = re.search(r"(?:N[uú]mero\s+de\s+medidor|Medidor)[:\s]+([\w\-]+)", texto, re.IGNORECASE)
    if m:
        datos["medidor"] = m.group(1).strip()

    m = re.search(r"Energ[ií]a\s+activa\s+([\d\.,]+)\s+([\d\.,]+)\s+([\d\.,]+)\s+kWh", texto, re.IGNORECASE)
    if m:
        datos["lectura_actual"] = normalizar_numero(m.group(1))
        datos["lectura_anterior"] = normalizar_numero(m.group(2))
        datos["consumo_kwh"] = normalizar_numero(m.group(3))
    else:
        m = re.search(r"Energ[ií]a\s+activa\s+total\s+\S+\s+(.+?)\s+[Kk][Ww][Hh]", texto, re.IGNORECASE)
        if m:
            nums = re.findall(r"[\d\.,]+", m.group(1))
            if len(nums) >= 3:
                datos["lectura_actual"] = normalizar_numero(nums[0])
                datos["lectura_anterior"] = normalizar_numero(nums[1])
                datos["consumo_kwh"] = normalizar_numero(nums[-1])
        else:
            m = re.search(r"Eng\.\s+Activa\s+([\d\.,]+)\s+([\d\.,]+)\s+([\d\.,]+)\s+kWh", texto, re.IGNORECASE)
            if m:
                datos["lectura_actual"] = normalizar_numero(m.group(1))
                datos["lectura_anterior"] = normalizar_numero(m.group(2))
                datos["consumo_kwh"] = normalizar_numero(m.group(3))

    return datos


def normalizar_numero(valor: str) -> Optional[float]:
    if not valor:
        return None
    if "," in valor:
        return float(valor.replace(".", "").replace(",", "."))
    return float(valor)


def nombre_sugerido(datos: dict) -> str:
    fecha = datos.get("fecha_emision") or "0000-00-00"
    cliente = datos.get("cliente_nombre") or "Cliente_desconocido"
    cuenta = datos.get("cuenta") or "SIN_CUENTA"
    monto = datos.get("monto_total")
    monto_txt = f"${monto:.2f}" if isinstance(monto, float) else "$SIN_MONTO"
    partes = ["Cnel", normalizar_texto(cliente), normalizar_texto(cuenta), fecha, monto_txt]
    return " ".join(partes) + ".pdf"


def ruta_destino_unica(destino: Path, row: dict) -> Path:
    anio = row.get("anio_destino") or "sin_fecha"
    carpeta = destino / "CNEL" / anio
    carpeta.mkdir(parents=True, exist_ok=True)
    base = carpeta / row["nombre_sugerido"]
    if not base.exists():
        return base

    stem = base.stem
    suffix = base.suffix
    idx = 2
    while True:
        candidata = carpeta / f"{stem} - {idx}{suffix}"
        if not candidata.exists():
            return candidata
        idx += 1


def analizar_pdf(path: Path) -> dict:
    datos = {
        "archivo_actual": path.name,
        "ruta_actual": str(path),
        "extension": path.suffix.lower(),
        "tamano_bytes": path.stat().st_size,
        "hash_archivo": sha256_file(path),
        "proveedor": PROVEEDOR,
        "tipo_servicio": "electricidad",
    }

    datos["fecha_emision"] = parse_fecha_dd_mm_yyyy(path.name)
    datos["monto_total"] = parse_monto(path.name)
    datos["cliente_nombre"] = parse_cliente_desde_nombre(path.name)

    texto = extraer_texto_pdf(path)
    if texto:
        datos.update({k: v for k, v in parse_pdf_text(texto).items() if v is not None})

    faltantes = [campo for campo in ["fecha_emision", "monto_total", "cuenta", "nro_factura"] if not datos.get(campo)]
    datos["estado"] = "ok" if not faltantes else "incompleto"
    datos["faltantes"] = ",".join(faltantes)
    datos["nombre_sugerido"] = nombre_sugerido(datos)
    datos["anio_destino"] = datos["fecha_emision"][:4] if datos.get("fecha_emision") else "sin_fecha"
    return datos


def main() -> int:
    parser = argparse.ArgumentParser(description="Analiza facturas CNEL PDF sin modificar archivos.")
    parser.add_argument("origen", help="Carpeta origen con PDFs")
    parser.add_argument("--salida", default="reports/reporte_facturas_cnel", help="Ruta base del reporte sin extensión")
    parser.add_argument("--copiar-unicos", help="Copia una sola factura por hash al destino indicado")
    args = parser.parse_args()

    origen = Path(args.origen).expanduser().resolve()
    if not origen.exists() or not origen.is_dir():
        print(f"Carpeta origen no válida: {origen}", file=sys.stderr)
        return 1

    salida_base = Path(args.salida)
    if not salida_base.is_absolute():
        salida_base = Path.cwd() / salida_base
    salida_base.parent.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(origen.rglob("*.pdf"))
    resultados = [analizar_pdf(pdf) for pdf in pdfs]

    por_hash = defaultdict(list)
    por_factura = defaultdict(list)
    for row in resultados:
        por_hash[row["hash_archivo"]].append(row)
        if row.get("nro_factura"):
            por_factura[row["nro_factura"]].append(row)

    for row in resultados:
        row["duplicado_hash"] = "si" if len(por_hash[row["hash_archivo"]]) > 1 else "no"
        row["duplicado_nro_factura"] = "si" if row.get("nro_factura") and len(por_factura[row["nro_factura"]]) > 1 else "no"
        row["accion"] = "pendiente"
        row["ruta_destino"] = ""

    copiados = 0
    omitidos_por_duplicado = 0
    if args.copiar_unicos:
        destino = Path(args.copiar_unicos).expanduser().resolve()
        vistos = set()
        for row in resultados:
            if row["hash_archivo"] in vistos:
                row["accion"] = "omitido_duplicado_hash"
                omitidos_por_duplicado += 1
                continue
            vistos.add(row["hash_archivo"])
            destino_pdf = ruta_destino_unica(destino, row)
            shutil.copy2(row["ruta_actual"], destino_pdf)
            row["accion"] = "copiado"
            row["ruta_destino"] = str(destino_pdf)
            copiados += 1

    csv_path = salida_base.with_suffix(".csv")
    json_path = salida_base.with_suffix(".json")

    campos = [
        "estado", "faltantes", "duplicado_hash", "duplicado_nro_factura",
        "accion", "ruta_destino",
        "archivo_actual", "nombre_sugerido", "anio_destino", "fecha_emision",
        "monto_total", "cliente_nombre", "cuenta", "nro_factura", "medidor",
        "consumo_kwh", "lectura_anterior", "lectura_actual", "hash_archivo", "ruta_actual",
    ]

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(resultados)

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)

    resumen = {
        "pdfs_encontrados": len(resultados),
        "ok": sum(1 for r in resultados if r["estado"] == "ok"),
        "incompletos": sum(1 for r in resultados if r["estado"] == "incompleto"),
        "duplicados_hash": sum(1 for r in resultados if r["duplicado_hash"] == "si"),
        "duplicados_nro_factura": sum(1 for r in resultados if r["duplicado_nro_factura"] == "si"),
        "copiados": copiados,
        "omitidos_por_duplicado": omitidos_por_duplicado,
        "csv": str(csv_path),
        "json": str(json_path),
        "generado_en": datetime.now().isoformat(timespec="seconds"),
    }
    print(json.dumps(resumen, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
