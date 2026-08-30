import { useState, useEffect, useRef } from 'react'
import { Button } from '@/components/ui/button.jsx'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card.jsx'
import { Input } from '@/components/ui/input.jsx'
import { Label } from '@/components/ui/label.jsx'
import { Textarea } from '@/components/ui/textarea.jsx'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select.jsx'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs.jsx'
import { Plus, Trash2, FileText, Calculator, Download, Upload, Save, FileJson, Search, Database, LogOut, Users } from 'lucide-react'
import { DeParaPanel, DeParaPanelToggle } from '@/components/DeParaPanel.jsx'
import { CalculationsResults } from '@/components/CalculationsResults.jsx'
import { CatalogPanel } from '@/components/CatalogPanel.jsx'
import { CatalogEquipmentPicker, applyCatalogFieldsToItem } from '@/components/CatalogEquipmentPicker.jsx'
import { Login } from '@/components/Login.jsx'
import { UserManagement } from '@/components/UserManagement.jsx'
import { apiFetch, apiJson } from '@/utils/api.js'
import {
  fillGaps,
  mapClasse,
  mapLigacao,
  mapTensao,
  mergeFilled,
  parseTxtData,
  toIsoDate,
} from './utils/txtParser'
import './App.css'

import { buildLocalDeParaPreview } from './utils/deParaMapper'
import { getInitialTechnicalData, getInitialContractData, EXEMPLO_TEXTO_VALOR_PAGAMENTO_CONTRATO, contractFromLegacyTechnical } from './utils/formDefaults'
import { parseCoordinateText, syncTechnicalCoordinates } from './utils/coordinateUtils'
import { computeAreaArranjo } from './utils/areaUtils'
import { FiguraLocalizacaoPreview } from '@/components/FiguraLocalizacaoPreview.jsx'

function App() {
  const [activeTab, setActiveTab] = useState('entrada')
  const [txtInput, setTxtInput] = useState('')
  const [yamlInput, setYamlInput] = useState('')
  const [inputMode, setInputMode] = useState('txt')

  const [clientData, setClientData] = useState({
    // Dados Cadastrais
    client_name: '',
    cpf: '',
    rg: '',
    validade_cnh: '',
    data_nascimento: '',

    // Endereço
    logradouro: '',
    numero: '',
    complemento: '',
    bairro: '',
    cidade: '',
    uf: '',
    cep: '',

    // Unidade Consumidora
    consumer_unit: '',
    tensao_atendimento: '220V',
    tipo_ligacao: 'MONOFASICO',
    classe: 'RESIDENCIAL',

    // Contato
    telefone: '',
    email: ''
  })

  const [technicalData, setTechnicalData] = useState(getInitialTechnicalData)
  const [contractData, setContractData] = useState(getInitialContractData)
  const [cepLookupLoading, setCepLookupLoading] = useState(false)

  const [modules, setModules] = useState([
    {
      quantity: '',
      fabricante: '',
      model: '',
      power: '',
      voc: '',
      isc: '',
      vmpp: '',
      impp: '',
      eficiencia: '',
      comprimento_m: '',
      largura_m: '',
      area_modulo: '',
    }
  ])

  const [inverters, setInverters] = useState([
    {
      quantity: '',
      fabricante: '',
      model: '',
      power: '',
      tensao_nominal: '',
      corrente_nominal: '',
      mppt_min: '',
      mppt_max: '',
      eficiencia: ''
    }
  ])

  const [calculations, setCalculations] = useState(null)
  const [loading, setLoading] = useState(false)
  const [generatedFiles, setGeneratedFiles] = useState(null)
  const [outputDirectory, setOutputDirectory] = useState('')
  const [outputWarning, setOutputWarning] = useState('')
  const [aiStatus, setAiStatus] = useState({ ollama: false, gemini: false, primary: 'none' })
  const [deParaOpen, setDeParaOpen] = useState(true)
  const [deParaWidth, setDeParaWidth] = useState(460)
  const [deParaPreview, setDeParaPreview] = useState(null)
  const [deParaLoading, setDeParaLoading] = useState(false)
  const [deParaFilter, setDeParaFilter] = useState('')
  const [deParaError, setDeParaError] = useState('')
  const [demandModels, setDemandModels] = useState([])
  const [stringPreview, setStringPreview] = useState(null)
  const [stringPreviewLoading, setStringPreviewLoading] = useState(false)
  const [authUser, setAuthUser] = useState(null)
  const [authLoading, setAuthLoading] = useState(true)
  const [authStatus, setAuthStatus] = useState({ master_configured: false })
  /** Disjuntor informado manualmente ou via TXT — não sobrescrever ao mudar ligação/classe. */
  const disjuntorEntradaManual = useRef(false)

  const modulesAreaKey = modules
    .map((m) => `${m.quantity}|${m.area_modulo}|${m.comprimento_m}|${m.largura_m}`)
    .join(';')

  useEffect(() => {
    const computed = computeAreaArranjo(modules)
    if (computed === '') return
    setTechnicalData((prev) => {
      if (prev.area_arranjo === computed) return prev
      return { ...prev, area_arranjo: computed }
    })
  }, [modulesAreaKey])

  const handleLogout = async () => {
    try {
      await apiFetch('/auth/logout', { method: 'POST' })
    } catch {
      // ignore
    }
    setAuthUser(null)
  }

  const patchTechnicalCoordinates = (patch) => {
    setTechnicalData((prev) => syncTechnicalCoordinates(prev, patch))
  }

  const handleCoordenadasRawBlur = (raw) => {
    const parsed = parseCoordinateText(raw)
    patchTechnicalCoordinates({ ...parsed, coordenadas_raw: raw })
  }

  const syncCoordinatesFromFields = () => {
    setTechnicalData((prev) => syncTechnicalCoordinates(prev))
  }

  useEffect(() => {
    const onAuthRequired = () => setAuthUser(null)
    window.addEventListener('auth:required', onAuthRequired)
    return () => window.removeEventListener('auth:required', onAuthRequired)
  }, [])

  useEffect(() => {
    let cancelled = false
    const boot = async () => {
      try {
        const statusRes = await apiFetch('/auth/status')
        const statusData = await statusRes.json()
        if (!cancelled) setAuthStatus(statusData)

        const { response, data } = await apiJson('/auth/me')
        if (!cancelled && response.ok && data.authenticated) {
          setAuthUser(data.user)
        }
      } catch {
        if (!cancelled) setAuthUser(null)
      } finally {
        if (!cancelled) setAuthLoading(false)
      }
    }
    boot()
    return () => { cancelled = true }
  }, [])

  // Verificar status da IA após login
  useEffect(() => {
    if (!authUser) return undefined

    apiFetch('/ai-status')
      .then(res => res.json())
      .then(status => {
        setAiStatus({
          ...status,
          primary: status.primary || (status.ollama ? 'ollama' : status.gemini ? 'gemini' : 'none'),
        })
      })
      .catch(() => setAiStatus({ ollama: false, gemini: false, primary: 'none' }))

    apiFetch('/demanda-modelos')
      .then((res) => res.json())
      .then((data) => {
        if (data.success && Array.isArray(data.modelos)) {
          setDemandModels(data.modelos)
        }
      })
      .catch(() => setDemandModels([]))
  }, [authUser])

  const buildRequestPayload = (options = {}) => {
    const endereco_completo = [
      clientData.logradouro,
      clientData.numero ? `Nº ${clientData.numero}` : '',
      clientData.complemento,
      clientData.bairro,
      clientData.cidade && clientData.uf ? `${clientData.cidade}/${clientData.uf}` : '',
    ].filter(Boolean).join(', ')

    return {
      client: clientData,
      contract: contractData,
      technical: technicalData,
      client_name: clientData.client_name,
      client_address: endereco_completo,
      consumer_unit: clientData.consumer_unit,
      client_cpf: clientData.cpf,
      grid_voltage: clientData.tensao_atendimento,
      ...clientData,
      ...contractData,
      ...technicalData,
      endereco_completo,
      modules,
      inverters,
      calculations,
      enrich_specs: options.enrich_specs ?? false,
    }
  }

  const lookupAddress = async () => {
    const cepDigits = (clientData.cep || '').replace(/\D/g, '')
    const hasCep = cepDigits.length === 8
    const hasAddress = clientData.logradouro && clientData.cidade && clientData.uf

    if (!hasCep && !hasAddress) {
      alert('Informe o CEP ou logradouro + cidade + UF para buscar.')
      return
    }

    setCepLookupLoading(true)
    try {
      const response = await apiFetch('/lookup-address', {
        method: 'POST',
        body: JSON.stringify({
          cep: clientData.cep,
          logradouro: clientData.logradouro,
          bairro: clientData.bairro,
          cidade: clientData.cidade,
          uf: clientData.uf,
        }),
      })
      const data = await response.json()
      if (response.ok && data.success && data.address) {
        const addr = data.address
        setClientData((prev) => ({
          ...prev,
          cep: addr.cep || prev.cep,
          logradouro: addr.logradouro || prev.logradouro,
          bairro: addr.bairro || prev.bairro,
          cidade: addr.cidade || prev.cidade,
          uf: addr.uf || prev.uf,
          complemento: addr.complemento || prev.complemento,
        }))
      } else {
        alert(data.error || 'Endereço ou CEP não encontrado.')
      }
    } catch (error) {
      alert('Erro ao buscar endereço. Verifique se o backend está rodando.')
      console.error(error)
    } finally {
      setCepLookupLoading(false)
    }
  }

  const estimateCargaKw = () => {
    const demanda = parseFloat(String(technicalData.demanda_alvo_kw || '').replace(',', '.'))
    if (Number.isFinite(demanda) && demanda > 0) return demanda
    let potMod = 0
    for (const m of modules) {
      const q = parseInt(String(m.quantity || '').trim(), 10) || 0
      const p = parseFloat(String(m.power || '').replace(',', '.')) || 0
      if (q > 0 && p > 0) potMod += (q * p) / 1000
    }
    if (potMod > 0) return Math.round(potMod * 10) / 10
    let potInv = 0
    for (const inv of inverters) {
      const q = parseInt(String(inv.quantity || '').trim(), 10) || 0
      const p = parseFloat(String(inv.power || '').replace(',', '.')) || 0
      if (q > 0 && p > 0) potInv += q * p
    }
    return potInv > 0 ? Math.round(potInv * 10) / 10 : undefined
  }

  const syncPadraoEntrada = async (uf, tipoLigacao, classe, cargaKw) => {
    const ufVal = (uf || 'GO').trim().toUpperCase()
    const tipo = tipoLigacao || 'MONOFASICO'
    const cls = classe || 'RESIDENCIAL'
    const carga = cargaKw ?? estimateCargaKw()
    try {
      const qs = new URLSearchParams({
        uf: ufVal,
        tipo_ligacao: tipo,
        classe: cls,
      })
      if (carga != null && carga > 0) {
        qs.set('carga_kw', String(carga))
      }
      const res = await apiFetch(`/normas?${qs}`)
      const data = await res.json()
      if (!data.success) return
      const padrao = data.padrao_entrada
      if (padrao?.tensao_v) {
        setClientData((prev) => ({
          ...prev,
          tensao_atendimento: padrao.tensao_v,
        }))
      }
      const disjA = padrao?.disjuntor_a ?? 40
      if (!disjuntorEntradaManual.current) {
        setTechnicalData((prev) => ({
          ...prev,
          disjuntor_entrada: String(disjA),
          ...(padrao?.bitola_cabo_padrao_mm2 && !prev.bitola_cabo_padrao
            ? { bitola_cabo_padrao: padrao.bitola_cabo_padrao_mm2 }
            : {}),
          ...(padrao?.curva_disjuntor && !prev.curva_disjuntor
            ? { curva_disjuntor: padrao.curva_disjuntor }
            : {}),
        }))
      }
    } catch {
      if (!disjuntorEntradaManual.current) {
        setTechnicalData((prev) => ({
          ...prev,
          disjuntor_entrada: prev.disjuntor_entrada || '40',
        }))
      }
    }
  }

  const suggestTensao = (uf, tipoLigacao) => syncPadraoEntrada(uf, tipoLigacao, clientData.classe)

  const cargaKwKey = `${technicalData.demanda_alvo_kw}|${modulesAreaKey}|${inverters.map((i) => `${i.quantity}|${i.power}`).join(';')}`

  useEffect(() => {
    if (!authUser) return
    syncPadraoEntrada(clientData.uf, clientData.tipo_ligacao, clientData.classe)
  }, [authUser, clientData.uf, clientData.tipo_ligacao, clientData.classe, cargaKwKey])

  const normalizeConsumerUnit = (value) => {
    const digits = String(value || '').replace(/\D/g, '')
    if (digits.length >= 20 && digits.length % 2 === 0) {
      const half = digits.length / 2
      if (digits.slice(0, half) === digits.slice(half)) {
        return digits.slice(0, half)
      }
    }
    return digits
  }

  const fetchDeParaPreview = async () => {
    const local = buildLocalDeParaPreview(clientData, contractData, technicalData, modules, inverters)
    setDeParaPreview(local)
    setDeParaLoading(true)
    setDeParaError('')
    try {
      const response = await apiFetch('/preview-de-para', {
        method: 'POST',
        body: JSON.stringify(buildRequestPayload({ enrich_specs: false })),
      })
      const data = await response.json()
      if (response.ok && data.success) {
        setDeParaPreview({ ...data, source: 'server' })
      } else {
        setDeParaError(
          response.status === 404
            ? 'Backend desatualizado — reinicie start_backend.bat (preview local ativo).'
            : (data.error || `Erro ${response.status} ao carregar preview completo.`),
        )
      }
    } catch (error) {
      setDeParaError('Sem conexão com o backend — exibindo preview local do formulário.')
      console.error('Erro ao carregar DE/PARA:', error)
    } finally {
      setDeParaLoading(false)
    }
  }

  useEffect(() => {
    if (!deParaOpen) return undefined
    setDeParaPreview(buildLocalDeParaPreview(clientData, contractData, technicalData, modules, inverters))
    const timer = setTimeout(() => {
      fetchDeParaPreview()
    }, 400)
    return () => clearTimeout(timer)
  }, [deParaOpen, clientData, contractData, technicalData, modules, inverters])

  const applyLocalParse = (parsed, aiPatch = null) => {
    const aiClient = aiPatch?.client || {}
    const aiTechnical = aiPatch?.technical || {}

    if (aiClient.rg && /^\d{1,2}[/.\\-]\d{1,2}[/.\\-]\d{2,4}$/.test(String(aiClient.rg).trim())) {
      aiClient.rg = ''
    }
    if (aiClient.data_nascimento) aiClient.data_nascimento = toIsoDate(aiClient.data_nascimento)
    if (aiClient.validade_cnh) aiClient.validade_cnh = toIsoDate(aiClient.validade_cnh)
    if (aiClient.tensao_atendimento) aiClient.tensao_atendimento = mapTensao(aiClient.tensao_atendimento)
    if (aiClient.tipo_ligacao) aiClient.tipo_ligacao = mapLigacao(aiClient.tipo_ligacao)
    if (aiClient.classe) aiClient.classe = mapClasse(aiClient.classe)

    setClientData((prev) => fillGaps(mergeFilled(prev, parsed.client), aiClient))
    setTechnicalData((prev) => fillGaps(mergeFilled(prev, parsed.technical), aiTechnical))
    if (parsed.technical?.disjuntor_entrada || aiTechnical.disjuntor_entrada) {
      disjuntorEntradaManual.current = true
    }
    setContractData((prev) => fillGaps(mergeFilled(prev, parsed.contract || {}), aiPatch?.contract || {}))

    const mergeEquip = (localList, aiList, blank) => {
      const local = localList?.length ? localList : [blank]
      if (!aiList?.length) return local
      return local.map((item, i) => fillGaps(item, aiList[i] || {}))
    }

    setModules(mergeEquip(parsed.modules, aiPatch?.modules, {
      quantity: '', fabricante: '', model: '', power: '',
      voc: '', isc: '', vmpp: '', impp: '', eficiencia: '',
    }))
    setInverters(mergeEquip(parsed.inverters, aiPatch?.inverters, {
      quantity: '', fabricante: '', model: '', power: '',
      tensao_nominal: '', corrente_nominal: '', mppt_min: '', mppt_max: '', eficiencia: '',
    }))
  }

  const handleParseTxt = async () => {
    if (!txtInput.trim()) {
      alert('Cole o conteúdo do arquivo TXT primeiro!')
      return
    }

    setLoading(true)
    const parsed = parseTxtData(txtInput)

    if (aiStatus.primary === 'none') {
      applyLocalParse(parsed)
      setActiveTab('cliente')
      setLoading(false)
      alert('Dados importados pelo parser local.\n\nRevise e complete os campos vazios (bairro não vinha neste TXT).')
      return
    }

    try {
      const response = await apiFetch('/analyze-text', {
        method: 'POST',
        body: JSON.stringify({ text: txtInput }),
      })

      if (response.ok) {
        const result = await response.json()
        const ai = result.data || {}
        const uc = ai.unidade_consumidora || {}
        const tech = ai.dados_tecnicos || {}

        applyLocalParse(parsed, {
          client: {
            client_name: ai.cliente?.nome,
            cpf: ai.cliente?.cpf,
            rg: ai.cliente?.rg,
            validade_cnh: ai.cliente?.validade_cnh,
            data_nascimento: ai.cliente?.data_nascimento,
            telefone: ai.cliente?.telefone,
            email: ai.cliente?.email,
            logradouro: ai.cliente?.logradouro,
            numero: ai.cliente?.numero,
            complemento: ai.cliente?.complemento,
            bairro: ai.cliente?.bairro,
            cidade: ai.cliente?.cidade,
            uf: ai.cliente?.uf,
            cep: ai.cliente?.cep,
            consumer_unit: uc.numero || uc.numero_uc,
            tensao_atendimento: uc.tensao_atendimento,
            tipo_ligacao: uc.tipo_ligacao,
            classe: uc.classe,
          },
          technical: {
            disjuntor_entrada: uc.disjuntor_entrada || tech.disjuntor_entrada,
            bitola_cabo_ca: tech.bitola_cabo_ca,
            bitola_cabo_cc: tech.bitola_cabo_cc,
            bitola_cabo_padrao: tech.bitola_cabo_padrao,
            curva_disjuntor: tech.curva_disjuntor,
            dps_tipo: tech.dps_tipo,
            dps_classe: tech.dps_classe,
            tipo_aterramento: tech.tipo_aterramento,
            resistencia_aterramento: tech.resistencia_aterramento,
            coordenada_utm_x: tech.coordenada_utm_x,
            coordenada_utm_y: tech.coordenada_utm_y,
            fuso_utm: tech.fuso_utm,
            latitude: tech.latitude,
            longitude: tech.longitude,
            num_poste: tech.num_poste,
            tipo_arranjo: tech.tipo_arranjo,
            area_arranjo: tech.area_arranjo,
            data_operacao: tech.data_operacao,
          },
          modules: (ai.modulos || []).map((m) => ({
            quantity: m.quantidade || '',
            fabricante: m.fabricante || '',
            model: m.modelo || '',
            power: m.potencia || '',
            voc: m.voc || '',
            isc: m.isc || '',
            vmpp: m.vmpp || '',
            impp: m.impp || '',
            eficiencia: m.eficiencia || '',
          })),
          inverters: (ai.inversores || []).map((inv) => ({
            quantity: inv.quantidade || '',
            fabricante: inv.fabricante || '',
            model: inv.modelo || '',
            power: inv.potencia || '',
            tensao_nominal: inv.tensao_nominal || '',
            corrente_nominal: inv.corrente_nominal || '',
            mppt_min: inv.mppt_min || '',
            mppt_max: inv.mppt_max || '',
            eficiencia: inv.eficiencia || '',
          })),
        })

        setActiveTab('cliente')
        alert('Dados importados pelo parser De/Para. A IA só preencheu campos que ainda estavam vazios.\n\nRevise bairro (se não veio no TXT) e o restante.')
      } else {
        applyLocalParse(parsed)
        setActiveTab('cliente')
        alert('Dados importados pelo parser local.\n\nRevise e complete os campos vazios.')
      }
    } catch (error) {
      console.error('Erro ao analisar texto:', error)
      applyLocalParse(parsed)
      setActiveTab('cliente')
      alert('Dados importados pelo parser local.\n\nRevise e complete os campos vazios.')
    } finally {
      setLoading(false)
    }
  }

  const handleLoadYamlTemplate = async () => {
    try {
      const response = await apiFetch('/yaml/template')
      const data = await response.json()
      if (response.ok && data.success) {
        setYamlInput(data.content)
        setInputMode('yaml')
        setActiveTab('entrada')
      } else {
        alert(data.error || 'Erro ao carregar modelo YAML.')
      }
    } catch (error) {
      console.error(error)
      alert('Erro ao carregar modelo. Verifique se o backend está rodando.')
    }
  }

  const handleParseYaml = async () => {
    if (!yamlInput.trim()) {
      alert('Cole o conteúdo YAML primeiro!')
      return
    }

    setLoading(true)
    try {
      const response = await apiFetch('/import-yaml', {
        method: 'POST',
        body: JSON.stringify({ yaml: yamlInput }),
      })
      const data = await response.json()

      if (response.ok && data.success && data.parsed) {
        applyLocalParse(data.parsed)
        setActiveTab('cliente')
        const catalogMsg = data.catalog_notes?.length
          ? `\n\nEnriquecido pelo catálogo:\n• ${data.catalog_notes.join('\n• ')}`
          : ''
        alert(`YAML importado com sucesso.${catalogMsg}\n\nRevise o painel DE/PARA e complete campos restantes.`)
      } else {
        alert(data.error || 'Erro ao importar YAML.')
      }
    } catch (error) {
      console.error(error)
      alert('Erro ao conectar com o servidor.')
    } finally {
      setLoading(false)
    }
  }

  const handleExportYaml = async () => {
    try {
      const response = await apiFetch('/export-yaml', {
        method: 'POST',
        body: JSON.stringify(buildRequestPayload()),
      })
      const data = await response.json()

      if (response.ok && data.success) {
        setYamlInput(data.yaml)
        setInputMode('yaml')
        setActiveTab('entrada')
        if (navigator.clipboard?.writeText) {
          await navigator.clipboard.writeText(data.yaml)
          alert('YAML exportado e copiado para a área de transferência.')
        } else {
          alert('YAML exportado — copie manualmente da aba Entrada → YAML.')
        }
      } else {
        alert(data.error || 'Erro ao exportar YAML.')
      }
    } catch (error) {
      console.error(error)
      alert('Erro ao exportar YAML.')
    }
  }

  // Salvar formulário em JSON
  const handleSaveForm = async () => {
    const formData = {
      timestamp: new Date().toISOString(),
      client: clientData,
      contract: contractData,
      technical: technicalData,
      modules,
      inverters,
      calculations
    }

    try {
      const response = await apiFetch('/save-form', {
        method: 'POST',
        body: JSON.stringify(formData)
      })

      const result = await response.json()

      if (response.ok) {
        alert(`Formulário salvo em: ${result.filename}`)
      } else {
        alert(`Erro ao salvar: ${result.error}`)
      }
    } catch (error) {
      console.error('Erro ao salvar formulário:', error)

      // Fallback: download do JSON
      const blob = new Blob([JSON.stringify(formData, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `formulario_${new Date().getTime()}.json`
      a.click()
      URL.revokeObjectURL(url)

      alert('Formulário baixado como arquivo JSON')
    }
  }

  // Carregar formulário de JSON
  const handleLoadForm = async (event) => {
    const file = event.target.files[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target.result)

        if (data.client) setClientData(data.client)
        if (data.contract) {
          setContractData(data.contract)
        } else if (data.technical) {
          setContractData((prev) => fillGaps(prev, contractFromLegacyTechnical(data.technical)))
        }
        if (data.technical) setTechnicalData(data.technical)
        if (data.modules) setModules(data.modules)
        if (data.inverters) setInverters(data.inverters)
        if (data.calculations) setCalculations(data.calculations)

        alert('Formulário carregado com sucesso!')
      } catch (error) {
        alert('Erro ao carregar arquivo JSON: ' + error.message)
      }
    }
    reader.readAsText(file)
  }

  const addModule = () => {
    setModules([...modules, {
      quantity: '',
      fabricante: '',
      model: '',
      power: '',
      voc: '',
      isc: '',
      vmpp: '',
      impp: '',
      eficiencia: '',
      comprimento_m: '',
      largura_m: '',
      area_modulo: '',
    }])
  }

  const removeModule = (index) => {
    setModules(modules.filter((_, i) => i !== index))
  }

  const updateModule = (index, field, value) => {
    const updated = modules.map((module, i) =>
      i === index ? { ...module, [field]: value } : module
    )
    setModules(updated)
  }

  const applyCatalogToModule = (index, fields) => {
    setModules((prev) => prev.map((item, i) => (
      i === index ? applyCatalogFieldsToItem(item, fields) : item
    )))
  }

  const addInverter = () => {
    setInverters([...inverters, {
      quantity: '',
      fabricante: '',
      model: '',
      power: '',
      tensao_nominal: '',
      corrente_nominal: '',
      mppt_min: '',
      mppt_max: '',
      eficiencia: ''
    }])
  }

  const removeInverter = (index) => {
    setInverters(inverters.filter((_, i) => i !== index))
  }

  const updateInverter = (index, field, value) => {
    const updated = inverters.map((inverter, i) =>
      i === index ? { ...inverter, [field]: value } : inverter
    )
    setInverters(updated)
  }

  const applyCatalogToInverter = (index, fields) => {
    const { strings_por_mppt_suggested, strings_por_mppt_json, ...invFields } = fields
    setInverters((prev) => prev.map((item, i) => (
      i === index ? applyCatalogFieldsToItem(item, invFields) : item
    )))
    setTechnicalData((prev) => ({
      ...prev,
      ...(invFields.num_mppt ? { num_mppt: invFields.num_mppt } : {}),
      ...(invFields.tipo_inversor ? { tipo_inversor: invFields.tipo_inversor } : {}),
      ...(strings_por_mppt_suggested ? { strings_por_mppt: strings_por_mppt_suggested } : {}),
    }))
  }

  const previewStringLayout = async () => {
    setStringPreviewLoading(true)
    setStringPreview(null)
    try {
      const requestData = {
        client: clientData,
        technical: technicalData,
        modules,
        inverters,
        demanda_alvo_kw: technicalData.demanda_alvo_kw,
        demand_table_ai: technicalData.demand_table_ai,
        demanda_modelo_id: technicalData.demanda_modelo_id,
      }
      const response = await apiFetch('/calculate-system', {
        method: 'POST',
        body: JSON.stringify(requestData),
      })
      const data = await response.json()
      if (response.ok && data.success) {
        const dc = data.calculations?.dc_strings
        setStringPreview(dc || null)
        if (dc) {
          setTechnicalData((prev) => ({
            ...prev,
            ...(dc.suggested_modulos_por_string
              ? { modulos_por_string: String(dc.suggested_modulos_por_string) }
              : {}),
            ...(dc.suggested_strings_por_mppt
              ? { strings_por_mppt: String(dc.suggested_strings_por_mppt) }
              : {}),
            ...(dc.num_mppt_per_inverter
              ? { num_mppt: String(dc.num_mppt_per_inverter) }
              : {}),
            ...(dc.topology === 'micro'
              ? { tipo_inversor: 'MICRO' }
              : dc.topology === 'string'
                ? { tipo_inversor: 'STRING' }
                : {}),
          }))
        }
      } else {
        alert('Erro ao calcular strings: ' + (data.error || 'Erro desconhecido'))
      }
    } catch {
      alert('Erro ao conectar com o servidor')
    } finally {
      setStringPreviewLoading(false)
    }
  }

  const calculateSystem = async () => {
    setLoading(true)
    try {
      const requestData = {
        client: clientData,
        technical: technicalData,
        modules,
        inverters,
        demanda_alvo_kw: technicalData.demanda_alvo_kw,
        demand_table_ai: technicalData.demand_table_ai,
        demanda_modelo_id: technicalData.demanda_modelo_id,
      }

      const response = await apiFetch('/calculate-system', {
        method: 'POST',
        body: JSON.stringify(requestData),
      })

      const data = await response.json()

      if (response.ok && data.success) {
        setCalculations(data.calculations)
        if (data.modules?.length) {
          setModules((prev) => prev.map((m, i) => mergeFilled(m, data.modules[i] || {})))
        }
        if (data.inverters?.length) {
          setInverters((prev) => prev.map((inv, i) => mergeFilled(inv, data.inverters[i] || {})))
        }
        const calc = data.calculations
        const dc = calc?.dc_strings
        setTechnicalData((prev) => ({
          ...prev,
          tabela_demanda_text: calc.demand_table?.memorial_text || prev.tabela_demanda_text,
          tabela_demanda_json: calc.demand_table
            ? JSON.stringify(calc.demand_table)
            : prev.tabela_demanda_json,
          ...(dc?.suggested_modulos_por_string && !prev.modulos_por_string
            ? { modulos_por_string: String(dc.suggested_modulos_por_string) }
            : {}),
          ...(dc?.suggested_strings_por_mppt && !prev.strings_por_mppt
            ? { strings_por_mppt: String(dc.suggested_strings_por_mppt) }
            : {}),
          ...(dc?.num_mppt_per_inverter && !prev.num_mppt
            ? { num_mppt: String(dc.num_mppt_per_inverter) }
            : {}),
        }))
        const cableWarnings = calc.cable_warnings || []
        if (cableWarnings.length) {
          alert(
            'Atenção — conferir cabos (valores do formulário mantidos):\n\n'
            + cableWarnings.map((w) => `• ${w}`).join('\n')
          )
        }
        setActiveTab('calculos')
      } else {
        alert('Erro ao calcular: ' + (data.error || 'Erro desconhecido'))
      }
    } catch (error) {
      console.error('Erro:', error)
      alert('Erro ao conectar com o servidor')
    } finally {
      setLoading(false)
    }
  }

  const applyDemandTableToForm = (demand) => {
    setTechnicalData((prev) => ({
      ...prev,
      demanda_alvo_kw: String(demand.target_kw),
      tabela_demanda_text: demand.memorial_text,
      tabela_demanda_json: JSON.stringify(demand),
      demanda_modelo_id: demand.modelo_id || prev.demanda_modelo_id,
    }))
    alert('Tabela de demanda aplicada. Na geração do memorial será inserida como tabela Word formatada.')
  }

  const applyDemandModel = async (modelId) => {
    if (!modelId) return
    setLoading(true)
    try {
      const response = await apiFetch(`/demanda-modelos/${modelId}/gerar`, {
        method: 'POST',
        body: JSON.stringify({
          client: clientData,
          apply_form: true,
          demanda_notas: technicalData.demanda_notas,
        }),
      })
      const data = await response.json()
      if (!response.ok || !data.success) {
        alert('Erro ao aplicar modelo: ' + (data.error || 'Erro desconhecido'))
        return
      }
      const patch = data.form_patch || {}
      const table = data.demand_table
      if (patch.classe) {
        setClientData((prev) => ({ ...prev, classe: patch.classe }))
      }
      if (patch.tipo_ligacao) {
        setClientData((prev) => ({
          ...prev,
          tipo_ligacao: patch.tipo_ligacao,
          tensao_atendimento: patch.tensao_atendimento || prev.tensao_atendimento,
        }))
      }
      setTechnicalData((prev) => ({
        ...prev,
        demanda_modelo_id: modelId,
        demanda_alvo_kw: patch.demanda_alvo_kw || String(table?.target_kw ?? prev.demanda_alvo_kw),
        disjuntor_entrada: patch.disjuntor_entrada || prev.disjuntor_entrada,
        tabela_demanda_text: table?.memorial_text || prev.tabela_demanda_text,
        tabela_demanda_json: table ? JSON.stringify(table) : prev.tabela_demanda_json,
      }))
      setCalculations((prev) => (prev ? { ...prev, demand_table: table } : prev))
      alert(`Modelo aplicado: ${table?.modelo_nome || modelId}\nDemanda calculada: ${table?.calculated_d_kw ?? '—'} kW`)
    } catch (error) {
      alert('Erro ao aplicar modelo: ' + error.message)
    } finally {
      setLoading(false)
    }
  }

  const handleEnrichEquipment = async () => {
    if (aiStatus.primary === 'none') {
      alert('Configure Ollama local ou GEMINI_API_KEY no arquivo .env (raiz do projeto, nunca no frontend).')
      return
    }

    setLoading(true)
    try {
      const response = await apiFetch('/enrich-equipment', {
        method: 'POST',
        body: JSON.stringify({ modules, inverters }),
      })
      const data = await response.json()

      if (response.ok && data.success) {
        if (data.modules?.length) setModules(data.modules)
        if (data.inverters?.length) setInverters(data.inverters)
        if (data.enriched) {
          const src = (data.sources || []).join(', ') || aiStatus.primary
          alert(`Especificações buscadas via ${src}.\nRevise Voc, Isc e faixa MPPT antes de gerar.`)
        } else {
          alert(data.hint || 'Nenhum campo novo preenchido. Campos já tinham valor ou a IA não respondeu.')
        }
      } else {
        alert('Não foi possível buscar specs: ' + (data.error || 'erro desconhecido'))
      }
    } catch (error) {
      alert('Erro ao buscar specs: ' + error.message)
    } finally {
      setLoading(false)
    }
  }

  const generateDocuments = async () => {
    if (!contractData.numero_contrato?.trim()) {
      alert('Informe o número do contrato na aba Contrato.\n\nA pasta no Google Drive será: número + 1º e 2º nome (ex.: 80 - João Silva).')
      setActiveTab('contrato')
      return
    }

    setLoading(true)
    try {
      const requestData = buildRequestPayload({ enrich_specs: false })

      const response = await apiFetch('/fill-documents', {
        method: 'POST',
        body: JSON.stringify(requestData)
      })

      const data = await response.json()

      if (response.ok) {
        setGeneratedFiles(data.files)
        setOutputDirectory(data.output_directory || '')
        setOutputWarning(data.output_warning || '')
        if (deParaOpen) fetchDeParaPreview()
        const dest = data.output_directory ? `\n\nPasta:\n${data.output_directory}` : ''
        const warn = data.output_warning ? `\n\n⚠ ${data.output_warning}` : ''
        alert(`Documentos gerados com sucesso!${dest}${warn}`)
      } else {
        alert('Erro ao gerar documentos: ' + (data.error || 'Erro desconhecido'))
      }
    } catch (error) {
      console.error('Erro:', error)
      alert('Erro ao conectar com o servidor: ' + error.message)
    } finally {
      setLoading(false)
    }
  }

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
        <p className="text-gray-600">Verificando sessão...</p>
      </div>
    )
  }

  if (!authUser) {
    const confirmToken = new URLSearchParams(window.location.search).get('confirm_device')
    return (
      <Login
        authStatus={authStatus}
        confirmToken={confirmToken}
        onSuccess={(user) => {
          setAuthUser(user)
          if (confirmToken) {
            window.history.replaceState({}, '', window.location.pathname)
          }
        }}
      />
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-8">
      <div
        className="max-w-7xl mx-auto transition-[margin] duration-200"
        style={{ marginRight: deParaOpen ? deParaWidth : 0 }}
      >
        <header className="flex items-start gap-5 mb-8">
          <img
            src="/brand/logo-app-96.png"
            srcSet="/brand/logo-app-96.png 1x, /brand/icon-192.png 2x"
            width={96}
            height={96}
            alt="PIENG Soluções Energéticas"
            className="h-20 w-20 sm:h-24 sm:w-24 shrink-0 object-contain"
          />
          <div className="pt-1 sm:pt-2 min-w-0">
            <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-2 text-left">
              Automação Equatorial Energia
            </h1>
            <p className="text-gray-600 text-left text-sm sm:text-base">
              Sistema de Preenchimento de Documentos PRODIST 3 - Geração Distribuída
            </p>
            <p className="text-xs text-gray-500 mt-1">
              {authUser.username}
              {authUser.role === 'master' ? ' · administrador' : ' · operador'}
            </p>
          </div>
        </header>

        {/* Botões de Ação Globais */}
        <div className="flex gap-4 justify-end mb-6 flex-wrap">
          <Button variant="outline" onClick={handleLogout}>
            <LogOut className="mr-2 h-4 w-4" />
            Sair
          </Button>
          {!deParaOpen && <DeParaPanelToggle onToggle={() => setDeParaOpen(true)} />}
          <Button
            variant={activeTab === 'catalogo' ? 'default' : 'outline'}
            onClick={() => setActiveTab('catalogo')}
          >
            <Database className="mr-2 h-4 w-4" />
            Catálogo SQL
          </Button>
          <Button variant="outline" onClick={fetchDeParaPreview} disabled={deParaLoading}>
            Atualizar DE/PARA
          </Button>
          <Button variant="outline" onClick={handleExportYaml}>
            <FileJson className="mr-2 h-4 w-4" />
            Exportar YAML
          </Button>
          <Button variant="outline" onClick={handleSaveForm}>
            <Save className="mr-2 h-4 w-4" />
            Salvar Formulário
          </Button>
          <label>
            <Button variant="outline" asChild>
              <span>
                <Upload className="mr-2 h-4 w-4" />
                Carregar Formulário
              </span>
            </Button>
            <input
              type="file"
              accept=".json"
              className="hidden"
              onChange={handleLoadForm}
            />
          </label>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className={`grid w-full ${authUser.role === 'master' ? 'grid-cols-7' : 'grid-cols-6'}`}>
            <TabsTrigger value="entrada">📄 Entrada</TabsTrigger>
            <TabsTrigger value="cliente">👤 Cliente</TabsTrigger>
            <TabsTrigger value="equipamentos">⚡ Equipamentos</TabsTrigger>
            <TabsTrigger value="contrato">📋 Contrato</TabsTrigger>
            <TabsTrigger value="tecnico">🔧 Dados Técnicos</TabsTrigger>
            <TabsTrigger value="calculos">📊 Cálculos</TabsTrigger>
            {authUser.role === 'master' && (
              <TabsTrigger value="usuarios">
                <Users className="inline h-4 w-4 mr-1" />
                Usuários
              </TabsTrigger>
            )}
          </TabsList>

          {/* ABA 1: ENTRADA TXT / YAML */}
          <TabsContent value="entrada">
            <Card>
              <CardHeader>
                <CardTitle>Importar Dados — TXT ou YAML</CardTitle>
                <CardDescription>
                  TXT: formato De/Para com rótulos livres. YAML: estrutura fixa para preenchimento
                  manual ou com IA externa (veja dados/YAML_INSTRUCOES.md).
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Tabs value={inputMode} onValueChange={setInputMode} className="w-full">
                  <TabsList className="mb-4">
                    <TabsTrigger value="txt">TXT (De/Para)</TabsTrigger>
                    <TabsTrigger value="yaml">YAML (estruturado)</TabsTrigger>
                  </TabsList>

                  <TabsContent value="txt">
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="txt-input">Conteúdo do Arquivo TXT</Label>
                    <Textarea
                      id="txt-input"
                      placeholder={`Exemplo:
Nome: João Silva
CPF: 123.456.789-00
Endereço: Rua Pernambuco, Nº 123, Q. F, L. 5/6
Bairro: Centro
Cidade/UF: Anápolis/GO
CEP: 75000-000
Unidade Consumidora: 704.212.012-65
Tensão da rede: 220/380 V
Quantidade de painéis: 32 unidades
Potência dos painéis: 680 W
Número do Contrato: 122/2026
Texto Valor Pagamento Contrato: • O investimento objeto deste contrato é de R$ 12.000,00.
Cidade do Documento: Goiânia
Data do Documento: 15/08/2026
...`}
                      rows={20}
                      value={txtInput}
                      onChange={(e) => setTxtInput(e.target.value)}
                      className="font-mono text-sm"
                    />
                  </div>

                  <div className="flex gap-4">
                    <Button onClick={handleParseTxt} disabled={loading} className="flex-1">
                      <FileText className="mr-2 h-4 w-4" />
                      {loading ? 'Analisando com IA...' : 'Importar Dados do TXT'}
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => setTxtInput('')}
                    >
                      Limpar
                    </Button>
                  </div>

                  {/* Status da IA */}
                  <div className={`p-3 rounded-lg border ${
                    aiStatus.primary === 'ollama' ? 'bg-green-50 border-green-200' :
                    aiStatus.primary === 'gemini' ? 'bg-blue-50 border-blue-200' :
                    'bg-yellow-50 border-yellow-200'
                  }`}>
                    <div className="flex items-center gap-2">
                      <span className="text-lg">🤖</span>
                      <div className="flex-1">
                        <p className="text-sm font-semibold">
                          {aiStatus.primary === 'ollama' ? '✅ IA Local Ativa (Ollama - DeepSeek R1)' :
                           aiStatus.primary === 'gemini' ? '🌐 IA Cloud Ativa (Google Gemini)' :
                           '⚠️ IA Desativada - Usando Parser Local'}
                        </p>
                        <p className="text-xs text-gray-600 mt-1">
                          {aiStatus.primary === 'ollama' ? 'Análise 100% local e gratuita' :
                           aiStatus.primary === 'gemini' ? 'Análise via Google Cloud' :
                           'Extração baseada em regras De/Para'}
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                    <h4 className="font-semibold mb-2 text-blue-900">💡 Dica:</h4>
                    <p className="text-sm text-blue-800">
                      O sistema reconhece automaticamente diversos formatos de rótulos usando
                      {aiStatus.primary !== 'none' ? ' Inteligência Artificial' : ' sistema De/Para'}.
                      Exemplo: "UC", "Unidade Consumidora", "Número da UC" são todos
                      reconhecidos como o mesmo campo.
                    </p>
                  </div>
                </div>
                  </TabsContent>

                  <TabsContent value="yaml">
                    <div className="space-y-4">
                      <div>
                        <Label htmlFor="yaml-input">Conteúdo YAML do Projeto</Label>
                        <Textarea
                          id="yaml-input"
                          placeholder="# Cole aqui o YAML preenchido (dados/projeto_padrao.yaml como base)"
                          rows={20}
                          value={yamlInput}
                          onChange={(e) => setYamlInput(e.target.value)}
                          className="font-mono text-sm"
                        />
                      </div>

                      <div className="flex gap-4 flex-wrap">
                        <Button variant="outline" onClick={handleLoadYamlTemplate}>
                          <FileText className="mr-2 h-4 w-4" />
                          Carregar modelo
                        </Button>
                        <Button onClick={handleParseYaml} disabled={loading} className="flex-1 min-w-[200px]">
                          <Upload className="mr-2 h-4 w-4" />
                          {loading ? 'Importando...' : 'Importar YAML'}
                        </Button>
                        <Button variant="outline" onClick={() => setYamlInput('')}>
                          Limpar
                        </Button>
                      </div>

                      <div className="bg-emerald-50 p-4 rounded-lg border border-emerald-200">
                        <h4 className="font-semibold mb-2 text-emerald-900">YAML + IA externa</h4>
                        <p className="text-sm text-emerald-800">
                          1. Carregue o modelo → 2. Preencha nome/endereço/equipamentos →
                          3. Envie o YAML parcial ao Gemini/Claude com o prompt em{' '}
                          <code className="text-xs bg-white px-1 rounded">dados/YAML_INSTRUCOES.md</code> →
                          4. Cole o YAML retornado aqui. Specs vazias são completadas pelo catálogo SQLite.
                        </p>
                      </div>
                    </div>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          </TabsContent>

          {/* ABA 2: DADOS DO CLIENTE */}
          <TabsContent value="cliente">
            <Card>
              <CardHeader>
                <CardTitle>Dados do Cliente</CardTitle>
                <CardDescription>
                  Preencha ou revise os dados cadastrais e de endereço
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Dados Cadastrais */}
                <div>
                  <h3 className="text-lg font-semibold mb-4">Dados Cadastrais</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="col-span-2">
                      <Label htmlFor="client_name">Nome Completo *</Label>
                      <Input
                        id="client_name"
                        value={clientData.client_name}
                        onChange={(e) => setClientData({...clientData, client_name: e.target.value})}
                        placeholder="Nome completo do cliente"
                      />
                    </div>

                    <div>
                      <Label htmlFor="cpf">CPF *</Label>
                      <Input
                        id="cpf"
                        value={clientData.cpf}
                        onChange={(e) => setClientData({...clientData, cpf: e.target.value})}
                        placeholder="000.000.000-00"
                      />
                    </div>

                    <div>
                      <Label htmlFor="rg">RG</Label>
                      <Input
                        id="rg"
                        value={clientData.rg}
                        onChange={(e) => setClientData({...clientData, rg: e.target.value})}
                        placeholder="00.000.000-0"
                      />
                    </div>

                    <div>
                      <Label htmlFor="validade_cnh">Validade da CNH</Label>
                      <Input
                        id="validade_cnh"
                        type="date"
                        value={clientData.validade_cnh}
                        onChange={(e) => setClientData({...clientData, validade_cnh: e.target.value})}
                      />
                    </div>

                    <div>
                      <Label htmlFor="data_nascimento">Data de Nascimento</Label>
                      <Input
                        id="data_nascimento"
                        type="date"
                        value={clientData.data_nascimento}
                        onChange={(e) => setClientData({...clientData, data_nascimento: e.target.value})}
                      />
                    </div>

                    <div>
                      <Label htmlFor="telefone">Telefone</Label>
                      <Input
                        id="telefone"
                        value={clientData.telefone}
                        onChange={(e) => setClientData({...clientData, telefone: e.target.value})}
                        placeholder="(00) 00000-0000"
                      />
                    </div>

                    <div className="col-span-2">
                      <Label htmlFor="email">E-mail</Label>
                      <Input
                        id="email"
                        type="email"
                        value={clientData.email}
                        onChange={(e) => setClientData({...clientData, email: e.target.value})}
                        placeholder="email@exemplo.com"
                      />
                    </div>
                  </div>
                </div>

                {/* Endereço */}
                <div>
                  <h3 className="text-lg font-semibold mb-4">Endereço</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="col-span-2">
                      <Label htmlFor="logradouro">Logradouro *</Label>
                      <Input
                        id="logradouro"
                        value={clientData.logradouro}
                        onChange={(e) => setClientData({...clientData, logradouro: e.target.value})}
                        placeholder="Rua, Avenida, etc"
                      />
                    </div>

                    <div>
                      <Label htmlFor="numero">Número</Label>
                      <Input
                        id="numero"
                        value={clientData.numero}
                        onChange={(e) => setClientData({...clientData, numero: e.target.value})}
                        placeholder="123"
                      />
                    </div>

                    <div>
                      <Label htmlFor="complemento">Complemento</Label>
                      <Input
                        id="complemento"
                        value={clientData.complemento}
                        onChange={(e) => setClientData({...clientData, complemento: e.target.value})}
                        placeholder="Apto 101, Bloco A, etc"
                      />
                    </div>

                    <div className="col-span-2">
                      <Label htmlFor="bairro">Bairro *</Label>
                      <Input
                        id="bairro"
                        value={clientData.bairro}
                        onChange={(e) => setClientData({...clientData, bairro: e.target.value})}
                        placeholder="Nome do bairro"
                      />
                    </div>

                    <div>
                      <Label htmlFor="cidade">Cidade *</Label>
                      <Input
                        id="cidade"
                        value={clientData.cidade}
                        onChange={(e) => setClientData({...clientData, cidade: e.target.value})}
                        placeholder="Nome da cidade"
                      />
                    </div>

                    <div>
                      <Label htmlFor="uf">UF *</Label>
                      <Input
                        id="uf"
                        value={clientData.uf}
                        onChange={(e) => {
                          const uf = e.target.value.toUpperCase()
                          setClientData({...clientData, uf})
                          suggestTensao(uf, clientData.tipo_ligacao)
                        }}
                        placeholder="GO"
                        maxLength={2}
                      />
                    </div>

                    <div>
                      <Label htmlFor="cep">CEP</Label>
                      <div className="flex gap-2">
                        <Input
                          id="cep"
                          value={clientData.cep}
                          onChange={(e) => setClientData({...clientData, cep: e.target.value})}
                          onBlur={() => {
                            const digits = (clientData.cep || '').replace(/\D/g, '')
                            if (digits.length === 8) lookupAddress()
                          }}
                          placeholder="00000-000"
                        />
                        <Button
                          type="button"
                          variant="outline"
                          onClick={lookupAddress}
                          disabled={cepLookupLoading}
                          title="Buscar endereço pelo CEP ou CEP pelo endereço"
                        >
                          <Search className="h-4 w-4" />
                        </Button>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">
                        Com CEP preenchido busca logradouro; sem CEP, tenta achar pelo endereço (internet).
                      </p>
                    </div>
                  </div>
                </div>

                {/* Unidade Consumidora */}
                <div>
                  <h3 className="text-lg font-semibold mb-4">Unidade Consumidora</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="col-span-2">
                      <Label htmlFor="consumer_unit">Número da UC *</Label>
                      <Input
                        id="consumer_unit"
                        value={clientData.consumer_unit}
                        onChange={(e) => setClientData({...clientData, consumer_unit: e.target.value})}
                        onBlur={(e) => {
                          const normalized = normalizeConsumerUnit(e.target.value)
                          if (normalized !== e.target.value) {
                            setClientData({...clientData, consumer_unit: normalized})
                          }
                        }}
                        placeholder="000.000.000-00"
                      />
                    </div>

                    <div>
                      <Label htmlFor="tensao_atendimento">Tensão de Atendimento</Label>
                      <Select
                        value={clientData.tensao_atendimento}
                        onValueChange={(value) => setClientData({...clientData, tensao_atendimento: value})}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="127V">127V</SelectItem>
                          <SelectItem value="220V">220V</SelectItem>
                          <SelectItem value="220/380V">220/380V (Trifásico)</SelectItem>
                          <SelectItem value="13.8kV">13.8kV (Média Tensão)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div>
                      <Label htmlFor="tipo_ligacao">Tipo de Ligação</Label>
                      <Select
                        value={clientData.tipo_ligacao}
                        onValueChange={(value) => {
                          setClientData({...clientData, tipo_ligacao: value})
                          syncPadraoEntrada(clientData.uf, value, clientData.classe)
                        }}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="MONOFASICO">Monofásico</SelectItem>
                          <SelectItem value="BIFASICO">Bifásico</SelectItem>
                          <SelectItem value="TRIFASICO">Trifásico</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div>
                      <Label htmlFor="classe">Classe</Label>
                      <Select
                        value={clientData.classe}
                        onValueChange={(value) => {
                          setClientData({...clientData, classe: value})
                          syncPadraoEntrada(clientData.uf, clientData.tipo_ligacao, value)
                        }}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="RESIDENCIAL">Residencial</SelectItem>
                          <SelectItem value="COMERCIAL">Comercial</SelectItem>
                          <SelectItem value="INDUSTRIAL">Industrial</SelectItem>
                          <SelectItem value="RURAL">Rural</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div>
                      <Label htmlFor="disjuntor_entrada">Disjuntor do padrão de entrada (A)</Label>
                      <Input
                        id="disjuntor_entrada"
                        type="number"
                        min="1"
                        step="1"
                        value={technicalData.disjuntor_entrada || '40'}
                        onChange={(e) => {
                          disjuntorEntradaManual.current = true
                          setTechnicalData({ ...technicalData, disjuntor_entrada: e.target.value })
                        }}
                        placeholder="40"
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        Tabela ramal BT (NT.00020.EQTL): disjuntor e cabo conforme carga kW
                        (demanda-alvo ou potência FV). Padrão 40 A se não informado.
                      </p>
                    </div>
                  </div>
                </div>

                <Button onClick={() => setActiveTab('equipamentos')} className="w-full">
                  Próximo: Equipamentos →
                </Button>
              </CardContent>
            </Card>
          </TabsContent>

          {/* ABA 3: EQUIPAMENTOS */}
          <TabsContent value="equipamentos">
            <div className="space-y-6">
              <div className="flex flex-col items-end gap-1">
                <Button
                  variant="outline"
                  onClick={handleEnrichEquipment}
                  disabled={loading || aiStatus.primary === 'none'}
                  title={
                    aiStatus.primary === 'none'
                      ? 'Configure Ollama ou .env com GEMINI_API_KEY'
                      : `IA: ${aiStatus.primary}`
                  }
                >
                  Buscar specs na internet (IA)
                </Button>
                {aiStatus.gemini && !aiStatus.gemini_working && aiStatus.gemini_error && (
                  <p className="text-xs text-red-600 max-w-md text-right">
                    Gemini indisponível: chave bloqueada ou inválida. Use uma chave de{' '}
                    <a href="https://aistudio.google.com/apikey" className="underline" target="_blank" rel="noreferrer">
                      aistudio.google.com/apikey
                    </a>
                  </p>
                )}
              </div>
              {/* Módulos Fotovoltaicos */}
              <Card>
                <CardHeader>
                  <CardTitle>Módulos Fotovoltaicos</CardTitle>
                  <CardDescription>
                    Configure os módulos solares do sistema
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {modules.map((module, index) => (
                    <div key={index} className="p-4 border rounded-lg space-y-4 bg-gray-50">
                      <div className="flex justify-between items-center">
                        <h4 className="font-semibold">Módulo {index + 1}</h4>
                        {modules.length > 1 && (
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => removeModule(index)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        )}
                      </div>

                      <CatalogEquipmentPicker
                        kind="module"
                        current={module}
                        onApply={(fields) => applyCatalogToModule(index, fields)}
                      />

                      <div className="grid grid-cols-3 gap-4">
                        <div>
                          <Label>Quantidade *</Label>
                          <Input
                            type="number"
                            value={module.quantity}
                            onChange={(e) => updateModule(index, 'quantity', e.target.value)}
                            placeholder="Ex: 32"
                          />
                        </div>

                        <div>
                          <Label>Fabricante</Label>
                          <Input
                            value={module.fabricante}
                            onChange={(e) => updateModule(index, 'fabricante', e.target.value)}
                            placeholder="Ex: RENEPV"
                          />
                        </div>

                        <div>
                          <Label>Potência (W) *</Label>
                          <Input
                            type="number"
                            value={module.power}
                            onChange={(e) => updateModule(index, 'power', e.target.value)}
                            placeholder="Ex: 680"
                          />
                        </div>

                        <div className="col-span-3">
                          <Label>Modelo *</Label>
                          <Input
                            value={module.model}
                            onChange={(e) => updateModule(index, 'model', e.target.value)}
                            placeholder="Ex: MÓDULO 680W RENEPV BIFACIAL 30MM"
                          />
                        </div>

                        <div>
                          <Label>Voc (V)</Label>
                          <Input
                            type="number"
                            step="0.01"
                            value={module.voc}
                            onChange={(e) => updateModule(index, 'voc', e.target.value)}
                            placeholder="45.5"
                          />
                        </div>

                        <div>
                          <Label>Isc (A)</Label>
                          <Input
                            type="number"
                            step="0.01"
                            value={module.isc}
                            onChange={(e) => updateModule(index, 'isc', e.target.value)}
                            placeholder="14.2"
                          />
                        </div>

                        <div>
                          <Label>Vmpp (V)</Label>
                          <Input
                            type="number"
                            step="0.01"
                            value={module.vmpp}
                            onChange={(e) => updateModule(index, 'vmpp', e.target.value)}
                            placeholder="37.8"
                          />
                        </div>

                        <div>
                          <Label>Impp (A)</Label>
                          <Input
                            type="number"
                            step="0.01"
                            value={module.impp}
                            onChange={(e) => updateModule(index, 'impp', e.target.value)}
                            placeholder="18.0"
                          />
                        </div>

                        <div>
                          <Label>Eficiência (%)</Label>
                          <Input
                            type="number"
                            step="0.01"
                            value={module.eficiencia}
                            onChange={(e) => updateModule(index, 'eficiencia', e.target.value)}
                            placeholder="21.5"
                          />
                        </div>
                      </div>
                    </div>
                  ))}

                  <Button onClick={addModule} variant="outline" className="w-full">
                    <Plus className="mr-2 h-4 w-4" />
                    Adicionar Módulo
                  </Button>
                </CardContent>
              </Card>

              {/* Inversores */}
              <Card>
                <CardHeader>
                  <CardTitle>Inversores</CardTitle>
                  <CardDescription>
                    Configure os inversores do sistema
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {inverters.map((inverter, index) => (
                    <div key={index} className="p-4 border rounded-lg space-y-4 bg-gray-50">
                      <div className="flex justify-between items-center">
                        <h4 className="font-semibold">Inversor {index + 1}</h4>
                        {inverters.length > 1 && (
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => removeInverter(index)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        )}
                      </div>

                      <CatalogEquipmentPicker
                        kind="inverter"
                        current={inverter}
                        onApply={(fields) => applyCatalogToInverter(index, fields)}
                      />

                      <div className="grid grid-cols-3 gap-4">
                        <div>
                          <Label>Quantidade *</Label>
                          <Input
                            type="number"
                            value={inverter.quantity}
                            onChange={(e) => updateInverter(index, 'quantity', e.target.value)}
                            placeholder="Ex: 8"
                          />
                        </div>

                        <div>
                          <Label>Fabricante</Label>
                          <Input
                            value={inverter.fabricante}
                            onChange={(e) => updateInverter(index, 'fabricante', e.target.value)}
                            placeholder="Ex: DEYE"
                          />
                        </div>

                        <div>
                          <Label>Potência (kW) *</Label>
                          <Input
                            type="number"
                            step="0.01"
                            value={inverter.power}
                            onChange={(e) => updateInverter(index, 'power', e.target.value)}
                            placeholder="Ex: 2.25"
                          />
                        </div>

                        <div className="col-span-3">
                          <Label>Modelo *</Label>
                          <Input
                            value={inverter.model}
                            onChange={(e) => updateInverter(index, 'model', e.target.value)}
                            placeholder="Ex: MICRO INVERSOR DEYE-S2.25K-G4 220V"
                          />
                        </div>

                        <div>
                          <Label>Tensão Nominal (V)</Label>
                          <Input
                            type="number"
                            value={inverter.tensao_nominal}
                            onChange={(e) => updateInverter(index, 'tensao_nominal', e.target.value)}
                            placeholder="220"
                          />
                        </div>

                        <div>
                          <Label>Corrente Nominal (A)</Label>
                          <Input
                            type="number"
                            step="0.01"
                            value={inverter.corrente_nominal}
                            onChange={(e) => updateInverter(index, 'corrente_nominal', e.target.value)}
                            placeholder="10.2"
                          />
                        </div>

                        <div>
                          <Label>MPPT Min (V)</Label>
                          <Input
                            type="number"
                            value={inverter.mppt_min}
                            onChange={(e) => updateInverter(index, 'mppt_min', e.target.value)}
                            placeholder="200"
                          />
                        </div>

                        <div>
                          <Label>MPPT Max (V)</Label>
                          <Input
                            type="number"
                            value={inverter.mppt_max}
                            onChange={(e) => updateInverter(index, 'mppt_max', e.target.value)}
                            placeholder="800"
                          />
                        </div>

                        <div>
                          <Label>Eficiência (%)</Label>
                          <Input
                            type="number"
                            step="0.01"
                            value={inverter.eficiencia}
                            onChange={(e) => updateInverter(index, 'eficiencia', e.target.value)}
                            placeholder="97.6"
                          />
                        </div>
                      </div>
                    </div>
                  ))}

                  <Button onClick={addInverter} variant="outline" className="w-full">
                    <Plus className="mr-2 h-4 w-4" />
                    Adicionar Inversor
                  </Button>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Layout de strings CC</CardTitle>
                  <CardDescription>
                    Sugestão automática com topologia MPPT do catálogo (módulos/série, strings por MPPT, Icc/Voc).
                    Preenche os campos em Técnico → Strings CC / MPPT.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <Button
                    type="button"
                    variant="secondary"
                    className="w-full"
                    disabled={stringPreviewLoading}
                    onClick={previewStringLayout}
                  >
                    {stringPreviewLoading ? 'Calculando strings…' : 'Sugerir layout de strings'}
                  </Button>

                  {stringPreview && (
                    <div className={`rounded-lg border p-4 text-sm space-y-2 ${
                      stringPreview.status === 'OK'
                        ? 'bg-green-50 border-green-200'
                        : 'bg-amber-50 border-amber-200'
                    }`}>
                      <p className="font-semibold">
                        Status: {stringPreview.status} · Topologia: {stringPreview.topology}
                      </p>
                      <p>
                        {stringPreview.modules_per_string} módulo(s)/string ·{' '}
                        {stringPreview.strings_count} string(s) total ·{' '}
                        até {stringPreview.strings_per_mppt} em paralelo/MPPT
                      </p>
                      <p>
                        Voc string: {stringPreview.string_voc_v} V · Vmpp: {stringPreview.string_vmpp_v} V ·{' '}
                        Isc: {stringPreview.string_isc_a} A
                      </p>
                      {stringPreview.mppt_layout?.length > 0 && (
                        <p>Topologia catálogo: {stringPreview.mppt_layout.join('+')}</p>
                      )}
                      {stringPreview.icc_ok === false && (
                        <p className="text-red-700 font-medium">Atenção: Isc excede Icc do MPPT</p>
                      )}
                      {stringPreview.mppt_ok === false && (
                        <p className="text-red-700 font-medium">Atenção: faixa MPPT (Voc/Vmpp) fora do limite</p>
                      )}
                      {(stringPreview.messages || []).map((msg, i) => (
                        <p key={i} className="text-xs text-gray-700">• {msg}</p>
                      ))}
                      {stringPreview.configuracao_strings_text && (
                        <p className="text-xs mt-2">{stringPreview.configuracao_strings_text}</p>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>

              <Button onClick={() => setActiveTab('contrato')} className="w-full">
                Próximo: Contrato →
              </Button>
            </div>
          </TabsContent>

          {/* ABA 4: CONTRATO */}
          <TabsContent value="contrato">
            <Card>
              <CardHeader>
                <CardTitle>Contrato de prestação de serviços</CardTitle>
                <CardDescription>
                  Template oficial: ModeloContrato.docx — banco e dados da PIENG permanecem fixos no Word.
                  Revise aqui o que varia por cliente.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="numero_contrato">Número do contrato *</Label>
                    <Input
                      id="numero_contrato"
                      value={contractData.numero_contrato}
                      onChange={(e) => setContractData({
                        ...contractData,
                        numero_contrato: e.target.value,
                      })}
                      placeholder="122/2026"
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      Nome da pasta no Google Drive: número do contrato + 1º e 2º nome (ex.: 80 - João Silva). Token {'{{NUMERO_CONTRATO}}'} no cabeçalho do contrato.
                    </p>
                  </div>
                  <div>
                    <Label htmlFor="data_documento">Data de assinatura</Label>
                    <Input
                      id="data_documento"
                      type="date"
                      value={contractData.data_documento}
                      onChange={(e) => setContractData({
                        ...contractData,
                        data_documento: e.target.value,
                      })}
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      {'{{DATA_DOCUMENTO}}'} e {'{{DATA_DOCUMENTO_EXTENSO}}'} (também usados na procuração).
                    </p>
                  </div>
                  <div className="col-span-2">
                    <Label htmlFor="cidade_documento">Cidade da assinatura</Label>
                    <Input
                      id="cidade_documento"
                      value={contractData.cidade_documento}
                      onChange={(e) => setContractData({
                        ...contractData,
                        cidade_documento: e.target.value,
                      })}
                      placeholder={clientData.cidade || 'Goiânia'}
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      Token {'{{CIDADE_DOCUMENTO}}/{{UF}}'} — vazio usa a cidade do cliente ({clientData.cidade || '—'}).
                    </p>
                  </div>
                </div>

                <div>
                  <Label htmlFor="texto_pagamento">Valor e forma de pagamento</Label>
                  <Textarea
                    id="texto_pagamento"
                    value={contractData.texto_valor_pagamento_contrato}
                    onChange={(e) => setContractData({
                      ...contractData,
                      texto_valor_pagamento_contrato: e.target.value,
                    })}
                    placeholder={EXEMPLO_TEXTO_VALOR_PAGAMENTO_CONTRATO}
                    rows={6}
                    className="font-mono text-sm"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Texto livre → {'{{TEXTO_VALOR_PAGAMENTO_CONTRATO}}'} (Cláusula de valor/pagamento). Enter = nova linha.
                  </p>
                  {!contractData.texto_valor_pagamento_contrato?.trim() && (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="mt-2"
                      onClick={() => setContractData({
                        ...contractData,
                        texto_valor_pagamento_contrato: EXEMPLO_TEXTO_VALOR_PAGAMENTO_CONTRATO,
                      })}
                    >
                      Usar exemplo (R$ 12.000 / 18× cartão)
                    </Button>
                  )}
                </div>

                <div className="flex gap-3">
                  <Button variant="outline" onClick={() => setActiveTab('equipamentos')}>
                    ← Equipamentos
                  </Button>
                  <Button onClick={() => setActiveTab('tecnico')} className="flex-1">
                    Próximo: Dados Técnicos →
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* ABA 5: DADOS TÉCNICOS */}
          <TabsContent value="tecnico">
            <Card>
              <CardHeader>
                <CardTitle>Dados Técnicos</CardTitle>
                <CardDescription>
                  Informações técnicas da instalação
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Documento / operação */}
                <div>
                  <h3 className="text-lg font-semibold mb-4">Operação</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>Data prevista de operação</Label>
                      <Input
                        type="date"
                        value={technicalData.data_operacao}
                        onChange={(e) => setTechnicalData({...technicalData, data_operacao: e.target.value})}
                      />
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground mt-2">
                    Data de assinatura do contrato/procuração: aba Contrato.
                  </p>
                </div>

                {/* Proteção */}
                <div>
                  <h3 className="text-lg font-semibold mb-4">Proteção Elétrica</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>Disjuntor de Entrada (A)</Label>
                      <Input
                        type="number"
                        value={technicalData.disjuntor_entrada || '40'}
                        onChange={(e) => {
                          disjuntorEntradaManual.current = true
                          setTechnicalData({...technicalData, disjuntor_entrada: e.target.value})
                        }}
                        placeholder="40"
                      />
                    </div>

                    <div>
                      <Label>Curva do Disjuntor</Label>
                      <Select
                        value={technicalData.curva_disjuntor}
                        onValueChange={(value) => setTechnicalData({...technicalData, curva_disjuntor: value})}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Selecione" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="B">Curva B</SelectItem>
                          <SelectItem value="C">Curva C</SelectItem>
                          <SelectItem value="D">Curva D</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div>
                      <Label>Tipo de DPS</Label>
                      <Input
                        value={technicalData.dps_tipo}
                        onChange={(e) => setTechnicalData({...technicalData, dps_tipo: e.target.value})}
                        placeholder="Ex: Tipo 2"
                      />
                    </div>

                    <div>
                      <Label>Classe DPS</Label>
                      <Input
                        value={technicalData.dps_classe}
                        onChange={(e) => setTechnicalData({...technicalData, dps_classe: e.target.value})}
                        placeholder="Ex: Classe II"
                      />
                    </div>

                    <div>
                      <Label>DR (tipo)</Label>
                      <Input
                        value={technicalData.dr_tipo}
                        onChange={(e) => setTechnicalData({...technicalData, dr_tipo: e.target.value})}
                        placeholder="DR 30 mA — alta sensibilidade"
                      />
                    </div>

                    <div>
                      <Label>Sensibilidade DR (mA)</Label>
                      <Input
                        value={technicalData.dr_sensibilidade_ma}
                        onChange={(e) => setTechnicalData({...technicalData, dr_sensibilidade_ma: e.target.value})}
                        placeholder="30"
                      />
                    </div>
                  </div>
                </div>

                {/* Cabos */}
                <div>
                  <h3 className="text-lg font-semibold mb-4">Cabeamento</h3>
                  <p className="text-xs text-muted-foreground mb-3">
                    Recomendações aparecem na aba Cálculos; o sistema não altera estes campos automaticamente.
                  </p>
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <Label>Bitola Cabo CA (mm²)</Label>
                      <Input
                        value={technicalData.bitola_cabo_ca}
                        onChange={(e) => setTechnicalData({...technicalData, bitola_cabo_ca: e.target.value})}
                        placeholder="10"
                      />
                    </div>

                    <div>
                      <Label>Bitola Cabo CC (mm²)</Label>
                      <Input
                        value={technicalData.bitola_cabo_cc}
                        onChange={(e) => setTechnicalData({...technicalData, bitola_cabo_cc: e.target.value})}
                        placeholder="6"
                      />
                    </div>

                    <div>
                      <Label>Bitola Cabo Padrão (mm²)</Label>
                      <Input
                        value={technicalData.bitola_cabo_padrao}
                        onChange={(e) => setTechnicalData({...technicalData, bitola_cabo_padrao: e.target.value})}
                        placeholder="10"
                      />
                    </div>
                  </div>
                </div>

                {/* Aterramento */}
                <div>
                  <h3 className="text-lg font-semibold mb-4">Aterramento</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>Tipo de Aterramento</Label>
                      <Input
                        value={technicalData.tipo_aterramento}
                        onChange={(e) => setTechnicalData({...technicalData, tipo_aterramento: e.target.value})}
                        placeholder="Haste copper 2,4 m com caixa de inspeção"
                      />
                    </div>

                    <div>
                      <Label>Resistência de Aterramento</Label>
                      <Input
                        value={technicalData.resistencia_aterramento}
                        onChange={(e) => setTechnicalData({...technicalData, resistencia_aterramento: e.target.value})}
                        placeholder="≤ 10 Ω"
                      />
                    </div>
                  </div>
                </div>

                {/* Localização */}
                <div>
                  <h3 className="text-lg font-semibold mb-4">Localização</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="col-span-2">
                      <Label>Coordenadas georreferenciadas</Label>
                      <Textarea
                        value={technicalData.coordenadas_raw || ''}
                        onChange={(e) => setTechnicalData({ ...technicalData, coordenadas_raw: e.target.value })}
                        onBlur={(e) => handleCoordenadasRawBlur(e.target.value)}
                        placeholder="-16.306664, -48.913032  ou  22 K 722986.05 m E 8196002.05 m S / -16.306664 -48.913032"
                        rows={2}
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        Cole do Google Earth — UTM e graus decimais são calculados automaticamente.
                      </p>
                    </div>

                    <div>
                      <Label>Coordenada UTM X (E)</Label>
                      <Input
                        value={technicalData.coordenada_utm_x}
                        onChange={(e) => setTechnicalData({...technicalData, coordenada_utm_x: e.target.value})}
                        onBlur={syncCoordinatesFromFields}
                        placeholder="722986.05"
                      />
                    </div>

                    <div>
                      <Label>Coordenada UTM Y (N/S)</Label>
                      <Input
                        value={technicalData.coordenada_utm_y}
                        onChange={(e) => setTechnicalData({...technicalData, coordenada_utm_y: e.target.value})}
                        onBlur={syncCoordinatesFromFields}
                        placeholder="8196002.05"
                      />
                    </div>

                    <div>
                      <Label>Fuso UTM</Label>
                      <Input
                        value={technicalData.fuso_utm}
                        onChange={(e) => setTechnicalData({...technicalData, fuso_utm: e.target.value})}
                        onBlur={syncCoordinatesFromFields}
                        placeholder="22S"
                      />
                    </div>

                    <div>
                      <Label>Latitude (graus decimais)</Label>
                      <Input
                        value={technicalData.latitude}
                        onChange={(e) => setTechnicalData({...technicalData, latitude: e.target.value})}
                        onBlur={syncCoordinatesFromFields}
                        placeholder="-16.306664"
                      />
                    </div>

                    <div>
                      <Label>Longitude (graus decimais)</Label>
                      <Input
                        value={technicalData.longitude}
                        onChange={(e) => setTechnicalData({...technicalData, longitude: e.target.value})}
                        onBlur={syncCoordinatesFromFields}
                        placeholder="-48.913032"
                      />
                    </div>

                    <div>
                      <Label>Número do Poste/Transformador</Label>
                      <Input
                        value={technicalData.num_poste}
                        onChange={(e) => setTechnicalData({...technicalData, num_poste: e.target.value})}
                        placeholder="Ex: 12345"
                      />
                    </div>

                    <FiguraLocalizacaoPreview
                      technicalData={technicalData}
                      onTechnicalChange={(patch) => setTechnicalData((prev) => ({ ...prev, ...patch }))}
                    />
                  </div>
                </div>

                {/* Arranjo */}
                <div>
                  <h3 className="text-lg font-semibold mb-4">Arranjo Fotovoltaico</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>Tipo de Arranjo</Label>
                      <Select
                        value={technicalData.tipo_arranjo}
                        onValueChange={(value) => setTechnicalData({...technicalData, tipo_arranjo: value})}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Selecione" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="SOLO">Solo</SelectItem>
                          <SelectItem value="TELHADO">Telhado</SelectItem>
                          <SelectItem value="LAJE">Laje</SelectItem>
                          <SelectItem value="CARPORT">Carport</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div>
                      <Label>Área do Arranjo (m²)</Label>
                      <Input
                        type="number"
                        step="0.01"
                        value={technicalData.area_arranjo}
                        onChange={(e) => setTechnicalData({...technicalData, area_arranjo: e.target.value})}
                        placeholder="125"
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        Calculado: quantidade de módulos × área do módulo (catálogo ou 2,5 m² padrão).
                      </p>
                    </div>
                  </div>
                </div>

                <div className="border-t pt-6 space-y-4">
                  <h3 className="text-lg font-semibold">Strings CC / MPPT</h3>
                  <p className="text-sm text-gray-600">
                    Série: soma Voc, Isc permanece. String/MPPT: informe módulos por string e strings em paralelo por MPPT.
                    Micro: 1 módulo/equipamento; até 3 micros em série por disjuntor CA.
                  </p>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    <div>
                      <Label>Tipo de inversor</Label>
                      <Select
                        value={technicalData.tipo_inversor || 'STRING'}
                        onValueChange={(v) => setTechnicalData({
                          ...technicalData,
                          tipo_inversor: v,
                          modulos_por_string: v === 'MICRO' ? '1' : technicalData.modulos_por_string,
                          strings_por_mppt: v === 'MICRO' ? '1' : technicalData.strings_por_mppt,
                        })}
                      >
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="STRING">String / central</SelectItem>
                          <SelectItem value="MICRO">Microinversor</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label>MPPT por inversor</Label>
                      <Input
                        type="number"
                        min="1"
                        value={technicalData.num_mppt}
                        onChange={(e) => setTechnicalData({...technicalData, num_mppt: e.target.value})}
                        placeholder="2"
                      />
                    </div>
                    {technicalData.tipo_inversor === 'MICRO' ? (
                      <div>
                        <Label>Micros em série por disjuntor CA</Label>
                        <Select
                          value={String(technicalData.micros_por_grupo_ca || '3')}
                          onValueChange={(v) => setTechnicalData({...technicalData, micros_por_grupo_ca: v})}
                        >
                          <SelectTrigger><SelectValue /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="1">1 (1 disjuntor/micro)</SelectItem>
                            <SelectItem value="2">2 em série</SelectItem>
                            <SelectItem value="3">3 em série (máx.)</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    ) : (
                      <>
                        <div>
                          <Label>Módulos por string</Label>
                          <Input
                            type="number"
                            min="1"
                            value={technicalData.modulos_por_string}
                            onChange={(e) => setTechnicalData({...technicalData, modulos_por_string: e.target.value})}
                            placeholder="Auto"
                          />
                        </div>
                        <div>
                          <Label>Strings em paralelo / MPPT</Label>
                          <Input
                            type="number"
                            min="1"
                            value={technicalData.strings_por_mppt}
                            onChange={(e) => setTechnicalData({...technicalData, strings_por_mppt: e.target.value})}
                            placeholder="Auto"
                          />
                        </div>
                      </>
                    )}
                  </div>
                </div>

                <div className="border-t pt-6 space-y-4">
                  <h3 className="text-lg font-semibold">Tabela de demanda — Tabela 1 · Levantamento de Carga</h3>
                  <p className="text-sm text-gray-600">
                    Escolha um modelo pronto (NTC-04) ou informe a demanda-alvo manualmente. A tabela é inserida formatada no memorial Word.
                  </p>
                  <div className="space-y-2">
                    <Label>Modelo de demanda (atalho)</Label>
                    <div className="flex flex-col sm:flex-row gap-2">
                      <Select
                        value={technicalData.demanda_modelo_id || ''}
                        onValueChange={(id) => {
                          setTechnicalData({ ...technicalData, demanda_modelo_id: id })
                          applyDemandModel(id)
                        }}
                      >
                        <SelectTrigger className="sm:flex-1">
                          <SelectValue placeholder="Selecione um dos 6 modelos padrão…" />
                        </SelectTrigger>
                        <SelectContent>
                          {demandModels.map((m) => (
                            <SelectItem key={m.id} value={m.id}>
                              {m.nome}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    {technicalData.demanda_modelo_id && (
                      <p className="text-xs text-gray-500">
                        {demandModels.find((m) => m.id === technicalData.demanda_modelo_id)?.descricao}
                      </p>
                    )}
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>Demanda-alvo (kW)</Label>
                      <Input
                        type="number"
                        step="0.1"
                        value={technicalData.demanda_alvo_kw}
                        onChange={(e) => setTechnicalData({...technicalData, demanda_alvo_kw: e.target.value})}
                        placeholder="Ex: 20"
                      />
                    </div>
                    <div className="flex items-end">
                      <label className="flex items-center gap-2 text-sm cursor-pointer pb-2">
                        <input
                          type="checkbox"
                          checked={technicalData.demand_table_ai}
                          onChange={(e) => setTechnicalData({...technicalData, demand_table_ai: e.target.checked})}
                        />
                        Usar IA para sugerir cargas (Gemini/Ollama)
                      </label>
                    </div>
                  </div>
                  <div>
                    <Label>Observações para a tabela (opcional)</Label>
                    <Textarea
                      value={technicalData.demanda_notas}
                      onChange={(e) => setTechnicalData({...technicalData, demanda_notas: e.target.value})}
                      placeholder="Ex: fábrica de doces, linha de produção, câmara fria..."
                      rows={2}
                    />
                  </div>
                </div>

                <Button onClick={calculateSystem} disabled={loading} className="w-full">
                  <Calculator className="mr-2 h-4 w-4" />
                  {loading ? 'Calculando...' : 'Calcular Sistema'}
                </Button>
              </CardContent>
            </Card>
          </TabsContent>

          {/* ABA 5: CÁLCULOS */}
          <TabsContent value="calculos">
            <Card>
              <CardHeader>
                <CardTitle>Resultados dos Cálculos</CardTitle>
                <CardDescription>
                  Dimensionamento técnico do sistema
                </CardDescription>
              </CardHeader>
              <CardContent>
                {calculations ? (
                  <div className="space-y-6">
                    <CalculationsResults
                      calculations={calculations}
                      onApplyToForm={applyDemandTableToForm}
                    />

                    <Button onClick={generateDocuments} disabled={loading} className="w-full">
                      <Download className="mr-2 h-4 w-4" />
                      {loading ? 'Gerando...' : 'Gerar Documentos'}
                    </Button>

                    {generatedFiles && (
                      <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                        <p className="font-semibold text-green-800 mb-3">✅ Documentos Gerados com Sucesso!</p>
                        {outputDirectory && (
                          <div className="mb-3 p-2 bg-white rounded border border-green-200 text-xs text-gray-700 break-all">
                            <span className="font-medium">Pasta no Google Drive / disco:</span>
                            <br />
                            {outputDirectory}
                            <p className="mt-1 text-gray-500">Dados pessoais (LGPD) — não compartilhe nem suba ao GitHub.</p>
                          </div>
                        )}
                        {outputWarning && (
                          <p className="mb-3 text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded p-2">{outputWarning}</p>
                        )}
                        <div className="space-y-2">
                          {generatedFiles.excel && (
                            <div className="flex items-center justify-between p-2 bg-white rounded border border-green-300">
                              <span className="text-sm text-gray-700">📊 Excel: {generatedFiles.excel.name}</span>
                              <a
                                href={generatedFiles.excel.download_url}
                                download
                                className="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700 transition-colors"
                              >
                                Baixar
                              </a>
                            </div>
                          )}
                          {generatedFiles.memorial && (
                            <div className="flex items-center justify-between p-2 bg-white rounded border border-green-300">
                              <span className="text-sm text-gray-700">📄 Memorial: {generatedFiles.memorial.name}</span>
                              <a
                                href={generatedFiles.memorial.download_url}
                                download
                                className="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700 transition-colors"
                              >
                                Baixar
                              </a>
                            </div>
                          )}
                          {generatedFiles.procuracao && (
                            <div className="flex items-center justify-between p-2 bg-white rounded border border-green-300">
                              <span className="text-sm text-gray-700">📝 Procuração: {generatedFiles.procuracao.name}</span>
                              <a
                                href={generatedFiles.procuracao.download_url}
                                download
                                className="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700 transition-colors"
                              >
                                Baixar
                              </a>
                            </div>
                          )}
                          {generatedFiles.contrato && (
                            <div className="flex items-center justify-between p-2 bg-white rounded border border-green-300">
                              <span className="text-sm text-gray-700">📋 Contrato: {generatedFiles.contrato.name}</span>
                              <a
                                href={generatedFiles.contrato.download_url}
                                download
                                className="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700 transition-colors"
                              >
                                Baixar
                              </a>
                            </div>
                          )}
                          {generatedFiles.planta && (
                            <div className="flex items-center justify-between p-2 bg-white rounded border border-green-300">
                              <span className="text-sm text-gray-700">📐 Planta CAD: {generatedFiles.planta.name} (dados já preenchidos)</span>
                              <a
                                href={generatedFiles.planta.download_url}
                                download
                                className="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700 transition-colors"
                              >
                                Baixar
                              </a>
                            </div>
                          )}
                          {generatedFiles.outros && generatedFiles.outros.length > 0 && generatedFiles.outros.map((file, idx) => (
                            <div key={idx} className="flex items-center justify-between p-2 bg-white rounded border border-green-300">
                              <span className="text-sm text-gray-700">📎 {file.name}</span>
                              <a
                                href={file.download_url}
                                download
                                className="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700 transition-colors"
                              >
                                Baixar
                              </a>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-12 text-gray-500">
                    <Calculator className="mx-auto h-16 w-16 mb-4 opacity-50" />
                    <p>Preencha os dados e clique em "Calcular Sistema"</p>
                    <p className="text-sm mt-2">na aba "Dados Técnicos"</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="catalogo">
            <CatalogPanel />
          </TabsContent>

          {authUser.role === 'master' && (
            <TabsContent value="usuarios">
              <UserManagement />
            </TabsContent>
          )}
        </Tabs>
      </div>

      <DeParaPanel
        open={deParaOpen}
        onToggle={() => setDeParaOpen((v) => !v)}
        preview={deParaPreview}
        loading={deParaLoading}
        onRefresh={fetchDeParaPreview}
        filter={deParaFilter}
        onFilterChange={setDeParaFilter}
        error={deParaError}
        onWidthChange={setDeParaWidth}
      />
    </div>
  )
}

export default App
