import { useState, useEffect } from 'react'
import { useWorkspaceStore } from '../store/workspace'
import { api, Workspace } from '../lib/api'
import { 
  Settings, 
  X, 
  ChevronLeft,
  ChevronRight,
  Save,
  Loader2
} from 'lucide-react'

interface WorkspaceSettingsSidebarProps {
  workspace: Workspace
  isOpen: boolean
  isExpanded: boolean
  onToggleExpand: () => void
  onClose: () => void
  rightOffset?: number
}

export default function WorkspaceSettingsSidebar({
  workspace,
  isOpen,
  isExpanded,
  onToggleExpand,
  onClose,
  rightOffset = 0,
}: WorkspaceSettingsSidebarProps) {
  const [name, setName] = useState(workspace.name)
  const [description, setDescription] = useState(workspace.description || '')
  const [systemPrompt, setSystemPrompt] = useState(workspace.system_prompt || '')
  const [ragMode, setRagMode] = useState<'global' | 'precise' | 'comprehensive'>((workspace.rag_mode as 'global' | 'precise' | 'comprehensive') || 'global')
  const [useReranking, setUseReranking] = useState(workspace.use_reranking || false)
  const [rerankTopK, setRerankTopK] = useState(workspace.rerank_top_k || 20)
  const [useQueryExpansion, setUseQueryExpansion] = useState(workspace.use_query_expansion || false)
  const [saving, setSaving] = useState(false)
  const { setCurrentWorkspace, setWorkspaces, workspaces } = useWorkspaceStore()

  // Sync state when workspace changes
  useEffect(() => {
    setName(workspace.name)
    setDescription(workspace.description || '')
    setSystemPrompt(workspace.system_prompt || '')
    setRagMode((workspace.rag_mode as 'global' | 'precise' | 'comprehensive') || 'global')
    setUseReranking(workspace.use_reranking || false)
    setRerankTopK(workspace.rerank_top_k || 20)
    setUseQueryExpansion(workspace.use_query_expansion || false)
  }, [workspace.id, workspace.name, workspace.description, workspace.system_prompt, workspace.rag_mode, workspace.use_reranking, workspace.rerank_top_k, workspace.use_query_expansion])

  const handleSave = async () => {
    setSaving(true)
    try {
      const updated = await api.workspaces.update(workspace.id, {
        name,
        description,
        system_prompt: systemPrompt,
        rag_mode: ragMode,
        use_reranking: useReranking,
        rerank_top_k: rerankTopK,
        use_query_expansion: useQueryExpansion,
      })
      setCurrentWorkspace(updated)
      setWorkspaces(workspaces.map((w) => (w.id === updated.id ? updated : w)))
      onClose()
    } catch (err) {
      console.error('Failed to update workspace:', err)
    } finally {
      setSaving(false)
    }
  }

  if (!isOpen) return null

  const width = isExpanded ? 'w-[800px]' : 'w-64'

  return (
    <div 
      className={`fixed top-0 h-full ${width} bg-dark-800 border-l border-dark-700 flex flex-col z-40 transition-all duration-300`}
      style={{ right: `${rightOffset}px` }}
    >
      {/* Header */}
      <div className="h-14 border-b border-dark-700 flex items-center justify-between px-4">
        <div className="flex items-center gap-2">
          <button
            onClick={onToggleExpand}
            className="p-1 text-dark-400 hover:text-white hover:bg-dark-700 rounded"
            title={isExpanded ? 'Collapse' : 'Expand'}
          >
            {isExpanded ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
          <Settings className="w-5 h-5 text-blue-400" />
          {isExpanded && <h2 className="text-lg font-medium text-white">Workspace Settings</h2>}
        </div>
        <button
          onClick={onClose}
          className="p-2 text-dark-400 hover:text-white hover:bg-dark-700 rounded-lg"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Content */}
      {isExpanded ? (
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-dark-300 mb-1">Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 bg-dark-900 border border-dark-600 rounded text-white text-sm focus:outline-none focus:border-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-dark-300 mb-1">Description</label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 bg-dark-900 border border-dark-600 rounded text-white text-sm focus:outline-none focus:border-blue-500"
              placeholder="Optional description"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-dark-300 mb-1">System Prompt</label>
            <textarea
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              rows={8}
              className="w-full px-3 py-2 bg-dark-900 border border-dark-600 rounded text-white text-sm focus:outline-none focus:border-blue-500 resize-y font-mono"
              placeholder="Instructions for the AI assistant..."
            />
          </div>

          {/* RAG Quality - directly visible */}
          <div>
            <label className="block text-sm font-medium text-dark-300 mb-2">RAG Quality</label>
            <p className="text-xs text-dark-500 mb-2">How documents are searched when RAG is enabled</p>
            <div className="space-y-1">
              <label className="flex items-center gap-3 cursor-pointer p-2 rounded hover:bg-dark-700 border border-transparent hover:border-dark-600">
                <input
                  type="radio"
                  checked={ragMode === 'global'}
                  onChange={() => setRagMode('global')}
                  className="w-4 h-4 text-blue-600"
                />
                <div>
                  <span className="text-sm text-white">⚖️ Balanced</span>
                  <span className="text-xs text-dark-500 ml-2">(recommended)</span>
                </div>
              </label>
              <label className="flex items-center gap-3 cursor-pointer p-2 rounded hover:bg-dark-700 border border-transparent hover:border-dark-600">
                <input
                  type="radio"
                  checked={ragMode === 'precise'}
                  onChange={() => setRagMode('precise')}
                  className="w-4 h-4 text-blue-600"
                />
                <div>
                  <span className="text-sm text-white">🎯 Precise</span>
                  <span className="text-xs text-dark-500 ml-2">Fast, focused answers</span>
                </div>
              </label>
              <label className="flex items-center gap-3 cursor-pointer p-2 rounded hover:bg-dark-700 border border-transparent hover:border-dark-600">
                <input
                  type="radio"
                  checked={ragMode === 'comprehensive'}
                  onChange={() => setRagMode('comprehensive')}
                  className="w-4 h-4 text-blue-600"
                />
                <div>
                  <span className="text-sm text-white">📚 Comprehensive</span>
                  <span className="text-xs text-dark-500 ml-2">Thorough, detailed answers</span>
                </div>
              </label>
            </div>
          </div>

          {/* Reranking Section */}
          <div className="border-t border-dark-600 pt-4">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={useReranking}
                onChange={(e) => setUseReranking(e.target.checked)}
                className="w-4 h-4 text-blue-600 rounded"
              />
              <div className="flex-1">
                <span className="text-sm text-white font-medium">🎯 Accuracy Optimized (Reranking)</span>
                <p className="text-xs text-dark-400 mt-1">Use cross-encoder for better relevance (slower, +100-200ms)</p>
              </div>
            </label>
            {useReranking && (
              <div className="mt-3 ml-7">
                <label className="block text-xs font-medium text-dark-300 mb-1">Rerank Candidates</label>
                <input
                  type="number"
                  value={rerankTopK}
                  onChange={(e) => setRerankTopK(Math.max(5, Math.min(50, parseInt(e.target.value) || 20)))}
                  min="5"
                  max="50"
                  className="w-24 px-2 py-1 bg-dark-900 border border-dark-600 rounded text-white text-sm focus:outline-none focus:border-blue-500"
                />
                <span className="text-xs text-dark-400 ml-2">documents (5-50)</span>
              </div>
            )}
            
            {/* Query Expansion */}
            <label className="flex items-center gap-3 cursor-pointer mt-4">
              <input
                type="checkbox"
                checked={useQueryExpansion}
                onChange={(e) => setUseQueryExpansion(e.target.checked)}
                className="w-4 h-4 text-blue-600 rounded"
              />
              <div className="flex-1">
                <span className="text-sm text-white font-medium">🔍 Query Expansion</span>
                <p className="text-xs text-dark-400 mt-1">LLM generates query variants for better recall (+200ms)</p>
              </div>
            </label>
          </div>

          <div className="flex gap-2 pt-2">
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex-1 flex items-center justify-center gap-2 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 text-white font-medium rounded transition-colors"
            >
              {saving ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4" />
                  Save
                </>
              )}
            </button>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-dark-700 hover:bg-dark-600 text-white font-medium rounded transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto p-3 space-y-3">
          <div className="text-xs text-dark-400 truncate" title={workspace.name}>
            <span className="text-dark-500">Name:</span> {workspace.name}
          </div>
          <div className="text-xs text-dark-400">
            <span className="text-dark-500">RAG:</span> {ragMode === 'global' ? '⚖️' : ragMode === 'precise' ? '🎯' : '📚'}
          </div>
          {workspace.system_prompt && (
            <div className="text-xs text-dark-500 line-clamp-3">
              {workspace.system_prompt.slice(0, 100)}...
            </div>
          )}
          <button
            onClick={onToggleExpand}
            className="w-full mt-4 py-2 text-xs text-dark-400 hover:text-white bg-dark-700 hover:bg-dark-600 rounded transition-colors"
          >
            Expand to edit
          </button>
        </div>
      )}
    </div>
  )
}
