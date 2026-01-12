import { useState, useEffect } from 'react'
import { useAuthStore } from '../store/auth'
import {
  Play,
  Loader2,
  Trophy,
  BarChart3,
  ChevronDown,
  ChevronUp,
  Trash2,
  Plus,
  RefreshCw,
  X,
  Sparkles,
  Upload,
} from 'lucide-react'

interface ABTestRun {
  id: number
  name: string
  description?: string
  status: string
  num_queries: number
  num_documents: number
  winner?: string
  winner_reason?: string
  anythingllm_recall?: number
  anythingllm_mrr?: number
  anythingllm_avg_latency?: number
  privateai_recall?: number
  privateai_mrr?: number
  privateai_avg_latency?: number
  created_at: string
  completed_at?: string
}

interface QueryResult {
  id: number
  query_id: string
  query: string
  category?: string
  difficulty?: string
  ground_truth_docs?: string[]
  anythingllm: {
    answer?: string
    latency?: number
    faithfulness?: number
    relevancy?: number
    retrieved_docs?: string[]
    recall?: number
    mrr?: number
  }
  privateai: {
    answer?: string
    latency?: number
    faithfulness?: number
    relevancy?: number
    retrieved_docs?: string[]
    recall?: number
    mrr?: number
  }
  winner?: string
}

interface TestQuery {
  id: string
  query: string
  category?: string
  difficulty?: string
  ground_truth_docs?: string[]
}

export default function ABTestEvaluator() {
  const [runs, setRuns] = useState<ABTestRun[]>([])
  const [selectedRun, setSelectedRun] = useState<ABTestRun | null>(null)
  const [queryResults, setQueryResults] = useState<QueryResult[]>([])
  const [loading, setLoading] = useState(false)
  const [executing, setExecuting] = useState(false)
  const [showNewTest, setShowNewTest] = useState(false)
  const [expandedQuery, setExpandedQuery] = useState<number | null>(null)
  const [generating, setGenerating] = useState(false)
  const [numQuestionsToGenerate, setNumQuestionsToGenerate] = useState(10)

  // New test form
  const [testName, setTestName] = useState('')
  const [testDescription, setTestDescription] = useState('')
  const [anythingllmUrl, setAnythingllmUrl] = useState('https://chat.autoversio.ai')
  const [anythingllmApiKey, setAnythingllmApiKey] = useState('')
  const [anythingllmWorkspace, setAnythingllmWorkspace] = useState('rag-test')
  const [privateaiUrl, setPrivateaiUrl] = useState('http://localhost:8000')
  const [privateaiWorkspaceId, setPrivateaiWorkspaceId] = useState('2')
  const [queries, setQueries] = useState<TestQuery[]>([
    { id: 'q1', query: '', category: 'technical', ground_truth_docs: [] }
  ])

  useEffect(() => {
    loadRuns()
  }, [])

  const loadRuns = async () => {
    setLoading(true)
    try {
      const token = useAuthStore.getState().token
      const response = await fetch('/api/admin/abtest/runs', {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (response.ok) {
        const data = await response.json()
        setRuns(data)
      }
    } catch (err) {
      console.error('Failed to load runs:', err)
    } finally {
      setLoading(false)
    }
  }

  const loadRunDetails = async (runId: number) => {
    try {
      const token = useAuthStore.getState().token
      const response = await fetch(`/api/admin/abtest/runs/${runId}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (response.ok) {
        const data = await response.json()
        setSelectedRun(data.run)
        setQueryResults(data.queries)
      }
    } catch (err) {
      console.error('Failed to load run details:', err)
    }
  }

  const createTest = async () => {
    if (!testName || !anythingllmUrl || !anythingllmApiKey || queries.length === 0) {
      alert('Please fill in all required fields')
      return
    }

    const validQueries = queries.filter(q => q.query.trim())
    if (validQueries.length === 0) {
      alert('Please add at least one query')
      return
    }

    setLoading(true)
    try {
      const token = useAuthStore.getState().token
      const response = await fetch('/api/admin/abtest/runs', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          name: testName,
          description: testDescription,
          anythingllm_url: anythingllmUrl,
          anythingllm_api_key: anythingllmApiKey,
          anythingllm_workspace: anythingllmWorkspace,
          privateai_url: privateaiUrl,
          privateai_workspace_id: parseInt(privateaiWorkspaceId),
          queries: validQueries
        })
      })

      if (response.ok) {
        const data = await response.json()
        await loadRuns()
        setShowNewTest(false)
        resetForm()
        // Auto-select the new run
        loadRunDetails(data.id)
      } else {
        const error = await response.json()
        alert(`Error: ${error.detail || 'Failed to create test'}`)
      }
    } catch (err) {
      console.error('Failed to create test:', err)
      alert('Failed to create test')
    } finally {
      setLoading(false)
    }
  }

  const executeTest = async (runId: number) => {
    if (!anythingllmApiKey) {
      const key = prompt('Enter AnythingLLM API Key:')
      if (!key) return
      setAnythingllmApiKey(key)
    }

    setExecuting(true)
    try {
      const token = useAuthStore.getState().token
      const response = await fetch(
        `/api/admin/abtest/runs/${runId}/execute?anythingllm_api_key=${encodeURIComponent(anythingllmApiKey)}`,
        {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` }
        }
      )

      if (response.ok) {
        const data = await response.json()
        alert(`Test completed! Winner: ${data.winner}\n${data.winner_reason}`)
        await loadRuns()
        await loadRunDetails(runId)
      } else {
        const error = await response.json()
        alert(`Error: ${error.detail || 'Test execution failed'}`)
      }
    } catch (err) {
      console.error('Test execution failed:', err)
      alert('Test execution failed')
    } finally {
      setExecuting(false)
    }
  }

  const deleteRun = async (runId: number) => {
    if (!confirm('Delete this test run?')) return

    try {
      const token = useAuthStore.getState().token
      await fetch(`/api/admin/abtest/runs/${runId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      })
      await loadRuns()
      if (selectedRun?.id === runId) {
        setSelectedRun(null)
        setQueryResults([])
      }
    } catch (err) {
      console.error('Failed to delete run:', err)
    }
  }

  const resetForm = () => {
    setTestName('')
    setTestDescription('')
    setQueries([{ id: 'q1', query: '', category: 'technical', ground_truth_docs: [] }])
  }

  const addQuery = () => {
    setQueries([
      ...queries,
      { id: `q${queries.length + 1}`, query: '', category: 'technical', ground_truth_docs: [] }
    ])
  }

  const updateQuery = (index: number, field: keyof TestQuery, value: any) => {
    const updated = [...queries]
    updated[index] = { ...updated[index], [field]: value }
    setQueries(updated)
  }

  const removeQuery = (index: number) => {
    if (queries.length > 1) {
      setQueries(queries.filter((_, i) => i !== index))
    }
  }

  const generateQuestionsFromFiles = async (files: FileList) => {
    if (files.length === 0) return
    if (files.length > 5) {
      alert('Maximum 5 files allowed')
      return
    }

    setGenerating(true)
    try {
      const token = useAuthStore.getState().token
      const formData = new FormData()
      
      for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i])
      }

      const response = await fetch(
        `/api/admin/abtest/generate-questions?num_questions=${numQuestionsToGenerate}`,
        {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
          body: formData
        }
      )

      if (response.ok) {
        const data = await response.json()
        
        if (data.success && data.questions) {
          // Convert generated questions to TestQuery format
          const generatedQueries: TestQuery[] = data.questions.map((q: any, i: number) => ({
            id: `gen_${i + 1}`,
            query: q.query,
            category: q.category || 'technical',
            difficulty: q.difficulty || 'medium',
            ground_truth_docs: q.ground_truth_docs || []
          }))
          
          setQueries(generatedQueries)
          
          // Auto-fill test name if empty
          if (!testName) {
            setTestName(`Auto-generated test (${data.documents.join(', ')})`)
          }
          
          alert(`Generated ${data.num_questions} questions from ${data.documents.length} document(s)!`)
        } else {
          alert(`Generation failed: ${data.error || 'Unknown error'}`)
          console.error('Raw response:', data.raw_response)
        }
      } else {
        const error = await response.json()
        alert(`Error: ${error.detail || 'Failed to generate questions'}`)
      }
    } catch (err) {
      console.error('Failed to generate questions:', err)
      alert('Failed to generate questions')
    } finally {
      setGenerating(false)
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-500/20 text-green-400 border-green-500/30'
      case 'running':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
      case 'failed':
        return 'bg-red-500/20 text-red-400 border-red-500/30'
      default:
        return 'bg-gray-500/20 text-gray-400 border-gray-500/30'
    }
  }

  const getWinnerBadge = (winner?: string) => {
    if (winner === 'PrivateAI') return 'bg-purple-500/20 text-purple-400 border-purple-500/30'
    if (winner === 'AnythingLLM') return 'bg-blue-500/20 text-blue-400 border-blue-500/30'
    return 'bg-gray-500/20 text-gray-400 border-gray-500/30'
  }

  const formatPercent = (value?: number) => {
    if (value === undefined || value === null) return '-'
    return `${(value * 100).toFixed(0)}%`
  }

  const formatLatency = (value?: number) => {
    if (value === undefined || value === null) return '-'
    return `${(value / 1000).toFixed(1)}s`
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-medium text-white">A/B Test Evaluator</h2>
          <p className="text-sm text-dark-400">Compare AnythingLLM vs Private AI RAG performance</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={loadRuns}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-1.5 bg-dark-700 text-dark-300 hover:bg-dark-600 rounded-lg text-sm"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={() => setShowNewTest(!showNewTest)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm ${
              showNewTest ? 'bg-red-600 text-white' : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
          >
            {showNewTest ? <X className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
            {showNewTest ? 'Cancel' : 'New Test'}
          </button>
        </div>
      </div>

      {/* New Test Form */}
      {showNewTest && (
        <div className="bg-dark-800 rounded-xl p-4 space-y-4">
          <h3 className="text-sm font-medium text-white">Create New A/B Test</h3>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-dark-400 mb-1">Test Name *</label>
              <input
                type="text"
                value={testName}
                onChange={(e) => setTestName(e.target.value)}
                placeholder="e.g., MJP Technical Docs Test"
                className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-white text-sm"
              />
            </div>
            <div>
              <label className="block text-sm text-dark-400 mb-1">Description</label>
              <input
                type="text"
                value={testDescription}
                onChange={(e) => setTestDescription(e.target.value)}
                placeholder="Optional description"
                className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-white text-sm"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-3">
              <h4 className="text-sm font-medium text-blue-400">AnythingLLM</h4>
              <div>
                <label className="block text-xs text-dark-400 mb-1">URL</label>
                <input
                  type="text"
                  value={anythingllmUrl}
                  onChange={(e) => setAnythingllmUrl(e.target.value)}
                  className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-white text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-dark-400 mb-1">API Key *</label>
                <input
                  type="password"
                  value={anythingllmApiKey}
                  onChange={(e) => setAnythingllmApiKey(e.target.value)}
                  placeholder="Enter API key"
                  className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-white text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-dark-400 mb-1">Workspace</label>
                <input
                  type="text"
                  value={anythingllmWorkspace}
                  onChange={(e) => setAnythingllmWorkspace(e.target.value)}
                  className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-white text-sm"
                />
              </div>
            </div>

            <div className="space-y-3">
              <h4 className="text-sm font-medium text-purple-400">Private AI</h4>
              <div>
                <label className="block text-xs text-dark-400 mb-1">URL</label>
                <input
                  type="text"
                  value={privateaiUrl}
                  onChange={(e) => setPrivateaiUrl(e.target.value)}
                  className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-white text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-dark-400 mb-1">Workspace ID</label>
                <input
                  type="text"
                  value={privateaiWorkspaceId}
                  onChange={(e) => setPrivateaiWorkspaceId(e.target.value)}
                  className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-white text-sm"
                />
              </div>
            </div>
          </div>

          {/* Queries */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-medium text-white">Test Queries</h4>
              <div className="flex items-center gap-2">
                <button
                  onClick={addQuery}
                  className="flex items-center gap-1 px-2 py-1 text-xs bg-dark-700 text-dark-300 hover:bg-dark-600 rounded"
                >
                  <Plus className="w-3 h-3" /> Add Query
                </button>
              </div>
            </div>
            
            {/* Auto-generate from PDFs */}
            <div className="bg-dark-700/50 border border-dashed border-dark-500 rounded-lg p-3">
              <div className="flex items-center gap-3">
                <Sparkles className="w-5 h-5 text-yellow-400" />
                <div className="flex-1">
                  <p className="text-sm text-white font-medium">Auto-generate questions from PDFs</p>
                  <p className="text-xs text-dark-400">Upload 1-5 PDFs and let AI create test questions</p>
                </div>
                <div className="flex items-center gap-2">
                  <select
                    value={numQuestionsToGenerate}
                    onChange={(e) => setNumQuestionsToGenerate(parseInt(e.target.value))}
                    className="bg-dark-600 border border-dark-500 rounded px-2 py-1 text-white text-xs"
                  >
                    <option value={5}>5 questions</option>
                    <option value={10}>10 questions</option>
                    <option value={15}>15 questions</option>
                    <option value={20}>20 questions</option>
                  </select>
                  <label className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm cursor-pointer ${
                    generating ? 'bg-dark-600 text-dark-400' : 'bg-yellow-600 hover:bg-yellow-700 text-white'
                  }`}>
                    {generating ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Generating...
                      </>
                    ) : (
                      <>
                        <Upload className="w-4 h-4" />
                        Upload PDFs
                      </>
                    )}
                    <input
                      type="file"
                      accept=".pdf,.txt,.md"
                      multiple
                      disabled={generating}
                      onChange={(e) => e.target.files && generateQuestionsFromFiles(e.target.files)}
                      className="hidden"
                    />
                  </label>
                </div>
              </div>
            </div>
            
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {queries.map((q, i) => (
                <div key={i} className="flex gap-2 items-start bg-dark-700 rounded-lg p-2">
                  <div className="flex-1 space-y-2">
                    <input
                      type="text"
                      value={q.query}
                      onChange={(e) => updateQuery(i, 'query', e.target.value)}
                      placeholder="Enter test query..."
                      className="w-full bg-dark-600 border border-dark-500 rounded px-2 py-1 text-white text-sm"
                    />
                    <div className="flex gap-2">
                      <select
                        value={q.category || 'technical'}
                        onChange={(e) => updateQuery(i, 'category', e.target.value)}
                        className="bg-dark-600 border border-dark-500 rounded px-2 py-1 text-white text-xs"
                      >
                        <option value="technical">Technical</option>
                        <option value="legal">Legal</option>
                        <option value="product">Product</option>
                      </select>
                      <input
                        type="text"
                        value={(q.ground_truth_docs || []).join(', ')}
                        onChange={(e) => updateQuery(i, 'ground_truth_docs', e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
                        placeholder="Ground truth docs (comma-separated)"
                        className="flex-1 bg-dark-600 border border-dark-500 rounded px-2 py-1 text-white text-xs"
                      />
                    </div>
                  </div>
                  <button
                    onClick={() => removeQuery(i)}
                    className="p-1 text-dark-500 hover:text-red-400"
                    disabled={queries.length === 1}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          <div className="flex justify-end">
            <button
              onClick={createTest}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-dark-600 text-white rounded-lg text-sm font-medium"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
              Create Test
            </button>
          </div>
        </div>
      )}

      {/* Test Runs List */}
      <div className="bg-dark-800 rounded-xl p-4">
        <h3 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
          <BarChart3 className="w-4 h-4" />
          Test Runs ({runs.length})
        </h3>
        
        {runs.length === 0 ? (
          <p className="text-dark-400 text-sm">No test runs yet. Create one to get started.</p>
        ) : (
          <div className="space-y-2">
            {runs.map((run) => (
              <div
                key={run.id}
                className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                  selectedRun?.id === run.id
                    ? 'bg-dark-700 border-blue-500/50'
                    : 'bg-dark-700/50 border-dark-600 hover:border-dark-500'
                }`}
                onClick={() => loadRunDetails(run.id)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className={`px-2 py-0.5 rounded text-xs border ${getStatusBadge(run.status)}`}>
                      {run.status}
                    </span>
                    <span className="text-white font-medium">{run.name}</span>
                    <span className="text-dark-400 text-xs">{run.num_queries} queries</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {run.winner && (
                      <span className={`px-2 py-0.5 rounded text-xs border ${getWinnerBadge(run.winner)}`}>
                        {run.winner}
                      </span>
                    )}
                    {run.status === 'pending' && (
                      <button
                        onClick={(e) => { e.stopPropagation(); executeTest(run.id); }}
                        disabled={executing}
                        className="flex items-center gap-1 px-2 py-1 bg-green-600 hover:bg-green-700 text-white rounded text-xs"
                      >
                        {executing ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
                        Run
                      </button>
                    )}
                    <button
                      onClick={(e) => { e.stopPropagation(); deleteRun(run.id); }}
                      className="p-1 text-dark-500 hover:text-red-400"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                
                {run.status === 'completed' && (
                  <div className="mt-2 grid grid-cols-4 gap-4 text-xs">
                    <div>
                      <span className="text-dark-400">AnythingLLM Recall:</span>
                      <span className="ml-1 text-blue-400">{formatPercent(run.anythingllm_recall)}</span>
                    </div>
                    <div>
                      <span className="text-dark-400">Private AI Recall:</span>
                      <span className="ml-1 text-purple-400">{formatPercent(run.privateai_recall)}</span>
                    </div>
                    <div>
                      <span className="text-dark-400">AnythingLLM MRR:</span>
                      <span className="ml-1 text-blue-400">{formatPercent(run.anythingllm_mrr)}</span>
                    </div>
                    <div>
                      <span className="text-dark-400">Private AI MRR:</span>
                      <span className="ml-1 text-purple-400">{formatPercent(run.privateai_mrr)}</span>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Selected Run Details */}
      {selectedRun && (
        <div className="space-y-4">
          {/* Winner Banner */}
          {selectedRun.winner && (
            <div className={`rounded-xl p-4 border ${getWinnerBadge(selectedRun.winner)}`}>
              <div className="flex items-center gap-3">
                <Trophy className="w-6 h-6" />
                <div>
                  <div className="font-medium">Winner: {selectedRun.winner}</div>
                  <p className="text-sm opacity-80">{selectedRun.winner_reason}</p>
                </div>
              </div>
            </div>
          )}

          {/* Metrics Comparison */}
          {selectedRun.status === 'completed' && (
            <div className="grid grid-cols-2 gap-4">
              {/* AnythingLLM */}
              <div className="bg-dark-800 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-3 h-3 rounded-full bg-blue-500" />
                  <span className="font-medium text-white">AnythingLLM</span>
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-dark-400">Recall@5</span>
                    <span className="text-blue-400">{formatPercent(selectedRun.anythingllm_recall)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-dark-400">MRR</span>
                    <span className="text-blue-400">{formatPercent(selectedRun.anythingllm_mrr)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-dark-400">Avg Latency</span>
                    <span className="text-blue-400">{formatLatency(selectedRun.anythingllm_avg_latency)}</span>
                  </div>
                </div>
              </div>

              {/* Private AI */}
              <div className="bg-dark-800 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-3 h-3 rounded-full bg-purple-500" />
                  <span className="font-medium text-white">Private AI</span>
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-dark-400">Recall@5</span>
                    <span className="text-purple-400">{formatPercent(selectedRun.privateai_recall)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-dark-400">MRR</span>
                    <span className="text-purple-400">{formatPercent(selectedRun.privateai_mrr)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-dark-400">Avg Latency</span>
                    <span className="text-purple-400">{formatLatency(selectedRun.privateai_avg_latency)}</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Query Results */}
          <div className="bg-dark-800 rounded-xl p-4">
            <h3 className="text-sm font-medium text-white mb-3">Query Results ({queryResults.length})</h3>
            <div className="space-y-2">
              {queryResults.map((q) => (
                <div key={q.id} className="bg-dark-700 rounded-lg overflow-hidden">
                  <button
                    onClick={() => setExpandedQuery(expandedQuery === q.id ? null : q.id)}
                    className="w-full flex items-center justify-between p-3 hover:bg-dark-600"
                  >
                    <div className="flex items-center gap-3 text-left">
                      <span className="text-dark-400 text-xs">{q.query_id}</span>
                      <span className="text-white text-sm truncate max-w-md">{q.query}</span>
                      {q.category && (
                        <span className="px-2 py-0.5 bg-dark-600 rounded text-xs text-dark-300">{q.category}</span>
                      )}
                    </div>
                    <div className="flex items-center gap-3">
                      {q.winner && (
                        <span className={`px-2 py-0.5 rounded text-xs border ${getWinnerBadge(q.winner)}`}>
                          {q.winner}
                        </span>
                      )}
                      <div className="flex items-center gap-2 text-xs">
                        <span className="text-blue-400">R:{formatPercent(q.anythingllm.recall)}</span>
                        <span className="text-purple-400">R:{formatPercent(q.privateai.recall)}</span>
                      </div>
                      {expandedQuery === q.id ? (
                        <ChevronUp className="w-4 h-4 text-dark-400" />
                      ) : (
                        <ChevronDown className="w-4 h-4 text-dark-400" />
                      )}
                    </div>
                  </button>
                  
                  {expandedQuery === q.id && (
                    <div className="p-3 border-t border-dark-600 space-y-3">
                      <div className="grid grid-cols-2 gap-4">
                        {/* AnythingLLM Answer */}
                        <div>
                          <div className="text-xs text-blue-400 mb-1">AnythingLLM Response</div>
                          <div className="bg-dark-800 rounded p-2 text-xs text-dark-300 max-h-32 overflow-y-auto">
                            {q.anythingllm.answer || 'No response'}
                          </div>
                          <div className="mt-1 text-xs text-dark-500">
                            Latency: {formatLatency(q.anythingllm.latency)} | 
                            Docs: {(q.anythingllm.retrieved_docs || []).join(', ') || 'none'}
                          </div>
                        </div>
                        
                        {/* Private AI Answer */}
                        <div>
                          <div className="text-xs text-purple-400 mb-1">Private AI Response</div>
                          <div className="bg-dark-800 rounded p-2 text-xs text-dark-300 max-h-32 overflow-y-auto">
                            {q.privateai.answer || 'No response'}
                          </div>
                          <div className="mt-1 text-xs text-dark-500">
                            Latency: {formatLatency(q.privateai.latency)} | 
                            Docs: {(q.privateai.retrieved_docs || []).join(', ') || 'none'}
                          </div>
                        </div>
                      </div>
                      
                      {q.ground_truth_docs && q.ground_truth_docs.length > 0 && (
                        <div className="text-xs text-dark-400">
                          Ground truth docs: {q.ground_truth_docs.join(', ')}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tips */}
      <div className="bg-dark-800/50 rounded-xl p-4 text-sm text-dark-400">
        <h4 className="font-medium text-dark-300 mb-2">💡 Tips för A/B-testning</h4>
        <ul className="space-y-1 list-disc list-inside">
          <li><strong>Ground truth docs</strong> - Ange förväntade dokument för att mäta Recall</li>
          <li><strong>Recall@5</strong> - Hur många av rätt dokument hittades i top 5</li>
          <li><strong>MRR</strong> - Position för första rätta dokumentet (högre = bättre)</li>
          <li><strong>Kör flera tester</strong> - Spara och jämför resultat över tid</li>
        </ul>
      </div>
    </div>
  )
}
