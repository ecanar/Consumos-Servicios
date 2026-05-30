import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Asegurar que el path del backend esté disponible para importar los modelos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.db.session import Base
from app.models.factura import Factura
from app.models.lectura_semanal import LecturaSemanal

# Ruta de la base SQLite local
SQLITE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "app.db"))
SQLITE_URL = f"sqlite:///{SQLITE_PATH}"

def migrar(postgres_url: str):
    if not postgres_url:
        print("Error: Debes proporcionar la URL externa de PostgreSQL de Railway.")
        return

    # Corregir prefijo postgres:// de Railway si viene así
    if postgres_url.startswith("postgres://"):
        postgres_url = postgres_url.replace("postgres://", "postgresql://", 1)

    print("🔌 Conectando a bases de datos...")
    try:
        engine_sqlite = create_engine(SQLITE_URL)
        SessionSqlite = sessionmaker(bind=engine_sqlite)
        session_sqlite = SessionSqlite()
        print("✅ Conectado a SQLite local.")
    except Exception as e:
        print(f"❌ Error al conectar a SQLite local: {e}")
        return

    try:
        engine_pg = create_engine(postgres_url)
        SessionPg = sessionmaker(bind=engine_pg)
        session_pg = SessionPg()
        
        # Asegurar que las tablas existan en PostgreSQL antes de migrar
        Base.metadata.create_all(bind=engine_pg)
        print("✅ Conectado a PostgreSQL en Railway.")
    except Exception as e:
        print(f"❌ Error al conectar a PostgreSQL en Railway: {e}")
        session_sqlite.close()
        return

    try:
        # 1. Migrar Facturas
        print("\n📊 Leyendo facturas locales...")
        facturas_locales = session_sqlite.query(Factura).all()
        total_facturas = len(facturas_locales)
        print(f"Encontradas {total_facturas} facturas en SQLite.")

        if total_facturas > 0:
            print("⏳ Copiando facturas a Railway...")
            # Limpiar tabla de destino para evitar duplicados en la migración limpia
            session_pg.query(Factura).delete()
            
            for idx, f in enumerate(facturas_locales, 1):
                # Crear nueva instancia limpia para PostgreSQL usando los campos reales del modelo
                nueva_f = Factura(
                    id=f.id,
                    proveedor=f.proveedor,
                    tipo_servicio=f.tipo_servicio,
                    nro_factura=f.nro_factura,
                    cliente_nombre=f.cliente_nombre,
                    cuenta=f.cuenta,
                    medidor=f.medidor,
                    fecha_emision=f.fecha_emision,
                    periodo_desde=f.periodo_desde,
                    periodo_hasta=f.periodo_hasta,
                    lectura_anterior=f.lectura_anterior,
                    lectura_actual=f.lectura_actual,
                    consumo_kwh=f.consumo_kwh,
                    monto_total=f.monto_total,
                    moneda=f.moneda,
                    nombre_archivo=f.nombre_archivo,
                    hash_archivo=f.hash_archivo,
                    estado=f.estado,
                    error_extraccion=f.error_extraccion
                )
                session_pg.add(nueva_f)
                if idx % 50 == 0:
                    print(f"  -> Procesadas {idx}/{total_facturas} facturas...")
            
            session_pg.commit()
            print("✅ ¡Todas las facturas migradas con éxito!")

        # 2. Migrar Lecturas Semanales
        print("\n📈 Leyendo lecturas semanales locales...")
        lecturas_locales = session_sqlite.query(LecturaSemanal).all()
        total_lecturas = len(lecturas_locales)
        print(f"Encontradas {total_lecturas} lecturas semanales en SQLite.")

        if total_lecturas > 0:
            print("⏳ Copiando lecturas a Railway...")
            session_pg.query(LecturaSemanal).delete()
            
            for idx, l in enumerate(lecturas_locales, 1):
                nueva_l = LecturaSemanal(
                    cuenta=l.cuenta,
                    fecha_lectura=l.fecha_lectura,
                    valor_lectura=l.valor_lectura,
                    dias_transcurridos=l.dias_transcurridos,
                    consumo_periodo=l.consumo_periodo,
                    promedio_diario=l.promedio_diario,
                    promedio_diario_historico=l.promedio_diario_historico,
                    desviacion_porcentaje=l.desviacion_porcentaje,
                    alerta_estado=l.alerta_estado,
                    foto_nombre=l.foto_nombre
                )
                session_pg.add(nueva_l)
                if idx % 50 == 0:
                    print(f"  -> Procesadas {idx}/{total_lecturas} lecturas...")
            
            session_pg.commit()
            print("✅ ¡Todas las lecturas semanales migradas con éxito!")

        print("\n🎉 ¡MIGRACIÓN COMPLETADA CON ÉXITO ABSOLUTO! Revisa tu Dashboard en la nube.")

    except Exception as e:
        session_pg.rollback()
        print(f"❌ Error crítico durante la migración de datos: {e}")
    finally:
        session_sqlite.close()
        session_pg.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/migrar_a_nube.py <EXTERNAL_CONNECTION_STRING_DE_RAILWAY>")
    else:
        migrar(sys.argv[1])
