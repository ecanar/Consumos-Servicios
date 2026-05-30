import re
import hashlib
import pdfplumber
from datetime import datetime, date
from typing import Optional, Tuple
from pathlib import Path

# Mapa de normalización de nombres de clientes
MAPA_CLIENTES = {
    "arelis barzola": "Arelis Barzola",
    "arianna canar": "Arianna Canar",
    "daniel canar": "Daniel Canar",
    "edgar canar": "Sam7",  # Reemplazo Sam7
    "sam7": "Sam7",
    "nena tello": "Nena Tello",
    "p.fino": "P.Fino",
    "v.club": "V.Club",
    "wong": "Wong",
}

def normalizar_texto(texto: str) -> str:
    texto = re.sub(r"\s+", " ", texto.strip())
    texto = re.sub(r"[\\/:*?\"<>|]", "-", texto)
    return texto

def normalizar_cliente(nombre: str) -> str:
    if not nombre:
        return "Desconocido"
    nombre_limpio = nombre.strip().lower()
    for k, v in MAPA_CLIENTES.items():
        if k in nombre_limpio:
            return v
    return nombre.strip()

def sha256_bytes(content: bytes) -> str:
    hasher = hashlib.sha256()
    hasher.update(content)
    return hasher.hexdigest()

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

def parse_cliente_desde_nombre(nombre: str) -> str:
    m = re.match(r"Cnel\s+(.+?)\s+\d+\s+\d{4}-\d{2}-\d{2}", nombre, re.IGNORECASE)
    if m:
        return normalizar_cliente(m.group(1))

    m = re.match(r"Cnel\s+(.+?)\s+\d{2}-\d{2}-\d{4}", nombre, re.IGNORECASE)
    if not m:
        return "Desconocido"
    return normalizar_cliente(m.group(1))

def normalizar_numero(valor: str) -> Optional[float]:
    if not valor:
        return None
    if "," in valor:
        return float(valor.replace(".", "").replace(",", "."))
    return float(valor)

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

    # Consumo kWh con todos los fallbacks robustos
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

def extraer_datos_pdf_bytes(pdf_bytes: bytes, filename: str) -> dict:
    datos = {
        "proveedor": "CNEL",
        "tipo_servicio": "electricidad",
        "moneda": "USD",
        "estado": "ok",
    }

    # Intentar sacar datos del nombre del archivo primero
    fecha_str = parse_fecha_dd_mm_yyyy(filename)
    if fecha_str:
        datos["fecha_emision"] = date.fromisoformat(fecha_str)
    
    monto = parse_monto(filename)
    if monto is not None:
        datos["monto_total"] = monto

    cliente = parse_cliente_desde_nombre(filename)
    if cliente and cliente != "Desconocido":
        datos["cliente_nombre"] = cliente

    # Leer texto del PDF
    texto = ""
    try:
        with pdfplumber.open(BytesIO(pdf_bytes) if hasattr(pdf_bytes, "read") else pdfplumber.open(pdf_bytes)) as pdf:
            texto = "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception:
        pass

    import io
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            texto = "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception:
        pass

    if texto:
        pdf_datos = parse_pdf_text(texto)
        datos.update({k: v for k, v in pdf_datos.items() if v is not None})

    # Si falta cliente en los datos, sacarlo por medidor o cuenta, o mapearlo
    if "cuenta" in datos and ("cliente_nombre" not in datos or datos["cliente_nombre"] == "Desconocido"):
        # Mapeo estático de fallback
        cuenta_map = {
            "200023374552": "Sam7",
            "201005848696": "Arelis Barzola",
            "201005857978": "Arianna Canar",
            "200023485721": "Daniel Canar",
            "200022897082": "Nena Tello",
            "201011719725": "P.Fino",
            "200045321631": "V.Club",
            "200023183888": "Wong",
        }
        datos["cliente_nombre"] = cuenta_map.get(datos["cuenta"], "Desconocido")

    # Validar campos requeridos
    faltantes = [campo for campo in ["fecha_emision", "monto_total", "cuenta", "nro_factura"] if not datos.get(campo)]
    if faltantes:
        datos["estado"] = "incompleto"
        datos["error_extraccion"] = f"Campos faltantes: {', '.join(faltantes)}"

    return datos

def nombre_sugerido(datos: dict) -> str:
    fecha = datos.get("fecha_emision")
    fecha_str = fecha.isoformat() if isinstance(fecha, (date, datetime)) else "0000-00-00"
    cliente = datos.get("cliente_nombre") or "Cliente_desconocido"
    cuenta = datos.get("cuenta") or "SIN_CUENTA"
    monto = datos.get("monto_total")
    monto_txt = f"${monto:.2f}" if isinstance(monto, float) else "$SIN_MONTO"
    partes = ["Cnel", normalizar_texto(cliente), normalizar_texto(cuenta), fecha_str, monto_txt]
    return " ".join(partes) + ".pdf"
