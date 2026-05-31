from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.factura import Factura

router = APIRouter()


@router.get("/kpis")
def obtener_kpis(cuenta: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Factura).filter(Factura.estado == "ok")
    if cuenta:
        query = query.filter(Factura.cuenta == cuenta)

    stats = db.query(
        func.count(Factura.id).label("total_facturas"),
        func.sum(Factura.consumo_kwh).label("total_kwh"),
        func.sum(Factura.monto_total).label("total_monto"),
        func.avg(Factura.consumo_kwh).label("promedio_kwh"),
        func.avg(Factura.monto_total).label("promedio_monto"),
    ).filter(Factura.estado == "ok")

    if cuenta:
        stats = stats.filter(Factura.cuenta == cuenta)

    res = stats.first()

    # Promedio de los últimos 6 meses (últimas 6 facturas por fecha desc)
    subquery = db.query(Factura.consumo_kwh, Factura.monto_total).filter(
        Factura.estado == "ok",
        Factura.fecha_emision.isnot(None)
    )
    if cuenta:
        subquery = subquery.filter(Factura.cuenta == cuenta)
    
    ultimas_facturas = subquery.order_by(Factura.fecha_emision.desc()).limit(6).all()
    
    promedio_kwh_6m = 0.0
    promedio_monto_6m = 0.0
    total_facturas_6m = len(ultimas_facturas)
    if ultimas_facturas:
        valid_kwh = [f[0] for f in ultimas_facturas if f[0] is not None]
        valid_monto = [f[1] for f in ultimas_facturas if f[1] is not None]
        promedio_kwh_6m = sum(valid_kwh) / len(valid_kwh) if valid_kwh else 0.0
        promedio_monto_6m = sum(valid_monto) / len(valid_monto) if valid_monto else 0.0

    # Determinamos la expresión de agrupación mensual compatible con la base de datos
    if db.bind.dialect.name == "postgresql":
        mes_expr = func.to_char(Factura.fecha_emision, "YYYY-MM")
    else:
        mes_expr = func.strftime("%Y-%m", Factura.fecha_emision)

    # Agrupamos los datos mensualmente sumando todas las cuentas correspondientes a cada mes
    mensual_query = db.query(
        mes_expr.label("mes"),
        func.sum(Factura.consumo_kwh).label("kwh"),
        func.sum(Factura.monto_total).label("monto")
    ).filter(Factura.estado == "ok", Factura.fecha_emision.isnot(None))

    if cuenta:
        mensual_query = mensual_query.filter(Factura.cuenta == cuenta)

    # Ordenamos de forma descendente para tener los meses más recientes primero
    meses_res = mensual_query.group_by("mes").order_by(mes_expr.desc()).all()

    # Función helper para obtener promedios mensuales basados en la lista de meses agregados
    def obtener_stats_mensuales_n(n: int):
        meses_n = meses_res[:n]
        valid_kwh = [m[1] for m in meses_n if m[1] is not None]
        valid_monto = [m[2] for m in meses_n if m[2] is not None]
        
        total_kwh_n = sum(valid_kwh) if valid_kwh else 0.0
        total_monto_n = sum(valid_monto) if valid_monto else 0.0
        count_n = len(meses_n)
        
        # Estos promedios representan la suma mensual dividida para el número de meses en el rango
        promedio_kwh_n = total_kwh_n / count_n if count_n > 0 else 0.0
        promedio_monto_n = total_monto_n / count_n if count_n > 0 else 0.0
        
        return {
            "total_kwh": round(total_kwh_n, 2),
            "total_monto": round(total_monto_n, 2),
            "promedio_kwh": round(promedio_kwh_n, 2),
            "promedio_monto": round(promedio_monto_n, 2),
            "count": count_n
        }

    stats_3m = obtener_stats_mensuales_n(3)
    stats_6m = obtener_stats_mensuales_n(6)
    stats_12m = obtener_stats_mensuales_n(12)

    # Gasto y consumo del último mes completo registrado (el mes más reciente de forma agregada)
    ultimo_mes = {
        "monto": round(meses_res[0][2], 2) if (len(meses_res) > 0 and meses_res[0][2] is not None) else 0.0,
        "kwh": round(meses_res[0][1], 2) if (len(meses_res) > 0 and meses_res[0][1] is not None) else 0.0
    }

    # Total de cuentas activas
    total_cuentas = db.query(func.count(func.distinct(Factura.cuenta))).scalar() or 0

    total_facturas = res.total_facturas or 0
    total_kwh = res.total_kwh or 0.0
    total_monto = res.total_monto or 0.0
    promedio_kwh = res.promedio_kwh or 0.0
    promedio_monto = res.promedio_monto or 0.0

    costo_promedio_kwh = (total_monto / total_kwh) if total_kwh > 0 else 0.0

    return {
        "total_facturas": total_facturas,
        "total_kwh": round(total_kwh, 2),
        "total_monto": round(total_monto, 2),
        "promedio_kwh": round(promedio_kwh, 2),
        "promedio_monto": round(promedio_monto, 2),
        "promedio_kwh_6m": round(promedio_kwh_6m, 2),
        "promedio_monto_6m": round(promedio_monto_6m, 2),
        "total_facturas_6m": total_facturas_6m,
        "costo_promedio_kwh": round(costo_promedio_kwh, 4),
        "total_cuentas": total_cuentas,
        "stats_3m": stats_3m,
        "stats_6m": stats_6m,
        "stats_12m": stats_12m,
        "ultimo_mes": ultimo_mes,
    }


@router.get("/consumo-mensual")
def consumo_mensual(cuenta: Optional[str] = None, db: Session = Depends(get_db)):
    # Agrupa por mes de emisión de forma compatible con SQLite y PostgreSQL
    if db.bind.dialect.name == "postgresql":
        mes_expr = func.to_char(Factura.fecha_emision, "YYYY-MM")
    else:
        mes_expr = func.strftime("%Y-%m", Factura.fecha_emision)

    query = db.query(
        mes_expr.label("mes"),
        func.sum(Factura.consumo_kwh).label("kwh"),
        func.sum(Factura.monto_total).label("monto"),
        func.count(Factura.id).label("facturas"),
    ).filter(Factura.estado == "ok", Factura.fecha_emision.isnot(None))

    if cuenta:
        query = query.filter(Factura.cuenta == cuenta)

    resultados = query.group_by("mes").order_by("mes").all()

    mapa_anios = {
        "2022": "A",
        "2023": "B",
        "2024": "C",
        "2025": "D",
        "2026": "E",
        "2027": "F"
    }

    datos = []
    for r in resultados:
        if r.mes and len(r.mes) >= 7:
            datos.append({
                "mes": r.mes,  # Retorna directamente el formato "YYYY-MM" (ej: "2025-04")
                "kwh": round(r.kwh or 0.0, 2),
                "monto": round(r.monto or 0.0, 2),
                "facturas": r.facturas,
                "costo_kwh": round((r.monto / r.kwh) if r.kwh and r.kwh > 0 else 0.0, 4)
            })
    return datos


@router.get("/resumen-cuentas")
def resumen_por_cuenta(db: Session = Depends(get_db)):
    # 1. Resumen histórico acumulado
    resultados = db.query(
        Factura.cuenta,
        Factura.cliente_nombre,
        func.count(Factura.id).label("facturas"),
        func.sum(Factura.consumo_kwh).label("kwh"),
        func.sum(Factura.monto_total).label("monto"),
    ).filter(Factura.estado == "ok", Factura.cuenta.isnot(None)).group_by(Factura.cuenta, Factura.cliente_nombre).order_by(func.sum(Factura.monto_total).desc()).all()

    # 2. Obtener los valores del último mes (última factura emitida) para cada cuenta
    subquery_last = db.query(
        Factura.cuenta,
        func.max(Factura.fecha_emision).label("max_fecha")
    ).filter(Factura.estado == "ok", Factura.cuenta.isnot(None)).group_by(Factura.cuenta).subquery()

    ultimas_facturas = db.query(
        Factura.cuenta,
        Factura.monto_total.label("monto"),
        Factura.consumo_kwh.label("kwh")
    ).join(
        subquery_last,
        (Factura.cuenta == subquery_last.c.cuenta) & (Factura.fecha_emision == subquery_last.c.max_fecha)
    ).filter(Factura.estado == "ok").all()

    # Mapa para búsquedas rápidas: {cuenta: (monto, kwh)}
    mapa_ultimas = {f.cuenta: (f.monto, f.kwh) for f in ultimas_facturas}

    datos = []
    for r in resultados:
        u_monto, u_kwh = mapa_ultimas.get(r.cuenta, (0.0, 0.0))
        datos.append({
            "cuenta": r.cuenta,
            "cliente_nombre": r.cliente_nombre or "Desconocido",
            "facturas": r.facturas,
            "kwh": round(r.kwh or 0.0, 2),
            "monto": round(r.monto or 0.0, 2),
            "ultimo_mes_kwh": round(u_kwh or 0.0, 2),
            "ultimo_mes_monto": round(u_monto or 0.0, 2),
            "costo_kwh": round((r.monto / r.kwh) if r.kwh and r.kwh > 0 else 0.0, 4)
        })
    return datos


@router.get("/comparativa-anual")
def comparativa_anual(cuenta: Optional[str] = None, db: Session = Depends(get_db)):
    # Agrupa por año de emisión y compara consumo y costo total de forma compatible con SQLite y PostgreSQL
    if db.bind.dialect.name == "postgresql":
        anio_expr = func.to_char(Factura.fecha_emision, "YYYY")
    else:
        anio_expr = func.strftime("%Y", Factura.fecha_emision)

    query = db.query(
        anio_expr.label("anio"),
        func.sum(Factura.consumo_kwh).label("kwh"),
        func.sum(Factura.monto_total).label("monto"),
    ).filter(Factura.estado == "ok", Factura.fecha_emision.isnot(None))

    if cuenta:
        query = query.filter(Factura.cuenta == cuenta)

    resultados = query.group_by("anio").order_by("anio").all()

    datos = []
    for r in resultados:
        if r.anio:
            datos.append({
                "anio": r.anio,
                "kwh": round(r.kwh or 0.0, 2),
                "monto": round(r.monto or 0.0, 2),
            })
    return datos
