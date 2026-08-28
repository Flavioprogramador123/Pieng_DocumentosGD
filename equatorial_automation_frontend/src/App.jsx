import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button.jsx'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card.jsx'
import { Input } from '@/components/ui/input.jsx'
import { Label } from '@/components/ui/label.jsx'
import { Textarea } from '@/components/ui/textarea.jsx'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select.jsx'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs.jsx'
import { Plus, Trash2, FileText, Calculator, Download, Upload, Save, FileJson, Search, Database } from 'lucide-react'
import { DeParaPanel, DeParaPanelToggle } from '@/components/DeParaPanel.jsx'
import { CalculationsResults } from '@/components/CalculationsResults.jsx'
import { CatalogPanel } from '@/components/CatalogPanel.jsx'
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
import { getInitialTechnicalData } from './utils/formDefaults'

const API_BASE = '/api'

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
      eficiencia: ''
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
  const [aiStatus, setAiStatus] = useState({ ollama: false, gemini: false, primary: 'none' })
  const [deParaOpen, setDeParaOpen] = useState(true)
  const [deParaWidth, setDeParaWidth] = useState(460)
  const [deParaPreview, setDeParaPreview] = useState(null)
  const [deParaLoading, setDeParaLoading] = useState(false)
  const [deParaFilter, setDeParaFilter] = useState('')
  const [deParaError, setDeParaError] = useState('')

  // Verificar status da IA ao carregar
  useEffect(() => {
    fetch(`${API_BASE}/ai-status`)
      .then(res => res.json())
      .then(status => {
        setAiStatus({
          ...status,
          primary: status.primary || (status.ollama ? 'ollama' : status.gemini ? 'gemini' : 'none'),
        })
      })
      .catch(() => setAiStatus({ ollama: false, gemini: false, primary: 'none' }))
  }, [])

  const buildRequestPayload = (options = {}) => {
    const endereco_completo = [
      clientData.logradouro,
      clientData.numero ? `Nº ${clientData.numero}` : '',
      clientData.complemento,
      clientData.bairro,
      clientData.cidade && clientData.uf ? `${clientData.cidade}/${clientData.uf}` : '',
    ].filter(Boolean).join(', ')

    return {
      client_name: clientData.client_name,
      client_address: endereco_completo,
      consumer_unit: clientData.consumer_unit,
      client_cpf: clientData.cpf,
      grid_voltage: clientData.tensao_atendimento,
      ...clientData,
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
      const response = await fetch(`${API_BASE}/lookup-address`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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

  const suggestTensao = async (uf, tipoLigacao) => {
    try {
      const res = await fetch(`${API_BASE}/grid-voltage/suggest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ uf, tipo_ligacao: tipoLigacao }),
      })
      const data = await res.json()
      if (data.success && data.tensao_atendimento) {
        setClientData((prev) => ({
          ...prev,
          tensao_atendimento: data.tensao_atendimento,
        }))
      }
    } catch {
      // silencioso — usuário pode ajustar manualmente
    }
  }

  const fetchDeParaPreview = async () => {
    const local = buildLocalDeParaPreview(clientData, technicalData, modules, inverters)
    setDeParaPreview(local)
    setDeParaLoading(true)
    setDeParaError('')
    try {
      const response = await fetch(`${API_BASE}/preview-de-para`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
    setDeParaPreview(buildLocalDeParaPreview(clientData, technicalData, modules, inverters))
    const timer = setTimeout(() => {
      fetchDeParaPreview()
    }, 400)
    return () => clearTimeout(timer)
  }, [deParaOpen, clientData, technicalData, modules, inverters])

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
      const response = await fetch(`${API_BASE}/analyze-text`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
      const response = await fetch(`${API_BASE}/yaml/template`)
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
      const response = await fetch(`${API_BASE}/import-yaml`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
      const response = await fetch(`${API_BASE}/export-yaml`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
      technical: technicalData,
      modules,
      inverters,
      calculations
    }

    try {
      const response = await fetch(`${API_BASE}/save-form`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
      eficiencia: ''
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
      }

      const response = await fetch(`${API_BASE}/calculate-system`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestData),
      })

      const data = await response.json()

      if (response.ok && data.success) {
        setCalculations(data.calculations)
        const calc = data.calculations
        setTechnicalData((prev) => ({
          ...prev,
          bitola_cabo_cc: prev.bitola_cabo_cc || calc.cable_section_cc?.replace('mm²', ' mm²'),
          bitola_cabo_ca: prev.bitola_cabo_ca || calc.cable_section_ca?.replace('mm²', ' mm²'),
          disjuntor_entrada: prev.disjuntor_entrada || String(calc.disjuntor_recomendado_a || ''),
          tabela_demanda_text: calc.demand_table?.memorial_text || prev.tabela_demanda_text,
          modulos_por_string: prev.modulos_por_string || String(calc.dc_strings?.modules_per_string || ''),
        }))
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
    }))
    alert('Tabela de demanda aplicada ao formulário. Será incluída na geração dos documentos.')
  }

  const handleEnrichEquipment = async () => {
    if (aiStatus.primary === 'none') {
      alert('Configure Ollama local ou GEMINI_API_KEY no arquivo .env (raiz do projeto, nunca no frontend).')
      return
    }

    setLoading(true)
    try {
      const response = await fetch(`${API_BASE}/enrich-equipment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
    setLoading(true)
    try {
      const requestData = buildRequestPayload({ enrich_specs: false })

      const response = await fetch(`${API_BASE}/fill-documents`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestData)
      })

      const data = await response.json()

      if (response.ok) {
        setGeneratedFiles(data.files)
        if (deParaOpen) fetchDeParaPreview()
        alert('Documentos gerados com sucesso!')
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-8">
      <div
        className="max-w-7xl mx-auto transition-[margin] duration-200"
        style={{ marginRight: deParaOpen ? deParaWidth : 0 }}
      >
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Automação Equatorial Energia
          </h1>
          <p className="text-gray-600">
            Sistema de Preenchimento de Documentos PRODIST 3 - Geração Distribuída
          </p>
        </div>

        {/* Botões de Ação Globais */}
        <div className="flex gap-4 justify-end mb-6 flex-wrap">
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
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="entrada">📄 Entrada</TabsTrigger>
            <TabsTrigger value="cliente">👤 Cliente</TabsTrigger>
            <TabsTrigger value="equipamentos">⚡ Equipamentos</TabsTrigger>
            <TabsTrigger value="tecnico">🔧 Dados Técnicos</TabsTrigger>
            <TabsTrigger value="calculos">📊 Cálculos</TabsTrigger>
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
                          suggestTensao(clientData.uf, value)
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
                        onValueChange={(value) => setClientData({...clientData, classe: value})}
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

              <Button onClick={() => setActiveTab('tecnico')} className="w-full">
                Próximo: Dados Técnicos →
              </Button>
            </div>
          </TabsContent>

          {/* ABA 4: DADOS TÉCNICOS */}
          <TabsContent value="tecnico">
            <Card>
              <CardHeader>
                <CardTitle>Dados Técnicos</CardTitle>
                <CardDescription>
                  Informações técnicas da instalação
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Documento */}
                <div>
                  <h3 className="text-lg font-semibold mb-4">Documento</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>Data de assinatura / documento</Label>
                      <Input
                        type="date"
                        value={technicalData.data_documento}
                        onChange={(e) => setTechnicalData({
                          ...technicalData,
                          data_documento: e.target.value,
                          data_operacao: technicalData.data_operacao || e.target.value,
                        })}
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        Padrão: dia de hoje. Altere se necessário.
                      </p>
                    </div>
                    <div>
                      <Label>Data prevista de operação</Label>
                      <Input
                        type="date"
                        value={technicalData.data_operacao}
                        onChange={(e) => setTechnicalData({...technicalData, data_operacao: e.target.value})}
                      />
                    </div>
                  </div>
                </div>

                {/* Proteção */}
                <div>
                  <h3 className="text-lg font-semibold mb-4">Proteção Elétrica</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>Disjuntor de Entrada (A)</Label>
                      <Input
                        type="number"
                        value={technicalData.disjuntor_entrada}
                        onChange={(e) => setTechnicalData({...technicalData, disjuntor_entrada: e.target.value})}
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
                    <div>
                      <Label>Coordenada UTM X</Label>
                      <Input
                        value={technicalData.coordenada_utm_x}
                        onChange={(e) => setTechnicalData({...technicalData, coordenada_utm_x: e.target.value})}
                        placeholder="123456"
                      />
                    </div>

                    <div>
                      <Label>Coordenada UTM Y</Label>
                      <Input
                        value={technicalData.coordenada_utm_y}
                        onChange={(e) => setTechnicalData({...technicalData, coordenada_utm_y: e.target.value})}
                        placeholder="7890123"
                      />
                    </div>

                    <div>
                      <Label>Fuso UTM</Label>
                      <Input
                        value={technicalData.fuso_utm}
                        onChange={(e) => setTechnicalData({...technicalData, fuso_utm: e.target.value})}
                        placeholder="22S"
                      />
                    </div>

                    <div>
                      <Label>Latitude</Label>
                      <Input
                        value={technicalData.latitude}
                        onChange={(e) => setTechnicalData({...technicalData, latitude: e.target.value})}
                        placeholder="-16.291613"
                      />
                    </div>

                    <div>
                      <Label>Longitude</Label>
                      <Input
                        value={technicalData.longitude}
                        onChange={(e) => setTechnicalData({...technicalData, longitude: e.target.value})}
                        placeholder="-48.973249"
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
                        placeholder="64"
                      />
                    </div>
                  </div>
                </div>

                <div className="border-t pt-6 space-y-4">
                  <h3 className="text-lg font-semibold">Strings CC / MPPT</h3>
                  <p className="text-sm text-gray-600">
                    Em série: soma tensão (Voc), corrente permanece (Isc). Microinversor: 1 módulo/MPPT.
                  </p>
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <Label>Tipo de inversor</Label>
                      <Select
                        value={technicalData.tipo_inversor || 'STRING'}
                        onValueChange={(v) => setTechnicalData({...technicalData, tipo_inversor: v})}
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
                        value={technicalData.num_mppt}
                        onChange={(e) => setTechnicalData({...technicalData, num_mppt: e.target.value})}
                        placeholder="2"
                      />
                    </div>
                    <div>
                      <Label>Módulos por string (opcional)</Label>
                      <Input
                        type="number"
                        value={technicalData.modulos_por_string}
                        onChange={(e) => setTechnicalData({...technicalData, modulos_por_string: e.target.value})}
                        placeholder="Auto"
                      />
                    </div>
                  </div>
                </div>

                <div className="border-t pt-6 space-y-4">
                  <h3 className="text-lg font-semibold">Tabela de demanda — Tabela 1 · Levantamento de Carga</h3>
                  <p className="text-sm text-gray-600">
                    Informe a demanda-alvo (ex.: 7 kW residencial ou 20 kW comercial). Após calcular, preenche automaticamente o placeholder abaixo de &quot;Tabela 1 – Levantamento de Carga&quot; no memorial.
                  </p>
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
