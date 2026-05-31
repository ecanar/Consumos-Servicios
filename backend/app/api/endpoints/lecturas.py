import os
import shutil
import io
from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
from PIL.ExifTags import TAGS
import pytesseract
import re

from app.db.session import get_db
from app.models.factura import Factura
from app.models.lectura_semanal import LecturaSemanal

router = APIRouter()

# Directorio de fotos
FOTOS_DIR = Path("data/fotos_medidores")
FOTOS_DIR.mkdir(parents=True, exist_ok=True)


def extraer_fecha_exif_bytes(image_bytes: bytes) -> Optional[date]:
    try:
        img = Image.open(io.BytesIO(image_bytes))
        info = img._getexif()
        if info:
            for tag, value in info.items():
                decoded = TAGS.get(tag, tag)
                if decoded in ("DateTimeOriginal", "DateTime"):
                    # El formato EXIF es típicamente "YYYY:MM:DD HH:MM:SS"
                    fecha_str = value.split(" ")[0].replace(":", "-")
                    return date.fromisoformat(fecha_str)
    except Exception:
        pass
    return None


def ocr_google_vision(image_bytes: bytes, medidores_disponibles: list):
    try:
        # Importar dinámicamente para no crashear si hay algún problema con la librería
        from google.cloud import vision
        
        # Intentar ubicar las credenciales en la raíz del proyecto si no están en el entorno
        key_path = "google_key.json"
        if os.path.exists(key_path):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath(key_path)
            
        if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
            return None, None
            
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=image_bytes)
        
        # Ejecutar detección de texto de Google Cloud
        response = client.text_detection(image=image)
        texts = response.text_annotations
        
        if not texts:
            return None, None
            
        # El primer elemento contiene todo el texto consolidado detectado por Google Cloud Vision
        full_text = texts[0].description.lower()
        
        # Buscar número de medidor
        cuenta_detectada = None
        for item in medidores_disponibles:
            m_num = str(item["medidor"]).strip().lower()
            if m_num and len(m_num) > 3 and m_num in full_text:
                cuenta_detectada = item["cuenta"]
                break
                
        # Buscar lecturas de 4 a 6 dígitos en el texto
        posibles_numeros = re.findall(r'\b\d{4,6}\b', full_text)
        lectura_detectada = None
        
        if cuenta_detectada:
            medidor_info = next((m for m in medidores_disponibles if m["cuenta"] == cuenta_detectada), None)
            if medidor_info:
                ultima_l = medidor_info["ultima_lectura"]
                sug_l = medidor_info["sugerida_lectura"]
                
                candidatos = []
                for num_str in posibles_numeros:
                    if num_str == str(medidor_info["medidor"]).lower():
                        continue
                    try:
                        val = float(num_str)
                        if val >= (ultima_l - 5) and val < (sug_l * 1.5):
                            candidatos.append(val)
                    except ValueError:
                        continue
                
                if candidatos:
                    candidatos.sort(key=lambda x: abs(x - sug_l))
                    lectura_detectada = candidatos[0]
                    
        return cuenta_detectada, lectura_detectada
    except Exception as e:
        print(f"Google Cloud Vision no está listo o configurado: {e}")
    return None, None


def ocr_extraer_datos(image_bytes: bytes, medidores_disponibles: list):
    # 1. Intentar primero con Google Cloud Vision (Nube - Alta Precisión)
    try:
        cuenta, lectura = ocr_google_vision(image_bytes, medidores_disponibles)
        if cuenta is not None or lectura is not None:
            print("[OCR] Google Cloud Vision completado con éxito!")
            return cuenta, lectura
    except Exception as e:
        print(f"[OCR] Google Cloud Vision falló, cayendo en Tesseract local: {e}")

    # 2. Fallback a Tesseract (Local - Precisión Básica)
    try:
        # Abrir imagen con Pillow
        img = Image.open(io.BytesIO(image_bytes))
        
        # OCR en la imagen original
        text = pytesseract.image_to_string(img, lang='eng')
        
        # OCR en imagen con preprocesamiento para mejorar contraste
        img_gray = img.convert('L')
        enhancer = ImageEnhance.Contrast(img_gray)
        img_contrast = enhancer.enhance(2.0)
        img_sharp = img_contrast.filter(ImageFilter.SHARPEN)
        text_proc = pytesseract.image_to_string(img_sharp, lang='eng')
        
        full_text = (text + "\n" + text_proc).lower()
        
        # Buscar número de medidor
        cuenta_detectada = None
        for item in medidores_disponibles:
            m_num = str(item["medidor"]).strip().lower()
            if m_num and len(m_num) > 3 and m_num in full_text:
                cuenta_detectada = item["cuenta"]
                break
                
        # Buscar posibles lecturas (números de 4 a 6 dígitos que no sean el número de medidor)
        posibles_numeros = re.findall(r'\b\d{4,6}\b', full_text)
        lectura_detectada = None
        
        # Si se detectó la cuenta, buscar un valor lógico para la lectura
        if cuenta_detectada:
            medidor_info = next((m for m in medidores_disponibles if m["cuenta"] == cuenta_detectada), None)
            if medidor_info:
                ultima_l = medidor_info["ultima_lectura"]
                sug_l = medidor_info["sugerida_lectura"]
                
                # Filtrar números que estén por encima de la última lectura o cerca de ella
                candidatos = []
                for num_str in posibles_numeros:
                    # No tomar el número de medidor como lectura
                    if num_str == str(medidor_info["medidor"]).lower():
                        continue
                    try:
                        val = float(num_str)
                        # Permitir lecturas que sean mayores o iguales a la última lectura (o con un margen pequeño de -5 por si hay errores previos)
                        if val >= (ultima_l - 5) and val < (sug_l * 1.5):
                            candidatos.append(val)
                    except ValueError:
                        continue
                
                if candidatos:
                    # El candidato más cercano a la lectura sugerida es el más probable
                    candidatos.sort(key=lambda x: abs(x - sug_l))
                    lectura_detectada = candidatos[0]
                    
        return cuenta_detectada, lectura_detectada
    except Exception as e:
        print(f"Error en OCR backend: {e}")
    return None, None


@router.post("/procesar-foto")
async def procesar_foto_medidor(
    foto: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # 1. Leer los bytes de la foto
    content = await foto.read()
    
    # 2. Extraer la fecha real de toma (EXIF)
    fecha_foto = extraer_fecha_exif_bytes(content)
    if not fecha_foto:
        fecha_foto = date.today() # fallback a hoy si no tiene EXIF

    # 3. Guardar la foto físicamente con nombre temporal único
    file_ext = Path(foto.filename).suffix.lower()
    if file_ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise HTTPException(status_code=400, detail="Formato de foto inválido (solo JPG, PNG, WEBP)")
    
    timestamp = int(datetime.utcnow().timestamp())
    foto_nombre = f"temp_medidor_{timestamp}{file_ext}"
    target_path = FOTOS_DIR / foto_nombre
    with open(target_path, "wb") as buffer:
        buffer.write(content)

    # 4. Obtener todos los medidores y cuentas del sistema para el asistente de mapeo
    cuentas_db = (
        db.query(Factura.cuenta, Factura.cliente_nombre, Factura.medidor)
        .filter(Factura.cuenta.isnot(None))
        .group_by(Factura.cuenta)
        .all()
    )

    medidores_disponibles = []
    for cuenta, cliente, medidor in cuentas_db:
        # Buscar la última lectura de este medidor (sea manual o de factura)
        # A. Última manual
        ultima_manual = db.query(LecturaSemanal).filter(
            LecturaSemanal.cuenta == cuenta
        ).order_by(LecturaSemanal.fecha_lectura.desc()).first()

        # B. Última factura
        ultima_factura = db.query(Factura).filter(
            Factura.cuenta == cuenta,
            Factura.estado == "ok",
            Factura.lectura_actual.isnot(None)
        ).order_by(Factura.fecha_emision.desc()).first()

        # Tomar la lectura más reciente
        lectura_actual_val = 0.0
        fecha_actual = None

        if ultima_manual and ultima_factura:
            if ultima_manual.fecha_lectura > ultima_factura.fecha_emision:
                lectura_actual_val = ultima_manual.valor_lectura
                fecha_actual = ultima_manual.fecha_lectura
            else:
                lectura_actual_val = ultima_factura.lectura_actual
                fecha_actual = ultima_factura.fecha_emision
        elif ultima_manual:
            lectura_actual_val = ultima_manual.valor_lectura
            fecha_actual = ultima_manual.fecha_lectura
        elif ultima_factura:
            lectura_actual_val = ultima_factura.lectura_actual
            fecha_actual = ultima_factura.fecha_emision

        # Calcular promedio diario histórico de esta cuenta para sugerir consumo estimado
        prom_mensual = db.query(func.avg(Factura.consumo_kwh)).filter(
            Factura.cuenta == cuenta, 
            Factura.estado == "ok"
        ).scalar() or 300.0
        
        promedio_diario = prom_mensual / 30.0

        # Sugerir la lectura calculada: lectura_anterior + (promedio_diario * 7 dias)
        sugerida_lectura = lectura_actual_val
        if fecha_actual:
            dias_delta = (fecha_foto - fecha_actual).days
            if dias_delta < 0:
                dias_delta = 7
            sugerida_lectura = lectura_actual_val + (promedio_diario * dias_delta)

        medidores_disponibles.append({
            "cuenta": cuenta,
            "cliente_nombre": cliente or "Desconocido",
            "medidor": medidor or "Sin medidor",
            "ultima_lectura": round(lectura_actual_val, 2),
            "ultima_fecha": fecha_actual.isoformat() if fecha_actual else None,
            "sugerida_lectura": round(sugerida_lectura, 2)
        })

    # 5. Detectar cuenta automáticamente basada en el nombre del archivo original
    original_filename = foto.filename.lower()
    cuenta_detectada = None
    
    # Primero buscamos por número de medidor exacto
    for item in medidores_disponibles:
        m_num = str(item["medidor"]).strip()
        if m_num and len(m_num) > 3 and m_num.lower() in original_filename:
            cuenta_detectada = item["cuenta"]
            break
            
    # Si no se detectó por medidor, buscamos por palabras clave del nombre
    if not cuenta_detectada:
        keyword_mapping = {
            "wong": "Wong",
            "nena": "Nena Tello",
            "tello": "Nena Tello",
            "v.club": "V.Club",
            "vclub": "V.Club",
            "fino": "P.Fino",
            "p.fino": "P.Fino",
            "pfino": "P.Fino",
            "sam7": "Sam7",
            "sam 7": "Sam7",
            "daniel": "Daniel Canar",
            "arianna": "Arianna Canar",
            "arelis": "Arelis Barzola",
            "barzola": "Arelis Barzola"
        }
        for kw, name in keyword_mapping.items():
            if kw in original_filename:
                # Buscar la cuenta correspondiente a este nombre de cliente
                for item in medidores_disponibles:
                    if item["cliente_nombre"].lower() == name.lower():
                        cuenta_detectada = item["cuenta"]
                        break
                if cuenta_detectada:
                    break

    # Si aún no se ha detectado o para complementar la lectura, ejecutamos OCR real sobre la foto subida!
    lectura_detectada = None
    try:
        ocr_cuenta, ocr_lectura = ocr_extraer_datos(content, medidores_disponibles)
        if ocr_cuenta and not cuenta_detectada:
            cuenta_detectada = ocr_cuenta
        if ocr_lectura:
            lectura_detectada = ocr_lectura
    except Exception as e:
        print(f"Error ejecutando OCR en endpoint: {e}")

    return {
        "fecha_foto": fecha_foto.isoformat(),
        "foto_nombre": foto_nombre,
        "medidores_disponibles": medidores_disponibles,
        "cuenta_detectada": cuenta_detectada,
        "lectura_detectada": lectura_detectada
    }


@router.post("/confirmar-asistida")
async def confirmar_lectura_asistida(
    cuenta: str = Form(...),
    fecha_lectura: str = Form(...),
    valor_lectura: float = Form(...),
    foto_nombre: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        f_lectura = date.fromisoformat(fecha_lectura)
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido")

    # Eliminar foto de temporal para no ocupar espacio en disco
    temp_path = FOTOS_DIR / foto_nombre
    if temp_path.exists():
        try:
            os.remove(temp_path)
        except Exception as e:
            print(f"No se pudo eliminar la foto temporal: {e}")

    foto_nombre_final = None

    # El resto del cálculo es idéntico a registrar_lectura
    # 1. Buscar punto anterior
    ultima_lectura_manual = db.query(LecturaSemanal).filter(
        LecturaSemanal.cuenta == cuenta,
        LecturaSemanal.fecha_lectura < f_lectura
    ).order_by(LecturaSemanal.fecha_lectura.desc()).first()

    ultima_factura = db.query(Factura).filter(
        Factura.cuenta == cuenta,
        Factura.estado == "ok",
        Factura.fecha_emision < f_lectura,
        Factura.lectura_actual.isnot(None)
    ).order_by(Factura.fecha_emision.desc()).first()

    fecha_prev = None
    lectura_prev = None

    if ultima_lectura_manual and ultima_factura:
        if ultima_lectura_manual.fecha_lectura > ultima_factura.fecha_emision:
            fecha_prev = ultima_lectura_manual.fecha_lectura
            lectura_prev = ultima_lectura_manual.valor_lectura
        else:
            fecha_prev = ultima_factura.fecha_emision
            lectura_prev = ultima_factura.lectura_actual
    elif ultima_lectura_manual:
        fecha_prev = ultima_lectura_manual.fecha_lectura
        lectura_prev = ultima_lectura_manual.valor_lectura
    elif ultima_factura:
        fecha_prev = ultima_factura.fecha_emision
        lectura_prev = ultima_factura.lectura_actual

    dias_transcurridos = None
    consumo_periodo = None
    promedio_diario = None

    if fecha_prev is not None and lectura_prev is not None:
        dias_transcurridos = (f_lectura - fecha_prev).days
        if dias_transcurridos <= 0:
            raise HTTPException(
                status_code=400, 
                detail=f"La fecha de la lectura debe ser posterior a la última registrada ({fecha_prev})"
            )
        consumo_periodo = valor_lectura - lectura_prev
        if consumo_periodo < 0:
            consumo_periodo = 0.0
        promedio_diario = consumo_periodo / dias_transcurridos

    # Promedio histórico
    prom_mensual = db.query(func.avg(Factura.consumo_kwh)).filter(
        Factura.cuenta == cuenta, 
        Factura.estado == "ok"
    ).scalar() or 300.0
    promedio_diario_historico = prom_mensual / 30.0

    desviacion_porcentaje = 0.0
    alerta_estado = "ok"

    if promedio_diario is not None:
        if promedio_diario_historico > 0:
            desviacion_porcentaje = ((promedio_diario - promedio_diario_historico) / promedio_diario_historico) * 100.0
        
        if desviacion_porcentaje > 30.0:
            alerta_estado = "alerta"
        elif desviacion_porcentaje > 10.0:
            alerta_estado = "precaucion"
        else:
            alerta_estado = "ok"

    # Guardar en Base de Datos
    nueva_lectura = LecturaSemanal(
        cuenta=cuenta,
        fecha_lectura=f_lectura,
        valor_lectura=valor_lectura,
        dias_transcurridos=dias_transcurridos,
        consumo_periodo=consumo_periodo,
        promedio_diario=round(promedio_diario, 2) if promedio_diario is not None else None,
        promedio_diario_historico=round(promedio_diario_historico, 2),
        desviacion_porcentaje=round(desviacion_porcentaje, 2),
        alerta_estado=alerta_estado,
        foto_nombre=foto_nombre_final
    )

    db.add(nueva_lectura)
    db.commit()
    db.refresh(nueva_lectura)

    return nueva_lectura


@router.get("/")
def listar_lecturas(cuenta: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(LecturaSemanal)
    if cuenta:
        query = query.filter(LecturaSemanal.cuenta == cuenta)
    return query.order_by(LecturaSemanal.fecha_lectura.desc()).all()

@router.post("/")
async def registrar_lectura(
    cuenta: str = Form(...),
    fecha_lectura: str = Form(...),
    valor_lectura: float = Form(...),
    foto: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    try:
        f_lectura = date.fromisoformat(fecha_lectura)
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido (debe ser YYYY-MM-DD)")

    # 1. Buscar punto anterior de comparación
    # A. Última lectura manual anterior
    ultima_lectura_manual = db.query(LecturaSemanal).filter(
        LecturaSemanal.cuenta == cuenta,
        LecturaSemanal.fecha_lectura < f_lectura
    ).order_by(LecturaSemanal.fecha_lectura.desc()).first()

    # B. Última factura anterior
    ultima_factura = db.query(Factura).filter(
        Factura.cuenta == cuenta,
        Factura.estado == "ok",
        Factura.fecha_emision < f_lectura,
        Factura.lectura_actual.isnot(None)
    ).order_by(Factura.fecha_emision.desc()).first()

    fecha_prev = None
    lectura_prev = None

    if ultima_lectura_manual and ultima_factura:
        # Tomar la más reciente de las dos
        if ultima_lectura_manual.fecha_lectura > ultima_factura.fecha_emision:
            fecha_prev = ultima_lectura_manual.fecha_lectura
            lectura_prev = ultima_lectura_manual.valor_lectura
        else:
            fecha_prev = ultima_factura.fecha_emision
            lectura_prev = ultima_factura.lectura_actual
    elif ultima_lectura_manual:
        fecha_prev = ultima_lectura_manual.fecha_lectura
        lectura_prev = ultima_lectura_manual.valor_lectura
    elif ultima_factura:
        fecha_prev = ultima_factura.fecha_emision
        lectura_prev = ultima_factura.lectura_actual

    # 2. Calcular variables de consumo del periodo
    dias_transcurridos = None
    consumo_periodo = None
    promedio_diario = None

    if fecha_prev is not None and lectura_prev is not None:
        dias_transcurridos = (f_lectura - fecha_prev).days
        if dias_transcurridos <= 0:
            raise HTTPException(
                status_code=400, 
                detail=f"La fecha de la lectura debe ser posterior a la última registrada ({fecha_prev})"
            )
        consumo_periodo = valor_lectura - lectura_prev
        # Evitar lecturas negativas por cambio de medidor o error
        if consumo_periodo < 0:
            consumo_periodo = 0.0
        promedio_diario = consumo_periodo / dias_transcurridos

    # 3. Calcular promedio diario histórico del cliente
    prom_mensual = db.query(func.avg(Factura.consumo_kwh)).filter(
        Factura.cuenta == cuenta, 
        Factura.estado == "ok"
    ).scalar()

    # Fallback si no hay facturas históricas para esta cuenta
    if prom_mensual is None:
        prom_mensual = 300.0  # promedio base estimado de 300 kWh/mes
    
    promedio_diario_historico = prom_mensual / 30.0

    # 4. Determinar alerta por desviación
    desviacion_porcentaje = 0.0
    alerta_estado = "ok"

    if promedio_diario is not None:
        if promedio_diario_historico > 0:
            desviacion_porcentaje = ((promedio_diario - promedio_diario_historico) / promedio_diario_historico) * 100.0
        
        if desviacion_porcentaje > 30.0:
            alerta_estado = "alerta"      # Rojo
        elif desviacion_porcentaje > 10.0:
            alerta_estado = "precaucion"   # Amarillo
        else:
            alerta_estado = "ok"           # Verde

    # 5. Guardar foto física si fue subida
    foto_nombre = None
    if foto:
        file_ext = Path(foto.filename).suffix.lower()
        if file_ext not in [".jpg", ".jpeg", ".png", ".webp"]:
            raise HTTPException(status_code=400, detail="Formato de foto inválido (solo JPG, PNG, WEBP)")
        
        # Generar nombre de archivo único
        foto_nombre = f"medidor_{cuenta}_{fecha_lectura}_{int(datetime.utcnow().timestamp())}{file_ext}"
        target_path = FOTOS_DIR / foto_nombre
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(foto.file, buffer)

    # 6. Guardar en Base de Datos
    nueva_lectura = LecturaSemanal(
        cuenta=cuenta,
        fecha_lectura=f_lectura,
        valor_lectura=valor_lectura,
        dias_transcurridos=dias_transcurridos,
        consumo_periodo=consumo_periodo,
        promedio_diario=round(promedio_diario, 2) if promedio_diario is not None else None,
        promedio_diario_historico=round(promedio_diario_historico, 2),
        desviacion_porcentaje=round(desviacion_porcentaje, 2),
        alerta_estado=alerta_estado,
        foto_nombre=foto_nombre
    )

    db.add(nueva_lectura)
    db.commit()
    db.refresh(nueva_lectura)

    return nueva_lectura


@router.delete("/{lectura_id}")
def eliminar_lectura(lectura_id: int, db: Session = Depends(get_db)):
    lectura = db.query(LecturaSemanal).filter(LecturaSemanal.id == lectura_id).first()
    if not lectura:
        raise HTTPException(status_code=404, detail="Lectura no encontrada")
    
    # Si la lectura tiene una foto asociada, eliminarla físicamente para no desperdiciar espacio
    if lectura.foto_nombre:
        foto_path = FOTOS_DIR / lectura.foto_nombre
        if foto_path.exists():
            try:
                os.remove(foto_path)
            except Exception as e:
                print(f"No se pudo eliminar la foto de la lectura: {e}")
                
    db.delete(lectura)
    db.commit()
    return {"ok": True, "message": "Lectura eliminada con éxito"}
