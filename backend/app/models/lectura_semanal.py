from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey

from app.db.session import Base

class LecturaSemanal(Base):
    __tablename__ = "lecturas_semanales"

    id = Column(Integer, primary_key=True, index=True)
    cuenta = Column(String, index=True, nullable=False)
    fecha_lectura = Column(Date, nullable=False)
    valor_lectura = Column(Float, nullable=False)
    
    # Cálculos automáticos de intervalo
    dias_transcurridos = Column(Integer, nullable=True)
    consumo_periodo = Column(Float, nullable=True)
    promedio_diario = Column(Float, nullable=True)
    
    # Comparación analítica contra históricos
    promedio_diario_historico = Column(Float, nullable=True)
    desviacion_porcentaje = Column(Float, nullable=True)
    alerta_estado = Column(String, default="ok")  # ok, precaucion, alerta
    
    # Registro de foto como evidencia
    foto_nombre = Column(String, nullable=True)
    
    creado_en = Column(DateTime, default=datetime.utcnow)
