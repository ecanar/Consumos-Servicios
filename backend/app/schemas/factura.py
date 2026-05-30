from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class FacturaOut(BaseModel):
    id: int
    proveedor: str
    tipo_servicio: str
    nro_factura: Optional[str]
    cliente_nombre: Optional[str]
    cuenta: Optional[str]
    medidor: Optional[str]
    fecha_emision: Optional[date]
    periodo_desde: Optional[date]
    periodo_hasta: Optional[date]
    lectura_anterior: Optional[float]
    lectura_actual: Optional[float]
    consumo_kwh: Optional[float]
    monto_total: Optional[float]
    moneda: str
    nombre_archivo: str
    hash_archivo: str
    estado: str
    error_extraccion: Optional[str]
    creado_en: Optional[datetime]

    class Config:
        from_attributes = True


class UploadResultado(BaseModel):
    archivo: str
    estado: str
    mensaje: str
    factura: Optional[FacturaOut] = None
