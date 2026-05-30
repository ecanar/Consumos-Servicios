from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from pathlib import Path

from app.db.session import get_db
from app.models.factura import Factura
from app.schemas.factura import FacturaOut
from app.core.pdf_parser import extraer_datos_pdf_bytes, sha256_bytes, nombre_sugerido

router = APIRouter()


@router.post("/upload")
async def subir_factura(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # 1. Leer los bytes del archivo
    content = await file.read()
    
    # 2. Calcular el hash SHA256 para evitar duplicidad por hash
    h_archivo = sha256_bytes(content)
    
    # Verificar si el hash ya existe en la base de datos
    factura_existente = db.query(Factura).filter(Factura.hash_archivo == h_archivo).first()
    if factura_existente:
        raise HTTPException(
            status_code=400, 
            detail=f"Esta factura ya ha sido cargada anteriormente (Duplicada por Hash: {factura_existente.nombre_archivo})."
        )
    
    # 3. Extraer los datos del PDF en memoria
    datos = extraer_datos_pdf_bytes(content, file.filename)
    
    # Verificar si ya existe el número de factura para evitar duplicidad por nro_factura
    if datos.get("nro_factura"):
        factura_nro_existente = db.query(Factura).filter(Factura.nro_factura == datos["nro_factura"]).first()
        if factura_nro_existente:
            raise HTTPException(
                status_code=400, 
                detail=f"El número de factura '{datos['nro_factura']}' ya está registrado en la cuenta {factura_nro_existente.cuenta} ({factura_nro_existente.cliente_nombre})."
            )
    
    # 4. Generar el nombre de archivo sugerido normalizado
    nom_sug = nombre_sugerido(datos)
    
    # 5. Guardar el archivo físicamente en la carpeta de destino ordenada
    anio = str(datos.get("fecha_emision").year) if datos.get("fecha_emision") else "sin_fecha"
    destino_dir = Path("data/facturas_ordenadas/CNEL") / anio
    destino_dir.mkdir(parents=True, exist_ok=True)
    
    destino_path = destino_dir / nom_sug
    # Si el archivo con el mismo nombre ya existe, buscar un nombre único agregando - 2, - 3
    if destino_path.exists():
        stem = destino_path.stem
        suffix = destino_path.suffix
        idx = 2
        while True:
            candidata = destino_dir / f"{stem} - {idx}{suffix}"
            if not candidata.exists():
                destino_path = candidata
                break
            idx += 1
            
    # Escribir el archivo
    with open(destino_path, "wb") as f:
        f.write(content)
        
    # 6. Registrar en la base de datos
    nueva_factura = Factura(
        proveedor=datos.get("proveedor", "CNEL"),
        tipo_servicio=datos.get("tipo_servicio", "electricidad"),
        nro_factura=datos.get("nro_factura"),
        cliente_nombre=datos.get("cliente_nombre"),
        cuenta=datos.get("cuenta"),
        medidor=datos.get("medidor"),
        fecha_emision=datos.get("fecha_emision"),
        lectura_anterior=datos.get("lectura_anterior"),
        lectura_actual=datos.get("lectura_actual"),
        consumo_kwh=datos.get("consumo_kwh"),
        monto_total=datos.get("monto_total"),
        moneda=datos.get("moneda", "USD"),
        nombre_archivo=destino_path.name,
        hash_archivo=h_archivo,
        estado=datos.get("estado", "ok"),
        error_extraccion=datos.get("error_extraccion")
    )
    
    db.add(nueva_factura)
    db.commit()
    db.refresh(nueva_factura)
    
    return {
        "status": "ok",
        "factura": {
            "id": nueva_factura.id,
            "cliente_nombre": nueva_factura.cliente_nombre,
            "cuenta": nueva_factura.cuenta,
            "fecha_emision": nueva_factura.fecha_emision,
            "consumo_kwh": nueva_factura.consumo_kwh,
            "monto_total": nueva_factura.monto_total,
            "estado": nueva_factura.estado
        }
    }


@router.get("/", response_model=List[FacturaOut])
def listar_facturas(
    cuenta: Optional[str] = None,
    cliente_nombre: Optional[str] = None,
    estado: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(Factura)
    if cuenta:
        query = query.filter(Factura.cuenta == cuenta)
    if cliente_nombre:
        query = query.filter(Factura.cliente_nombre.ilike(f"%{cliente_nombre}%"))
    if estado:
        query = query.filter(Factura.estado == estado)
    
    return query.order_by(Factura.fecha_emision.desc().nullslast()).offset(skip).limit(limit).all()


@router.get("/cuentas")
def listar_cuentas(db: Session = Depends(get_db)):
    # Retorna las cuentas únicas que tienen al menos un registro de consumo
    cuentas = (
        db.query(Factura.cuenta, Factura.cliente_nombre)
        .filter(Factura.cuenta.isnot(None))
        .group_by(Factura.cuenta)
        .order_by(Factura.cliente_nombre)
        .all()
    )
    return [
        {"cuenta": c[0], "cliente_nombre": c[1] or "Desconocido"}
        for c in cuentas
    ]


@router.get("/{factura_id}", response_model=FacturaOut)
def obtener_factura(factura_id: int, db: Session = Depends(get_db)):
    factura = db.query(Factura).filter(Factura.id == factura_id).first()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    return factura
