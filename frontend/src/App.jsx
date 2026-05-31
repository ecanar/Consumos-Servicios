import { useEffect, useState } from "react"
import {
  Activity,
  Calendar,
  DollarSign,
  FileText,
  Gauge,
  Layers,
  TrendingUp,
  User,
  UploadCloud,
  ArrowLeft,
  Plus,
  Image as ImageIcon,
  AlertTriangle,
  CheckCircle,
  Clock,
  Menu,
  Sparkles,
  Search,
} from "lucide-react"
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import {
  getComparativaAnual,
  getConsumoMensual,
  getCuentas,
  getFacturas,
  getHealth,
  getKPIs,
  getResumenCuentas,
  subirFacturaPDF,
  getLecturasSemanales,
  procesarFotoMedidor,
  confirmarLecturaAsistida,
} from "./lib/api"

export default function App() {
  // Navigation
  const [currentView, setCurrentView] = useState("menu") // menu, dashboard, upload, medidores

  // Shared state
  const [status, setStatus] = useState("verificando")
  const [cuentas, setCuentas] = useState([])
  const [resumenCuentas, setResumenCuentas] = useState([])

  // Dashboard View State
  const [cuentaSeleccionada, setCuentaSeleccionada] = useState("")
  const [kpis, setKPIs] = useState({
    total_facturas: 0,
    total_kwh: 0,
    total_monto: 0,
    promedio_kwh: 0,
    promedio_monto: 0,
    promedio_kwh_6m: 0,
    promedio_monto_6m: 0,
    total_facturas_6m: 0,
    costo_promedio_kwh: 0,
    total_cuentas: 0,
    stats_3m: { total_monto: 0, total_kwh: 0, promedio_monto: 0, promedio_kwh: 0, count: 0 },
    stats_6m: { total_monto: 0, total_kwh: 0, promedio_monto: 0, promedio_kwh: 0, count: 0 },
    stats_12m: { total_monto: 0, total_kwh: 0, promedio_monto: 0, promedio_kwh: 0, count: 0 },
  })
  const [consumoMensual, setConsumoMensual] = useState([])
  const [comparativaAnual, setComparativaAnual] = useState([])
  const [facturas, setFacturas] = useState([])
  const [page, setPage] = useState(0)
  const pageSize = 10
  const [totalFacturas, setTotalFacturas] = useState(0)

  // Upload View State
  const [uploadLogs, setUploadLogs] = useState([])

  // Weekly Meter Readings View State
  const [lecturasSemanales, setLecturasSemanales] = useState([])
  const [cuentaLecturaFiltro, setCuentaLecturaFiltro] = useState("")
  
  // Photo Processing state (Asistente Inteligente)
  const [isProcessingFoto, setIsProcessingFoto] = useState(false)
  const [datosAsistidos, setDatosAsistidos] = useState(null) // { fecha_foto, foto_nombre, medidores_disponibles }
  const [isLecturaOcr, setIsLecturaOcr] = useState(false)
  const [asistenteForm, setAsistenteForm] = useState({
    cuenta: "",
    fecha_lectura: "",
    valor_lectura: "",
  })

  // Initial connection check & load accounts list
  useEffect(() => {
    getHealth()
      .then(() => {
        setStatus("conectado")
        cargarCuentas()
      })
      .catch(() => setStatus("sin conexión"))
  }, [])

  // Reload data for dashboard when filters change
  useEffect(() => {
    if (status === "conectado" && currentView === "dashboard") {
      cargarDashboard()
    }
  }, [cuentaSeleccionada, currentView, status])

  useEffect(() => {
    if (status === "conectado" && currentView === "dashboard") {
      cargarFacturasPaginadas()
    }
  }, [cuentaSeleccionada, page, currentView, status])

  // Reload weekly readings when view or filter changes
  useEffect(() => {
    if (status === "conectado" && currentView === "medidores") {
      cargarLecturasSemanales()
    }
  }, [cuentaLecturaFiltro, currentView, status])

  const cargarCuentas = async () => {
    try {
      const res = await getCuentas()
      setCuentas(res.data)
      const resResumen = await getResumenCuentas()
      setResumenCuentas(resResumen.data)
    } catch (err) {
      console.error("Error al cargar cuentas:", err)
    }
  }

  const cargarDashboard = async () => {
    try {
      const [resKpis, resMensual, resAnual] = await Promise.all([
        getKPIs(cuentaSeleccionada),
        getConsumoMensual(cuentaSeleccionada),
        getComparativaAnual(cuentaSeleccionada),
      ])
      setKPIs(resKpis.data)
      setConsumoMensual(resMensual.data)
      setComparativaAnual(resAnual.data)
    } catch (err) {
      console.error("Error al cargar dashboard:", err)
    }
  }

  const cargarFacturasPaginadas = async () => {
    try {
      const skip = page * pageSize
      const res = await getFacturas(cuentaSeleccionada, skip, pageSize)
      setFacturas(res.data)
      
      const resKpis = await getKPIs(cuentaSeleccionada)
      setTotalFacturas(resKpis.data.total_facturas)
    } catch (err) {
      console.error("Error al cargar facturas:", err)
    }
  }

  const cargarLecturasSemanales = async () => {
    try {
      const res = await getLecturasSemanales(cuentaLecturaFiltro)
      setLecturasSemanales(res.data)
    } catch (err) {
      console.error("Error al cargar lecturas:", err)
    }
  }

  // Upload PDFs Handlers
  const handleFileUpload = async (e) => {
    const files = Array.from(e.target.files)
    if (files.length === 0) return
    
    const logs = []
    for (const file of files) {
      try {
        const res = await subirFacturaPDF(file)
        if (res.data.status === "ok") {
          const f = res.data.factura
          logs.push({
            name: file.name,
            success: true,
            msg: `Éxito. Cliente: ${f.cliente_nombre}, Consumo: ${f.consumo_kwh || '—'} kWh, Total: $${f.monto_total}`
          })
        }
      } catch (err) {
        const errMsg = err.response?.data?.detail || "Error al leer PDF o duplicado existente."
        logs.push({
          name: file.name,
          success: false,
          msg: errMsg
        })
      }
    }
    setUploadLogs((prev) => [...logs, ...prev])
    cargarCuentas()
  }

  // Weekly Photo Upload (Asistente EXIF + visual matcher)
  const handleFotoMedidorUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return

    setIsProcessingFoto(true)
    setDatosAsistidos(null)

    try {
      const res = await procesarFotoMedidor(file)
      const data = res.data
      setDatosAsistidos(data)
      
      // Inicializar el formulario con fecha EXIF y cuenta auto-detectada si existe
      const cuentaPreseleccionada = data.cuenta_detectada || ""
      const medidorInfo = data.medidores_disponibles.find(m => m.cuenta === cuentaPreseleccionada)
      
      // Si el backend detectó la lectura vía OCR, la pre-llenamos; de lo contrario, usamos la sugerida por historial
      const ocrDetectado = data.lectura_detectada !== null && data.lectura_detectada !== undefined;
      setIsLecturaOcr(ocrDetectado);
      
      const lecturaPrellenada = ocrDetectado
        ? data.lectura_detectada
        : (medidorInfo ? medidorInfo.sugerida_lectura : "")
      
      setAsistenteForm({
        cuenta: cuentaPreseleccionada,
        fecha_lectura: data.fecha_foto,
        valor_lectura: lecturaPrellenada
      })
    } catch (err) {
      alert("Error al analizar la imagen: " + (err.response?.data?.detail || "Formato inválido de imagen."))
    } finally {
      setIsProcessingFoto(false)
    }
  }

  // Al cambiar la cuenta seleccionada en el asistente, auto-completar la lectura sugerida
  const handleAsistenteCuentaChange = (cuenta) => {
    const medidor = datosAsistidos.medidores_disponibles.find(m => m.cuenta === cuenta)
    setIsLecturaOcr(false) // Al cambiar manualmente, cae en la sugerida histórica
    setAsistenteForm(prev => ({
      ...prev,
      cuenta: cuenta,
      valor_lectura: medidor ? medidor.sugerida_lectura : ""
    }))
  }

  // Confirmar lectura manual asistida
  const handleConfirmarAsistidaSubmit = async (e) => {
    e.preventDefault()
    if (!asistenteForm.cuenta || !asistenteForm.fecha_lectura || !asistenteForm.valor_lectura) {
      alert("Por favor, rellene todos los campos obligatorios.")
      return
    }

    const formData = new FormData()
    formData.append("cuenta", asistenteForm.cuenta)
    formData.append("fecha_lectura", asistenteForm.fecha_lectura)
    formData.append("valor_lectura", parseFloat(asistenteForm.valor_lectura))
    formData.append("foto_nombre", datosAsistidos.foto_nombre)

    try {
      await confirmarLecturaAsistida(formData)
      alert("Lectura registrada y foto asociada de forma correcta!")
      setDatosAsistidos(null)
      setAsistenteForm({ cuenta: "", fecha_lectura: "", valor_lectura: "" })
      cargarLecturasSemanales()
    } catch (err) {
      alert("Error: " + (err.response?.data?.detail || "No se pudo registrar la lectura."))
    }
  }

  const handleCambiarCuenta = (e) => {
    setCuentaSeleccionada(e.target.value)
    setPage(0)
  }

  const handleSeleccionarItemCuenta = (cuenta) => {
    setCuentaSeleccionada(cuenta)
    setPage(0)
  }

  // Helpers de formato
  const formatUSD = (val) =>
    new Intl.NumberFormat("es-EC", { style: "currency", currency: "USD" }).format(val)

  const formatKWH = (val) =>
    new Intl.NumberFormat("es-EC", { maximumFractionDigits: 1 }).format(val) + " kWh"

  const formatDecimal = (val) =>
    new Intl.NumberFormat("es-EC", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(val)

  const formatEntero = (val) =>
    new Intl.NumberFormat("es-EC", { maximumFractionDigits: 0 }).format(val)

  // Obtiene de forma dinámica la última letra de año cargada en el dataset
  const obtenerLeyendaAnio = () => {
    if (!consumoMensual || consumoMensual.length === 0) return ""
    const letras = new Set()
    consumoMensual.forEach((d) => {
      if (d.mes && d.mes.includes("-")) {
        letras.add(d.mes.split("-")[0])
      }
    })
    const letrasOrdenadas = Array.from(letras).sort()
    if (letrasOrdenadas.length === 0) return ""
    const ultimaLetra = letrasOrdenadas[letrasOrdenadas.length - 1]
    const mapaInverso = {
      A: 2022,
      B: 2023,
      C: 2024,
      D: 2025,
      E: 2026,
      F: 2027,
      G: 2028,
      H: 2029,
    }
    const anio = mapaInverso[ultimaLetra]
    return anio ? ` (${ultimaLetra} = ${anio})` : ""
  }

  const leyendaAnio = obtenerLeyendaAnio()

  return (
    <main className="app-shell">
      {/* Navigation Header when in a view */}
      {currentView !== "menu" && (
        <header className="nav-header">
          <button className="btn-back" onClick={() => {
            setCurrentView("menu")
            setDatosAsistidos(null) // reset asistente
          }}>
            <ArrowLeft size={18} />
            <span>Volver al Menú Principal</span>
          </button>
          <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
            <span style={{ fontSize: "12px", fontWeight: "700", color: "#64748b" }}>Vista Actual:</span>
            <span className="status-pill ok" style={{ textTransform: "uppercase" }}>
              {currentView === "dashboard" ? "Estadísticas" : currentView === "upload" ? "Carga PDFs" : "Medidores"}
            </span>
          </div>
        </header>
      )}

      {/* Hero Section */}
      <section className="hero-card">
        <div>
          <p className="eyebrow">Control de Consumo Eléctrico</p>
          <h1>Control de Consumo de Servicios</h1>
          <p className="subtitle">
            Monitoreo preventivo y auditoría histórica de planillas de CNEL integrados con lecturas semanales manuales de medidores.
          </p>
        </div>
        <div className={`status-pill ${status === "conectado" ? "ok" : ""}`}>
          {status === "conectado" ? "BBDD Conectada" : status}
        </div>
      </section>

      {/* 1. VIEW: MAIN MENU (HOME) */}
      {currentView === "menu" && (
        <section className="home-menu">
          <article className="dashboard-card menu-card" onClick={() => setCurrentView("dashboard")}>
            <div className="menu-icon-wrapper">
              <Activity size={32} />
            </div>
            <h2>Dashboard Analítico</h2>
            <p>
              Explora las estadísticas históricas, gráficos de área de consumo y costos, balances anuales y rankings de tus {cuentas.length} cuentas registradas.
            </p>
          </article>

          <article className="dashboard-card menu-card" onClick={() => setCurrentView("upload")}>
            <div className="menu-icon-wrapper">
              <UploadCloud size={32} />
            </div>
            <h2>Ingreso Mensual (PDFs)</h2>
            <p>
              Sube tus nuevas planillas de CNEL arrastrando los archivos PDFs. El sistema extraerá las lecturas, consumos y montos al instante.
            </p>
          </article>

          <article className="dashboard-card menu-card" onClick={() => setCurrentView("medidores")}>
            <div className="menu-icon-wrapper">
              <Clock size={32} />
            </div>
            <h2>Monitoreo de Medidores</h2>
            <p>
              ¡Cero errores de digitación! Sube la foto del medidor, el sistema lee la fecha real de la foto (EXIF), y te asiste para seleccionar el medidor visualmente con lecturas sugeridas.
            </p>
          </article>
        </section>
      )}

      {/* 2. VIEW: DASHBOARD ANALYTICS */}
      {currentView === "dashboard" && (
        <>
          {/* KPI Cards Grid */}
          <section className="grid-cards" style={{ marginTop: "24px" }}>
            <article className="metric-card" style={{ padding: "24px" }}>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                  <thead>
                    <tr>
                      <th style={{ textAlign: "left", paddingBottom: "12px", fontSize: "13px", fontWeight: "700", color: "#475569", textTransform: "none" }}>Informacion Acumulada</th>
                      <th style={{ textAlign: "right", paddingBottom: "12px", fontSize: "13px", fontWeight: "700", color: "#475569", textTransform: "none" }}>Gasto $$</th>
                      <th style={{ textAlign: "right", paddingBottom: "12px", paddingRight: "8px", fontSize: "13px", fontWeight: "700", color: "#475569", textTransform: "none" }}>Consumo kWh</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td style={{ textAlign: "left", padding: "12px 8px", fontSize: "13px", fontWeight: "500", color: "#0f172a" }}>Prom. Ult 12m</td>
                      <td style={{ textAlign: "right", padding: "12px 8px", fontSize: "13px", fontWeight: "600", color: "#0f172a" }}>
                        {formatDecimal(kpis.stats_12m?.promedio_monto || 0)}
                      </td>
                      <td style={{ textAlign: "right", padding: "12px 8px", paddingRight: "8px", fontSize: "13px", fontWeight: "600", color: "#0f172a" }}>
                        {formatEntero(kpis.stats_12m?.promedio_kwh || 0)}
                      </td>
                    </tr>
                    <tr>
                      <td style={{ textAlign: "left", padding: "12px 8px", fontSize: "13px", fontWeight: "500", color: "#0f172a" }}>Prom. Ult 6m</td>
                      <td style={{ textAlign: "right", padding: "12px 8px", fontSize: "13px", fontWeight: "600", color: "#0f172a" }}>
                        {formatDecimal(kpis.stats_6m?.promedio_monto || 0)}
                      </td>
                      <td style={{ textAlign: "right", padding: "12px 8px", paddingRight: "8px", fontSize: "13px", fontWeight: "600", color: "#0f172a" }}>
                        {formatEntero(kpis.stats_6m?.promedio_kwh || 0)}
                      </td>
                    </tr>
                    <tr>
                      <td style={{ textAlign: "left", padding: "12px 8px", fontSize: "13px", fontWeight: "500", color: "#0f172a" }}>Prom. Ult 3m</td>
                      <td style={{ textAlign: "right", padding: "12px 8px", fontSize: "13px", fontWeight: "600", color: "#0f172a" }}>
                        {formatDecimal(kpis.stats_3m?.promedio_monto || 0)}
                      </td>
                      <td style={{ textAlign: "right", padding: "12px 8px", paddingRight: "8px", fontSize: "13px", fontWeight: "600", color: "#0f172a" }}>
                        {formatEntero(kpis.stats_3m?.promedio_kwh || 0)}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </article>

            <article className="metric-card" style={{ minHeight: "180px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#64748b" }}>
                <Calendar size={20} style={{ color: "#2563eb" }} />
                <span style={{ fontWeight: "700", fontSize: "14px" }}>Consumo por Año</span>
              </div>
              <div style={{ height: "110px", width: "100%", marginTop: "12px" }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={comparativaAnual} margin={{ top: 0, right: 0, left: -25, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(148, 163, 184, 0.1)" />
                    <XAxis dataKey="anio" stroke="#64748b" fontSize={10} tickLine={false} />
                    <YAxis stroke="#64748b" fontSize={10} tickLine={false} />
                    <Tooltip
                      contentStyle={{
                        background: "transparent",
                        border: "none",
                        boxShadow: "none",
                        fontSize: "12px",
                      }}
                    />
                    <Bar name="Monto ($)" dataKey="monto" fill="#3b82f6" radius={[3, 3, 0, 0]} />
                    <Bar name="Energía (kWh)" dataKey="kwh" fill="#10b981" radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </article>
          </section>

          {/* Main Grid Content */}
          <section className="dashboard-grid">
            
            {/* 1. Historico de Consumo y Costos Mensuales */}
            <div className="dashboard-card">
              <h3 style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span>Histórico de Consumo y Costos Mensuales</span>
                {leyendaAnio && (
                  <span style={{ color: "#ef4444", fontSize: "13px", fontWeight: "800", letterSpacing: "0.05em" }}>
                    {leyendaAnio}
                  </span>
                )}
              </h3>
              <div className="chart-container">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart
                    data={consumoMensual}
                    margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                  >
                    <defs>
                      <linearGradient id="colorMonto" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0} />
                      </linearGradient>
                      <linearGradient id="colorKwh" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(148, 163, 184, 0.15)" />
                    <XAxis dataKey="mes" stroke="#64748b" fontSize={12} tickLine={false} />
                    <YAxis stroke="#64748b" fontSize={12} tickLine={false} />
                    <Tooltip
                      contentStyle={{
                        background: "rgba(255, 255, 255, 0.35)",
                        backdropFilter: "blur(8px)",
                        WebkitBackdropFilter: "blur(8px)",
                        borderRadius: "12px",
                        border: "1px solid rgba(148, 163, 184, 0.3)",
                        boxShadow: "0 4px 20px rgba(0, 0, 0, 0.05)",
                      }}
                    />
                    <Legend />
                    <Area
                      type="monotone"
                      name="Monto ($)"
                      dataKey="monto"
                      stroke="#3b82f6"
                      strokeWidth={2}
                      fillOpacity={1}
                      fill="url(#colorMonto)"
                    />
                    <Area
                      type="monotone"
                      name="Energía (kWh)"
                      dataKey="kwh"
                      stroke="#10b981"
                      strokeWidth={2}
                      fillOpacity={1}
                      fill="url(#colorKwh)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* 2. Cuentas Registradas */}
            <div className="dashboard-card">
              <h3>Cuentas Registradas ({kpis.total_cuentas})</h3>
              <p style={{ fontSize: "12px", color: "#64748b", margin: "-12px 0 16px" }}>
                Ordenado por facturación acumulada
              </p>
              <div className="accounts-list">
                <div
                  className={`account-item ${cuentaSeleccionada === "" ? "active" : ""}`}
                  onClick={() => handleSeleccionarItemCuenta("")}
                >
                  <div className="account-info">
                    <span className="account-name">Todas las cuentas</span>
                    <span className="account-number">Vista Global</span>
                  </div>
                  <div className="account-stats">
                    <span className="account-monto">{formatUSD(resumenCuentas.reduce((acc, c) => acc + c.monto, 0))}</span>
                    <span className="account-kwh">{formatKWH(resumenCuentas.reduce((acc, c) => acc + c.kwh, 0))}</span>
                  </div>
                </div>

                {resumenCuentas.map((c) => (
                  <div
                    key={c.cuenta}
                    className={`account-item ${cuentaSeleccionada === c.cuenta ? "active" : ""}`}
                    onClick={() => handleSeleccionarItemCuenta(c.cuenta)}
                  >
                    <div className="account-info">
                      <span className="account-name">{c.cliente_nombre}</span>
                      <span className="account-number">Cuenta: {c.cuenta}</span>
                    </div>
                    <div className="account-stats">
                      <span className="account-monto">{formatUSD(c.monto)}</span>
                      <span className="account-kwh">{formatKWH(c.kwh)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* 3. Facturas Procesadas */}
            <div className="dashboard-card">
              <h3>Facturas Procesadas</h3>
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Fecha Emisión</th>
                      <th>Cliente / Cuenta</th>
                      <th>Consumo</th>
                      <th>Monto Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {facturas.map((f) => (
                      <tr key={f.id}>
                        <td style={{ fontWeight: "600" }}>{f.fecha_emision || "—"}</td>
                        <td>
                          <div style={{ fontWeight: "600" }}>{f.cliente_nombre || "Desconocido"}</div>
                          <div style={{ fontSize: "11px", color: "#64748b" }}>Cuenta: {f.cuenta || "—"}</div>
                        </td>
                        <td style={{ fontWeight: "700", color: "#10b981" }}>
                          {f.consumo_kwh ? `${formatKWH(f.consumo_kwh)}` : "—"}
                        </td>
                        <td style={{ fontWeight: "700", color: "#2563eb" }}>
                          {f.monto_total ? formatUSD(f.monto_total) : "—"}
                        </td>
                      </tr>
                    ))}
                    {facturas.length === 0 && (
                      <tr>
                        <td colSpan="4" style={{ textAlign: "center", padding: "40px", color: "#64748b" }}>
                          No se encontraron facturas con los filtros seleccionados
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              {/* Pagination Controls */}
              <div className="pagination">
                <span style={{ fontSize: "14px", color: "#64748b" }}>
                  Mostrando {facturas.length} de {totalFacturas} facturas
                </span>
                <div style={{ display: "flex", gap: "8px" }}>
                  <button
                    onClick={() => setPage((prev) => Math.max(0, prev - 1))}
                    disabled={page === 0}
                  >
                    Anterior
                  </button>
                  <span style={{ display: "flex", alignItems: "center", padding: "0 10px", fontWeight: "700", fontSize: "14px" }}>
                    Página {page + 1}
                  </span>
                  <button
                    onClick={() => setPage((prev) => prev + 1)}
                    disabled={(page + 1) * pageSize >= totalFacturas}
                  >
                    Siguiente
                  </button>
                </div>
              </div>
            </div>

          </section>
        </>
      )}

      {/* 3. VIEW: UPLOAD MONTHLY BILLS (PDFs) */}
      {currentView === "upload" && (
        <section className="upload-container">
          <div className="dashboard-card">
            <h3>Carga de Planillas Mensuales CNEL</h3>
            <p style={{ fontSize: "14px", color: "#64748b", marginTop: "-10px" }}>
              Sube uno o varios archivos PDF descargados de CNEL. El sistema los procesará de inmediato, normalizará sus nombres y registrará los datos.
            </p>

            <label htmlFor="pdf-input" className="dropzone">
              <UploadCloud size={48} style={{ color: "#2563eb" }} />
              <div>
                <p style={{ fontWeight: "700", fontSize: "16px" }}>Arrastra tus facturas aquí o haz clic para buscar</p>
                <p style={{ fontSize: "12px", color: "#64748b", marginTop: "4px" }}>Soporta la subida de múltiples archivos PDF al mismo tiempo</p>
              </div>
              <input
                id="pdf-input"
                type="file"
                multiple
                accept=".pdf"
                onChange={handleFileUpload}
                className="file-input"
              />
            </label>
          </div>

          {uploadLogs.length > 0 && (
            <div className="dashboard-card upload-logs">
              <h3>Historial de Procesamiento en Vivo</h3>
              <div style={{ marginTop: "12px", maxHeight: "400px", overflowY: "auto" }}>
                {uploadLogs.map((log, index) => (
                  <div key={index} className={`log-item ${log.success ? "success" : "error"}`}>
                    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                      {log.success ? (
                        <CheckCircle size={18} style={{ color: "#10b981" }} />
                      ) : (
                        <AlertTriangle size={18} style={{ color: "#ef4444" }} />
                      )}
                      <div>
                        <div style={{ fontWeight: "700", color: "#0f172a" }}>{log.name}</div>
                        <div style={{ color: "#475569", marginTop: "2px" }}>{log.msg}</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>
      )}

      {/* 4. VIEW: WEEKLY METER MONITORING */}
      {currentView === "medidores" && (
        <section style={{ marginTop: "24px" }}>
          {/* Asistente Inteligente de Carga por Foto */}
          {!datosAsistidos ? (
            <div className="dashboard-card" style={{ padding: "40px", textAlign: "center", marginBottom: "24px" }}>
              <div style={{ width: "80px", height: "80px", background: "rgba(37, 99, 235, 0.1)", color: "#2563eb", borderRadius: "50%", display: "grid", placeItems: "center", margin: "0 auto 20px" }}>
                <UploadCloud size={40} />
              </div>
              <h2 style={{ fontSize: "24px", fontWeight: "800", color: "#0f172a", margin: "0 0 8px" }}>Asistente de Lecturas por Foto</h2>
              <p style={{ maxWidth: "600px", color: "#64748b", fontSize: "15px", margin: "0 auto 24px", lineHeight: "1.6" }}>
                ¡El operario solo necesita tomar la foto! El sistema extraerá de forma 100% real la fecha de la foto (EXIF), y te ayudará a asociar el medidor visualmente con lecturas automáticas recomendadas para evitar errores humanos.
              </p>
              
              {isProcessingFoto ? (
                <div style={{ padding: "20px" }}>
                  <div style={{ 
                    width: "48px", 
                    height: "48px", 
                    border: "4px solid rgba(37, 99, 235, 0.1)", 
                    borderTopColor: "#2563eb", 
                    borderRadius: "50%", 
                    animation: "pulse-alert 1s infinite linear",
                    margin: "0 auto 16px"
                  }} />
                  <p style={{ fontWeight: "700", color: "#2563eb" }}>Analizando metadatos EXIF de la imagen...</p>
                </div>
              ) : (
                <label htmlFor="foto-upload" className="btn-submit" style={{ display: "inline-flex", padding: "14px 32px", fontSize: "15px", margin: "0 auto", cursor: "pointer" }}>
                  <ImageIcon size={20} />
                  <span>Subir Foto del Medidor</span>
                  <input
                    id="foto-upload"
                    type="file"
                    accept="image/*"
                    capture="environment"
                    onChange={handleFotoMedidorUpload}
                    style={{ display: "none" }}
                  />
                </label>
              )}
            </div>
          ) : (
            /* Split View: Photo on the left, Verified Confirmation Form on the right */
            <div className="medidor-grid" style={{ marginBottom: "24px" }}>
              {/* Photo Display Card with scanning grid effect */}
              <div className="dashboard-card" style={{ padding: "20px", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
                <h3 style={{ margin: "0 0 12px", alignSelf: "flex-start", display: "flex", alignItems: "center", gap: "8px" }}>
                  <ImageIcon size={18} style={{ color: "#2563eb" }} />
                  <span>Foto del Medidor Física</span>
                </h3>
                <div style={{ 
                  position: "relative", 
                  width: "100%", 
                  borderRadius: "16px", 
                  overflow: "hidden", 
                  border: "1px solid rgba(148, 163, 184, 0.25)",
                  background: "#000",
                  aspectRatio: "4/3",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center"
                }}>
                  <img 
                    src={`http://127.0.0.1:8000/fotos/${datosAsistidos.foto_nombre}`} 
                    alt="Medidor" 
                    style={{ maxWidth: "100%", maxHeight: "100%", objectFit: "contain" }}
                  />
                  <div style={{
                    position: "absolute",
                    top: 0, left: 0, right: 0, bottom: 0,
                    boxShadow: "inset 0 0 40px rgba(37, 99, 235, 0.15)",
                    pointerEvents: "none"
                  }} />
                </div>
                <div style={{ display: "flex", gap: "10px", width: "100%", marginTop: "12px", background: "rgba(37, 99, 235, 0.05)", padding: "12px", borderRadius: "12px" }}>
                  <Clock size={20} style={{ color: "#2563eb", marginTop: "2px" }} />
                  <div>
                    <span style={{ fontSize: "11px", fontWeight: "700", textTransform: "uppercase", color: "#2563eb" }}>Fecha Real Capturada</span>
                    <div style={{ fontSize: "15px", fontWeight: "800", color: "#0f172a" }}>
                      {new Date(datosAsistidos.fecha_foto).toLocaleDateString("es-EC", { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
                    </div>
                  </div>
                </div>
              </div>

              {/* Verified Confirmation Form */}
              <form className="dashboard-card form-card" onSubmit={handleConfirmarAsistidaSubmit} style={{ gap: "20px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#2563eb" }}>
                  <Sparkles size={22} />
                  <h2 style={{ fontSize: "18px", margin: 0, fontWeight: "800" }}>Asistente Digital de Registro</h2>
                </div>
                
                <div className="form-group">
                  <label>1. Identifica el Medidor en la Foto e Selecciona el Cliente *</label>
                  <select
                    required
                    value={asistenteForm.cuenta}
                    onChange={(e) => handleAsistenteCuentaChange(e.target.value)}
                    style={{ fontSize: "15px", padding: "12px" }}
                  >
                    <option value="">Buscar en la foto y elegir cliente...</option>
                    {datosAsistidos.medidores_disponibles.map(m => (
                      <option key={m.cuenta} value={m.cuenta}>
                        {m.cliente_nombre} — (Medidor Nro: {m.medidor})
                      </option>
                    ))}
                  </select>
                </div>

                {asistenteForm.cuenta && (
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", background: "rgba(226, 232, 240, 0.4)", padding: "14px", borderRadius: "14px" }}>
                    <div>
                      <span style={{ fontSize: "11px", color: "#64748b", fontWeight: "700" }}>Lectura Anterior:</span>
                      <div style={{ fontWeight: "700", color: "#0f172a" }}>
                        {datosAsistidos.medidores_disponibles.find(m => m.cuenta === asistenteForm.cuenta)?.ultima_lectura} kWh
                      </div>
                    </div>
                    <div>
                      <span style={{ fontSize: "11px", color: "#64748b", fontWeight: "700" }}>Medidor Físico:</span>
                      <div style={{ fontWeight: "700", color: "#0f172a" }}>
                        {datosAsistidos.medidores_disponibles.find(m => m.cuenta === asistenteForm.cuenta)?.medidor}
                      </div>
                    </div>
                  </div>
                )}

                <div className="form-group">
                  <label htmlFor="lectura-asistida-form">2. Digita o Confirma la Lectura de la Foto (kWh) *</label>
                  <input
                    id="lectura-asistida-form"
                    type="number"
                    step="0.01"
                    required
                    placeholder="Escribe la cifra marcada en la foto..."
                    value={asistenteForm.valor_lectura}
                    onChange={(e) => setAsistenteForm(prev => ({ ...prev, valor_lectura: e.target.value }))}
                    style={{ fontSize: "16px", padding: "12px", fontWeight: "700", color: "#2563eb" }}
                  />
                  {isLecturaOcr ? (
                    <span style={{ fontSize: "11px", color: "#10b981", marginTop: "4px", display: "flex", gap: "4px", alignItems: "center", fontWeight: "700" }}>
                      <CheckCircle size={12} />
                      <span>✓ Lectura leída directamente de la foto mediante OCR</span>
                    </span>
                  ) : (
                    <span style={{ fontSize: "11px", color: "#d97706", marginTop: "4px", display: "flex", gap: "4px", alignItems: "center", fontWeight: "600" }}>
                      <Sparkles size={12} />
                      <span>💡 Lectura sugerida por historial (el OCR no leyó la pantalla, digita el valor real de la foto)</span>
                    </span>
                  )}
                </div>

                <div className="form-group">
                  <label htmlFor="fecha-asistida-form">3. Fecha de Lectura</label>
                  <input
                    id="fecha-asistida-form"
                    type="date"
                    required
                    value={asistenteForm.fecha_lectura}
                    onChange={(e) => setAsistenteForm(prev => ({ ...prev, fecha_lectura: e.target.value }))}
                  />
                </div>

                <div style={{ display: "flex", gap: "12px", marginTop: "10px" }}>
                  <button type="button" className="btn-back" style={{ flex: 1, justifyContent: "center" }} onClick={() => setDatosAsistidos(null)}>
                    Cancelar
                  </button>
                  <button type="submit" className="btn-submit" style={{ flex: 2, margin: 0 }}>
                    Confirmar e Ingresar Registro
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* Historical Readings and alerts timeline */}
          <div className="dashboard-card" style={{ padding: "20px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <h3 style={{ margin: 0 }}>Historial de Monitoreo Semanal Prevenido</h3>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <label htmlFor="filtro-lecturas" style={{ fontSize: "12px" }}>Filtrar Cuenta:</label>
                <select
                  id="filtro-lecturas"
                  style={{ minWidth: "150px", padding: "6px 12px", fontSize: "12px" }}
                  value={cuentaLecturaFiltro}
                  onChange={(e) => setCuentaLecturaFiltro(e.target.value)}
                >
                  <option value="">Todas</option>
                  {cuentas.map(c => (
                    <option key={c.cuenta} value={c.cuenta}>
                      {c.cliente_nombre}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="table-container" style={{ maxHeight: "450px", overflowY: "auto" }}>
              <table>
                <thead>
                  <tr>
                    <th>Fecha de Toma</th>
                    <th>Cuenta / Cliente</th>
                    <th>Valor</th>
                    <th>Intervalo / Consumo</th>
                    <th>Promedio Diario</th>
                    <th>Histórico</th>
                    <th>Desviación</th>
                    <th>Alerta</th>
                    <th>Evidencia</th>
                  </tr>
                </thead>
                <tbody>
                  {lecturasSemanales.map((l) => (
                    <tr key={l.id}>
                      <td style={{ fontWeight: "600" }}>{l.fecha_lectura}</td>
                      <td>
                        <div style={{ fontWeight: "600" }}>
                          {cuentas.find(c => c.cuenta === l.cuenta)?.cliente_nombre || "—"}
                        </div>
                        <div style={{ fontSize: "11px", color: "#64748b" }}>Cuenta: {l.cuenta}</div>
                      </td>
                      <td style={{ fontFamily: "monospace", fontWeight: "700" }}>{l.valor_lectura} kWh</td>
                      <td>
                        {l.dias_transcurridos ? (
                          <>
                            <div style={{ fontWeight: "600" }}>{l.consumo_periodo} kWh</div>
                            <div style={{ fontSize: "11px", color: "#64748b" }}>en {l.dias_transcurridos} días</div>
                          </>
                        ) : (
                          <span style={{ color: "#64748b", fontSize: "11px" }}>(Primer ingreso)</span>
                        )}
                      </td>
                      <td style={{ fontWeight: "700" }}>
                        {l.promedio_diario ? `${l.promedio_diario} kWh/d` : "—"}
                      </td>
                      <td style={{ color: "#64748b" }}>
                        {l.promedio_diario_historico} kWh/d
                      </td>
                      <td style={{ 
                        fontWeight: "700", 
                        color: l.desviacion_porcentaje > 0 ? "#ef4444" : "#10b981" 
                      }}>
                        {l.desviacion_porcentaje > 0 ? `+${l.desviacion_porcentaje}%` : `${l.desviacion_porcentaje}%`}
                      </td>
                      <td>
                        <span className={`badge ${l.alerta_estado}`}>
                          {l.alerta_estado === "alerta" ? "🚨 ALERTA" : l.alerta_estado === "precaucion" ? "⚠️ Ajuste" : "Verde OK"}
                        </span>
                      </td>
                      <td>
                        {l.foto_nombre ? (
                          <a 
                            href={`http://127.0.0.1:8000/fotos/${l.foto_nombre}`} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="btn-link-foto"
                          >
                            Ver Foto
                          </a>
                        ) : (
                          <span style={{ color: "#64748b", fontSize: "11px" }}>Sin foto</span>
                        )}
                      </td>
                    </tr>
                  ))}
                  {lecturasSemanales.length === 0 && (
                    <tr>
                      <td colSpan="9" style={{ textAlign: "center", padding: "40px", color: "#64748b" }}>
                        No se han registrado lecturas semanales aún.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

        </section>
      )}
    </main>
  )
}
