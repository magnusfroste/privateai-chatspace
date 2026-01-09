import { useState, useEffect } from 'react'
import { api } from '../lib/api'
import { useAuthStore } from '../store/auth'
import {
  Play,
  Loader2,
  Trophy,
  FileText,
  Layers,
  BarChart3,
  ChevronDown,
  ChevronUp,
  Save,
  History,
  Trash2,
} from 'lucide-react'

interface EvaluableDocument {
  id: number
  filename: string
  embedded_at: string
}

interface Workspace {
  id: number
  name: string
}

interface EvaluationScores {
  relevans: number
  fullständighet: number
  precision: number
  läsbarhet: number
  total: number
}

interface ComparisonResult {
  question: string
  rag: {
    response: string
    response_tokens: number
    context_tokens: number
    time_seconds: number
    chunks_retrieved: number
  }
  cag: {
    response: string
    response_tokens: number
    context_tokens: number
    time_seconds: number
    document_words: number
  }
  evaluation: {
    rag_scores: EvaluationScores
    cag_scores: EvaluationScores
    winner: 'RAG' | 'CAG' | 'TIE'
    reasoning: string
  } | null
}

export default function RagEvaluator() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [selectedWorkspace, setSelectedWorkspace] = useState<number | null>(null)
  const [documents, setDocuments] = useState<EvaluableDocument[]>([])
  const [selectedDocument, setSelectedDocument] = useState<number | null>(null)
  const [question, setQuestion] = useState('')
  const [topN, setTopN] = useState(5)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ComparisonResult | null>(null)
  const [history, setHistory] = useState<ComparisonResult[]>([])
  const [savedHistory, setSavedHistory] = useState<any[]>([])
  const [expandedResponse, setExpandedResponse] = useState<'rag' | 'cag' | null>(null)
  const [saving, setSaving] = useState(false)
  const [showSavedHistory, setShowSavedHistory] = useState(false)

  useEffect(() => {
    loadWorkspaces()
    loadSavedHistory()
  }, [])

  useEffect(() => {
    if (selectedWorkspace) {
      loadDocuments(selectedWorkspace)
    }
  }, [selectedWorkspace])

  const loadWorkspaces = async () => {
    try {
      const data = await api.admin.systemOverview()
      setWorkspaces(data.workspaces.map((w: any) => ({ id: w.id, name: w.name })))
    } catch (err) {
      console.error('Failed to load workspaces:', err)
    }
  }

  const loadSavedHistory = async () => {
    try {
      const token = useAuthStore.getState().token
      const response = await fetch('/api/admin/evaluate/history?limit=20', {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (response.ok) {
        const data = await response.json()
        setSavedHistory(data)
      }
    } catch (err) {
      console.error('Failed to load saved history:', err)
    }
  }

  const saveResult = async () => {
    if (!result || !selectedWorkspace || !selectedDocument) return
    
    setSaving(true)
    try {
      const token = useAuthStore.getState().token
      const selectedDoc = documents.find(d => d.id === selectedDocument)
      
      const response = await fetch('/api/admin/evaluate/save', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          workspace_id: selectedWorkspace,
          document_id: selectedDocument,
          document_name: selectedDoc?.filename,
          ...result
        })
      })
      
      if (response.ok) {
        await loadSavedHistory()
        alert('Evaluation saved!')
      }
    } catch (err) {
      console.error('Failed to save:', err)
    } finally {
      setSaving(false)
    }
  }

  const loadSavedEvaluation = async (id: number) => {
    try {
      const token = useAuthStore.getState().token
      const response = await fetch(`/api/admin/evaluate/history/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (response.ok) {
        const data = await response.json()
        setResult(data)
        setQuestion(data.question)
      }
    } catch (err) {
      console.error('Failed to load evaluation:', err)
    }
  }

  const deleteSavedEvaluation = async (id: number) => {
    if (!confirm('Delete this evaluation?')) return
    
    try {
      const token = useAuthStore.getState().token
      await fetch(`/api/admin/evaluate/history/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      })
      await loadSavedHistory()
    } catch (err) {
      console.error('Failed to delete:', err)
    }
  }

  const loadDocuments = async (workspaceId: number) => {
    try {
      const token = useAuthStore.getState().token
      const response = await fetch(`/api/admin/evaluate/documents/${workspaceId}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (response.ok) {
        const data = await response.json()
        setDocuments(data)
        if (data.length > 0) {
          setSelectedDocument(data[0].id)
        }
      }
    } catch (err) {
      console.error('Failed to load documents:', err)
    }
  }

  const runEvaluation = async () => {
    if (!selectedWorkspace || !selectedDocument || !question.trim()) return

    setLoading(true)
    setResult(null)

    try {
      const token = useAuthStore.getState().token
      const response = await fetch('/api/admin/evaluate/compare', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          workspace_id: selectedWorkspace,
          document_id: selectedDocument,
          question: question.trim(),
          top_n: topN
        })
      })

      if (response.ok) {
        const data = await response.json()
        setResult(data)
        setHistory(prev => [data, ...prev].slice(0, 10))
      } else {
        const error = await response.json()
        alert(`Error: ${error.detail || 'Evaluation failed'}`)
      }
    } catch (err) {
      console.error('Evaluation failed:', err)
      alert('Evaluation failed')
    } finally {
      setLoading(false)
    }
  }

  const getScoreColor = (score: number) => {
    if (score >= 9) return 'text-green-400'
    if (score >= 7) return 'text-yellow-400'
    if (score >= 5) return 'text-orange-400'
    return 'text-red-400'
  }

  const getWinnerBadge = (winner: string) => {
    if (winner === 'RAG') return 'bg-blue-500/20 text-blue-400 border-blue-500/30'
    if (winner === 'CAG') return 'bg-purple-500/20 text-purple-400 border-purple-500/30'
    return 'bg-gray-500/20 text-gray-400 border-gray-500/30'
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-medium text-white">RAG Evaluator</h2>
          <p className="text-sm text-dark-400">Compare RAG vs CAG response quality</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowSavedHistory(!showSavedHistory)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm ${
              showSavedHistory ? 'bg-blue-600 text-white' : 'bg-dark-700 text-dark-300 hover:bg-dark-600'
            }`}
          >
            <History className="w-4 h-4" />
            Saved ({savedHistory.length})
          </button>
          {result && (
            <button
              onClick={saveResult}
              disabled={saving}
              className="flex items-center gap-2 px-3 py-1.5 bg-green-600 hover:bg-green-700 disabled:bg-dark-600 text-white rounded-lg text-sm"
            >
              <Save className="w-4 h-4" />
              {saving ? 'Saving...' : 'Save'}
            </button>
          )}
        </div>
      </div>

      {/* Saved History Panel */}
      {showSavedHistory && savedHistory.length > 0 && (
        <div className="bg-dark-800 rounded-xl p-4">
          <h3 className="text-sm font-medium text-white mb-3">Saved Evaluations</h3>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {savedHistory.map((h) => (
              <div
                key={h.id}
                className="flex items-center justify-between p-2 bg-dark-700 rounded-lg text-sm"
              >
                <div 
                  className="flex-1 cursor-pointer hover:text-white text-dark-300"
                  onClick={() => loadSavedEvaluation(h.id)}
                >
                  <div className="truncate">{h.question}</div>
                  <div className="text-xs text-dark-500">
                    {h.document_name} • {new Date(h.created_at).toLocaleDateString()}
                  </div>
                </div>
                <div className="flex items-center gap-2 ml-2">
                  <span className="text-blue-400 text-xs">RAG: {h.rag_score || '?'}</span>
                  <span className="text-purple-400 text-xs">CAG: {h.cag_score || '?'}</span>
                  <span className={`px-2 py-0.5 rounded text-xs ${getWinnerBadge(h.winner)}`}>
                    {h.winner}
                  </span>
                  <button
                    onClick={(e) => { e.stopPropagation(); deleteSavedEvaluation(h.id); }}
                    className="p-1 text-dark-500 hover:text-red-400"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Configuration */}
      <div className="bg-dark-800 rounded-xl p-4 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm text-dark-400 mb-1">Workspace</label>
            <select
              value={selectedWorkspace || ''}
              onChange={(e) => setSelectedWorkspace(Number(e.target.value))}
              className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-white text-sm"
            >
              <option value="">Select workspace...</option>
              {workspaces.map(w => (
                <option key={w.id} value={w.id}>{w.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm text-dark-400 mb-1">Document (for CAG)</label>
            <select
              value={selectedDocument || ''}
              onChange={(e) => setSelectedDocument(Number(e.target.value))}
              className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-white text-sm"
              disabled={!selectedWorkspace}
            >
              <option value="">Select document...</option>
              {documents.map(d => (
                <option key={d.id} value={d.id}>{d.filename}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm text-dark-400 mb-1">RAG Chunks (top_n)</label>
            <select
              value={topN}
              onChange={(e) => setTopN(Number(e.target.value))}
              className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-white text-sm"
            >
              {[3, 5, 7, 10, 15].map(n => (
                <option key={n} value={n}>{n} chunks</option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm text-dark-400 mb-1">Question</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Enter your test question..."
              className="flex-1 bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-white text-sm"
              onKeyDown={(e) => e.key === 'Enter' && runEvaluation()}
            />
            <button
              onClick={runEvaluation}
              disabled={loading || !selectedWorkspace || !selectedDocument || !question.trim()}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-dark-600 disabled:text-dark-400 text-white rounded-lg text-sm font-medium"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              Evaluate
            </button>
          </div>
        </div>
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-4">
          {/* Winner Banner */}
          {result.evaluation && (
            <div className={`rounded-xl p-4 border ${getWinnerBadge(result.evaluation.winner)}`}>
              <div className="flex items-center gap-3">
                <Trophy className="w-6 h-6" />
                <div>
                  <div className="font-medium">
                    Winner: {result.evaluation.winner}
                    {result.evaluation.winner === 'TIE' && ' (Draw)'}
                  </div>
                  <p className="text-sm opacity-80">{result.evaluation.reasoning}</p>
                </div>
              </div>
            </div>
          )}

          {/* Scores Comparison */}
          {result.evaluation && result.evaluation.rag_scores && (
            <div className="grid grid-cols-2 gap-4">
              {/* RAG Scores */}
              <div className="bg-dark-800 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-3">
                  <Layers className="w-5 h-5 text-blue-400" />
                  <span className="font-medium text-white">RAG</span>
                  <span className={`ml-auto text-2xl font-bold ${getScoreColor(result.evaluation.rag_scores.total)}`}>
                    {result.evaluation.rag_scores.total}
                  </span>
                </div>
                <div className="space-y-2 text-sm">
                  {Object.entries(result.evaluation.rag_scores).filter(([k]) => k !== 'total').map(([key, value]) => (
                    <div key={key} className="flex justify-between">
                      <span className="text-dark-400 capitalize">{key}</span>
                      <span className={getScoreColor(value as number)}>{value as number}/10</span>
                    </div>
                  ))}
                </div>
                <div className="mt-3 pt-3 border-t border-dark-700 text-xs text-dark-400 space-y-1">
                  <div className="flex justify-between">
                    <span>Chunks</span>
                    <span>{result.rag.chunks_retrieved}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Time</span>
                    <span>{result.rag.time_seconds}s</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Context</span>
                    <span>{(result.rag.context_tokens / 1000).toFixed(1)}k tokens</span>
                  </div>
                </div>
              </div>

              {/* CAG Scores */}
              <div className="bg-dark-800 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-3">
                  <FileText className="w-5 h-5 text-purple-400" />
                  <span className="font-medium text-white">CAG</span>
                  <span className={`ml-auto text-2xl font-bold ${getScoreColor(result.evaluation.cag_scores.total)}`}>
                    {result.evaluation.cag_scores.total}
                  </span>
                </div>
                <div className="space-y-2 text-sm">
                  {Object.entries(result.evaluation.cag_scores).filter(([k]) => k !== 'total').map(([key, value]) => (
                    <div key={key} className="flex justify-between">
                      <span className="text-dark-400 capitalize">{key}</span>
                      <span className={getScoreColor(value as number)}>{value as number}/10</span>
                    </div>
                  ))}
                </div>
                <div className="mt-3 pt-3 border-t border-dark-700 text-xs text-dark-400 space-y-1">
                  <div className="flex justify-between">
                    <span>Doc words</span>
                    <span>{(result.cag.document_words / 1000).toFixed(1)}k</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Time</span>
                    <span>{result.cag.time_seconds}s</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Context</span>
                    <span>{(result.cag.context_tokens / 1000).toFixed(1)}k tokens</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Responses */}
          <div className="space-y-2">
            {/* RAG Response */}
            <div className="bg-dark-800 rounded-xl overflow-hidden">
              <button
                onClick={() => setExpandedResponse(expandedResponse === 'rag' ? null : 'rag')}
                className="w-full flex items-center justify-between p-4 hover:bg-dark-700"
              >
                <div className="flex items-center gap-2">
                  <Layers className="w-4 h-4 text-blue-400" />
                  <span className="text-white font-medium">RAG Response</span>
                  <span className="text-dark-400 text-sm">({result.rag.response_tokens} tokens)</span>
                </div>
                {expandedResponse === 'rag' ? (
                  <ChevronUp className="w-4 h-4 text-dark-400" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-dark-400" />
                )}
              </button>
              {expandedResponse === 'rag' && (
                <div className="px-4 pb-4">
                  <div className="bg-dark-900 rounded-lg p-4 text-sm text-dark-300 whitespace-pre-wrap max-h-96 overflow-y-auto">
                    {result.rag.response}
                  </div>
                </div>
              )}
            </div>

            {/* CAG Response */}
            <div className="bg-dark-800 rounded-xl overflow-hidden">
              <button
                onClick={() => setExpandedResponse(expandedResponse === 'cag' ? null : 'cag')}
                className="w-full flex items-center justify-between p-4 hover:bg-dark-700"
              >
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-purple-400" />
                  <span className="text-white font-medium">CAG Response</span>
                  <span className="text-dark-400 text-sm">({result.cag.response_tokens} tokens)</span>
                </div>
                {expandedResponse === 'cag' ? (
                  <ChevronUp className="w-4 h-4 text-dark-400" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-dark-400" />
                )}
              </button>
              {expandedResponse === 'cag' && (
                <div className="px-4 pb-4">
                  <div className="bg-dark-900 rounded-lg p-4 text-sm text-dark-300 whitespace-pre-wrap max-h-96 overflow-y-auto">
                    {result.cag.response}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* History */}
      {history.length > 0 && (
        <div className="bg-dark-800 rounded-xl p-4">
          <h3 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
            <BarChart3 className="w-4 h-4" />
            Evaluation History
          </h3>
          <div className="space-y-2">
            {history.map((h, i) => (
              <div
                key={i}
                className="flex items-center justify-between p-2 bg-dark-700 rounded-lg text-sm cursor-pointer hover:bg-dark-600"
                onClick={() => setResult(h)}
              >
                <span className="text-dark-300 truncate flex-1">{h.question}</span>
                {h.evaluation && (
                  <div className="flex items-center gap-3 ml-2">
                    <span className="text-blue-400">RAG: {h.evaluation.rag_scores?.total || '?'}</span>
                    <span className="text-purple-400">CAG: {h.evaluation.cag_scores?.total || '?'}</span>
                    <span className={`px-2 py-0.5 rounded text-xs ${getWinnerBadge(h.evaluation.winner)}`}>
                      {h.evaluation.winner}
                    </span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tips */}
      <div className="bg-dark-800/50 rounded-xl p-4 text-sm text-dark-400">
        <h4 className="font-medium text-dark-300 mb-2">💡 Tips för utvärdering</h4>
        <ul className="space-y-1 list-disc list-inside">
          <li><strong>Breda frågor</strong> ("Summera dokumentet") → CAG vinner ofta</li>
          <li><strong>Specifika frågor</strong> ("Vad kostar X?") → RAG kan vara bättre</li>
          <li><strong>Stora dokument</strong> → RAG är snabbare och billigare</li>
          <li><strong>Små dokument</strong> → CAG ger ofta bättre fullständighet</li>
        </ul>
      </div>
    </div>
  )
}
