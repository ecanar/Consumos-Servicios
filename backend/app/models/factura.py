from sqlalchemy import Column, Date, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func

from app.db.session import Base


class Factura(Base):
    __tablename__ = "facturas"

    id = Column(Integer, primary_key=True, index=True)
    proveedor = Column(String, index=True, nullable=False, default="CNEL")
    tipo_servicio = Column(String, index=True, nullable=False, default="electricidad")
    nro_factura = Column(String, unique=True, index=True, nullable=True)
    cliente_nombre = Column(String, index=True, nullable=True)
    cuenta = Column(String, index=True, nullable=True)
    medidor = Column(String, nullable=True)
    fecha_emision = Column(Date, index=True, nullable=True)
    periodo_desde = Column(Date, nullable=True)
    periodo_hasta = Column(Date, nullable=True)
    lectura_anterior = Column(Float, nullable=True)
    lectura_actual = Column(Float, nullable=True)
    consumo_kwh = Column(Float, nullable=True)
    monto_total = Column(Float, nullable=True)
    moneda = Column(String, nullable=False, default="USD")
    nombre_archivo = Column(String, nullable=False)
    hash_archivo = Column(String, unique=True, index=True, nullable=False)
    estado = Column(String, index=True, nullable=False, default="ok")
    error_extraccion = Column(Text, nullable=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
