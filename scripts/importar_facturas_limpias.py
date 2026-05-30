import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(BACKEND))

from analizar_facturas_cnel import analizar_pdf
from app.db.session import Base, SessionLocal, engine
from app.models.factura import Factura


def normalizar_valor(valor):
    return valor if valor not in ("", None) else None


def normalizar_fecha(valor):
    valor = normalizar_valor(valor)
    if not valor:
        return None
    if isinstance(valor, date):
        return valor
    return date.fromisoformat(valor)


def importar(origen: Path) -> dict:
    (ROOT / "data").mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)

    pdfs = sorted(origen.rglob("*.pdf"))
    db = SessionLocal()
    resumen = {
        "pdfs_encontrados": len(pdfs),
        "insertados": 0,
        "omitidos_duplicado_hash": 0,
        "omitidos_duplicado_nro_factura": 0,
        "errores": [],
    }

    try:
        for pdf in pdfs:
            try:
                datos = analizar_pdf(pdf)
                existe_hash = db.query(Factura).filter(Factura.hash_archivo == datos["hash_archivo"]).first()
                if existe_hash:
                    resumen["omitidos_duplicado_hash"] += 1
                    continue

                nro_factura = normalizar_valor(datos.get("nro_factura"))
                if nro_factura:
                    existe_nro = db.query(Factura).filter(Factura.nro_factura == nro_factura).first()
                    if existe_nro:
                        resumen["omitidos_duplicado_nro_factura"] += 1
                        continue

                factura = Factura(
                    proveedor="CNEL",
                    tipo_servicio="electricidad",
                    nro_factura=nro_factura,
                    cliente_nombre=normalizar_valor(datos.get("cliente_nombre")),
                    cuenta=normalizar_valor(datos.get("cuenta")),
                    medidor=normalizar_valor(datos.get("medidor")),
                    fecha_emision=normalizar_fecha(datos.get("fecha_emision")),
                    periodo_desde=normalizar_fecha(datos.get("periodo_desde")),
                    periodo_hasta=normalizar_fecha(datos.get("periodo_hasta")),
                    lectura_anterior=normalizar_valor(datos.get("lectura_anterior")),
                    lectura_actual=normalizar_valor(datos.get("lectura_actual")),
                    consumo_kwh=normalizar_valor(datos.get("consumo_kwh")),
                    monto_total=normalizar_valor(datos.get("monto_total")),
                    moneda="USD",
                    nombre_archivo=pdf.name,
                    hash_archivo=datos["hash_archivo"],
                    estado=datos.get("estado") or "incompleto",
                    error_extraccion=datos.get("faltantes") or None,
                )
                db.add(factura)
                resumen["insertados"] += 1
            except Exception as exc:
                resumen["errores"].append({"archivo": str(pdf), "error": str(exc)})

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    return resumen


def main() -> int:
    parser = argparse.ArgumentParser(description="Importa facturas limpias CNEL a SQLite.")
    parser.add_argument("origen", help="Carpeta con PDFs limpios/normalizados")
    args = parser.parse_args()

    origen = Path(args.origen).expanduser().resolve()
    if not origen.exists() or not origen.is_dir():
        print(f"Carpeta origen no válida: {origen}", file=sys.stderr)
        return 1

    resumen = importar(origen)
    print(json.dumps(resumen, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
