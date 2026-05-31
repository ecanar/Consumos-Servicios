import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
})

export const getHealth = () => api.get('/health')

export const getKPIs = (cuenta) => api.get('/dashboard/kpis', { params: { cuenta } })

export const getConsumoMensual = (cuenta) => api.get('/dashboard/consumo-mensual', { params: { cuenta } })

export const getResumenCuentas = () => api.get('/dashboard/resumen-cuentas')

export const getComparativaAnual = (cuenta) => api.get('/dashboard/comparativa-anual', { params: { cuenta } })

export const getFacturas = (cuenta, skip = 0, limit = 100) => 
  api.get('/facturas/', { params: { cuenta, skip, limit } })

export const getCuentas = () => api.get('/facturas/cuentas')

// Nuevos endpoints de ingreso y monitoreo
export const subirFacturaPDF = (file) => {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/facturas/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export const getLecturasSemanales = (cuenta) => 
  api.get('/lecturas-semanales/', { params: { cuenta } })

export const registrarLecturaSemanal = (formData) => 
  api.post('/lecturas-semanales/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })

export const procesarFotoMedidor = (fotoFile) => {
  const formData = new FormData()
  formData.append('foto', fotoFile)
  return api.post('/lecturas-semanales/procesar-foto', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export const confirmarLecturaAsistida = (formData) => 
  api.post('/lecturas-semanales/confirmar-asistida', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })

export const eliminarLecturaSemanal = (id) => api.delete(`/lecturas-semanales/${id}`)
