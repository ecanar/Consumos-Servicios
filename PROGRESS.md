# PROGRESS - Control de Consumo de Servicios

Este archivo sirve como bitácora y traspaso de contexto de desarrollo unificado. Permite que Cascade (u otros desarrolladores) entienda inmediatamente en qué consiste el proyecto, qué tecnologías utiliza, qué mejoras se han implementado y qué tareas quedan pendientes.

---

## 📌 1. ¿En qué consiste el Proyecto?
**Control-Consumo-Servicios** es una plataforma web inteligente diseñada para centralizar, auditar y prevenir sorpresas en las facturaciones de energía eléctrica de **9 cuentas (medidores) independientes**. 

### Funciones Principales:
* **Dashboard Analítico**: Visualización consolidada e individual de consumos en kWh y montos facturados en USD.
* **Monitoreo Semanal Prevenido**: Permite el ingreso de lecturas manuales intermedias o mediante la carga de una foto del medidor físico.
* **Asistente OCR Inteligente**: Extrae automáticamente el número de medidor y la lectura digital de la pantalla de la foto usando **Google Cloud Vision** (precisión premium en la nube) o **Tesseract OCR** (local como alternativa).
* **Métricas de Alerta Temprana**: El sistema calcula la desviación del promedio diario consumido contra el histórico del cliente, alertando visualmente en Verde (OK), Amarillo (Ajuste) o Rojo (🚨 Alerta de fuga o sobreconsumo) para actuar antes de que se emita la factura mensual.

---

## 💻 2. Arquitectura de Software
El sistema está diseñado de manera moderna, desacoplada y lista para producción:

* **Base de Datos**: **PostgreSQL** alojado en la nube en **Railway**, lo que garantiza un almacenamiento centralizado de datos reales accesible de manera segura desde cualquier PC de desarrollo o producción.
* **Backend**: **FastAPI (Python)**, SQLAlchemy, e integración de procesamiento de imágenes con Pillow y Google Cloud Vision API. Servido desde Railway.
* **Frontend**: **React (Vite)**, Axios, Recharts (gráficos vectoriales interactivos), y Lucide Icons. Diseñado con CSS puro responsivo y fluido (Mobile-First).

---

## 🏆 3. Mejoras y Características Implementadas

### 📊 Optimización del Dashboard e Interfaz
1. **Mapeo de Cuentas Coloreado**: Cada una de las 9 cuentas registradas posee un color corporativo de alto contraste y un resplandor dinámico personalizado en el selector horizontal superior. La vista global de "Todas las cuentas" usa un color Gris Pizarra elegante para unificar visualmente el control maestro.
2. **Información Acumulada**: Tarjeta resumida que muestra promedios mensuales reales (`Prom. Ult 12m`, `Prom. Ult 6m`, `Prom. Ult 3m` y el valor real del `Último mes`), dividiendo la suma acumulada para la cantidad de meses reales y activos de cada cuenta.
3. **Lógica de Agrupación Global**: Corregido el bug del backend en "Todas las cuentas". Ahora agrupa primero por mes natural antes de promediar, asegurando sumas y medias verídicas consolidadas de las 9 cuentas.
4. **Gráfico Consumo por Año**:
   * Muestra fijos los valores de consumo sobre cada barra verde de manera elegante.
   * El tamaño de la fuente es responsivo: **`16px`** en ordenadores (Windows/Desktop) para excelente lectura y **`10px`** en celulares para evitar saturar la pantalla.
   * Se removió el tooltip flotante para evitar datos redundantes al pasar el puntero.
5. **Gráfico Histórico Mensual**:
   * Eje X optimizado para mostrar únicamente el número de mes (ej. `04` en vez de `2025-04`), logrando una vista totalmente despejada.
   * El tooltip flotante conserva el año completo (ej. `2025-04`) para la consulta de datos al pasar el mouse.
6. **Layout en 2 Columnas**: Se eliminó el "Hero" de la portada superior para maximizar el área visible y se organizó el contenido en un grid responsivo simétrico de dos columnas en computadoras.

### 🔌 Conectividad de Recursos en la Nube y Archivos Estáticos
7. **Rutas Dinámicas de Evidencias (`getFotoUrl`)**:
   * Implementado un formateador que detecta dinámicamente si la aplicación corre en desarrollo local (puerto `5173` apuntando al backend en puerto `8000`) o en producción en Railway (usando la ruta relativa `/fotos/...`).
   * Esto soluciona de raíz el problema de que el botón **"Ver Foto"** diera error en producción al estar apuntando a `127.0.0.1`.
8. **Eliminación y Limpieza de Lecturas Mal Ingresadas**:
   * Creado el endpoint `DELETE /api/lecturas-semanales/{lectura_id}` que elimina el registro en base de datos.
   * **Limpieza de disco**: Si la lectura a eliminar tenía una foto, el backend borra el archivo físico del almacenamiento del servidor en Railway para no desperdiciar espacio.
   * Integrado en el frontend mediante una columna **"Acciones"** con botón de papelera roja (`Trash2`) y un cartel de confirmación seguro ante clics accidentales.

---

## 📋 4. Tareas Pendientes y Próximos Pasos

* [ ] **Monitoreo de Otros Servicios**: Extender el modelo de base de datos y la interfaz para registrar lecturas de agua o telecomunicaciones si el usuario lo requiere.
* [ ] **Preprocesamiento Avanzado de Imagen para OCR**: Añadir filtros adicionales de binarización o nitidez sobre la imagen en caliente para mejorar el índice de lectura automática en fotos tomadas en la oscuridad del medidor.
* [ ] **Reportes Exportables**: Crear un generador de reportes en formato PDF con el resumen de consumos anuales, mensuales y desviaciones de alertas para imprimir o archivar.
* [ ] **Alertas push o notificaciones**: Enviar notificaciones (ej: por correo o Telegram) si el promedio semanal calculado supera el 30% de la alerta de forma automática.

---

*Última actualización de progreso: 2 de Junio de 2026.*
