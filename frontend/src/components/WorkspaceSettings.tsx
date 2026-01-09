import { useState } from 'react'
import { useWorkspaceStore } from '../store/workspace'
import { api, Workspace } from '../lib/api'
import { ChevronDown, ChevronRight } from 'lucide-react'

interface WorkspaceSettingsProps {
  workspace: Workspace
  onClose: () => void
}

export default function WorkspaceSettings({
  workspace,
  onClose,
}: WorkspaceSettingsProps) {
  const [name, setName] = useState(workspace.name)
  const [description, setDescription] = useState(workspace.description || '')
  const [systemPrompt, setSystemPrompt] = useState(workspace.system_prompt || '')
  const [chatMode, setChatMode] = useState<'chat' | 'query'>((workspace.chat_mode as 'chat' | 'query') || 'chat')
  const [ragMode, setRagMode] = useState<'global' | 'precise' | 'comprehensive'>((workspace.rag_mode as 'global' | 'precise' | 'comprehensive') || 'global')
  const [saving, setSaving] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const { setCurrentWorkspace, setWorkspaces, workspaces } = useWorkspaceStore()

  const handleSave = async () => {
    setSaving(true)
    try {
      const updated = await api.workspaces.update(workspace.id, {
        name,
        description,
        system_prompt: systemPrompt,
        chat_mode: chatMode,
        rag_mode: ragMode,
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

  return (
    <div className="p-6 space-y-5">
      <div>
        <label className="block text-sm font-medium text-dark-300 mb-1">Name</label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-dark-300 mb-1">Description</label>
        <input
          type="text"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
          placeholder="Optional description"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-dark-300 mb-1">System Prompt</label>
        <textarea
          value={systemPrompt}
          onChange={(e) => setSystemPrompt(e.target.value)}
          rows={6}
          className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-lg text-white focus:outline-none focus:border-blue-500 resize-y"
          placeholder="Instructions for the AI assistant..."
        />
      </div>

      {/* Advanced Settings - Collapsible */}
      <div className="border border-dark-600 rounded-lg">
        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-dark-300 hover:text-white transition-colors"
        >
          <span>Advanced Settings</span>
          {showAdvanced ? (
            <ChevronDown className="w-4 h-4" />
          ) : (
            <ChevronRight className="w-4 h-4" />
          )}
        </button>
        
        {showAdvanced && (
          <div className="px-4 pb-4 space-y-4 border-t border-dark-600">
            <div className="pt-4">
              <label className="block text-sm font-medium text-dark-300 mb-2">Chat Mode</label>
              <div className="flex gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    checked={chatMode === 'chat'}
                    onChange={() => setChatMode('chat')}
                    className="w-4 h-4 text-blue-600"
                  />
                  <span className="text-sm text-white">Chat</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    checked={chatMode === 'query'}
                    onChange={() => setChatMode('query')}
                    className="w-4 h-4 text-blue-600"
                  />
                  <span className="text-sm text-white">Query</span>
                </label>
              </div>
              <p className="mt-1 text-xs text-dark-500">
                Chat: AI uses docs + knowledge. Query: Only docs.
              </p>
            </div>

            <div className="pt-2">
              <label className="block text-sm font-medium text-dark-300 mb-2">RAG Quality</label>
              <div className="space-y-2">
                <label className="flex items-center gap-3 cursor-pointer p-2 rounded-lg hover:bg-dark-700">
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
                <label className="flex items-center gap-3 cursor-pointer p-2 rounded-lg hover:bg-dark-700">
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
                <label className="flex items-center gap-3 cursor-pointer p-2 rounded-lg hover:bg-dark-700">
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
          </div>
        )}
      </div>

      <div className="flex gap-2 pt-2">
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex-1 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 text-white font-medium rounded-lg transition-colors"
        >
          {saving ? 'Saving...' : 'Save'}
        </button>
        <button
          onClick={onClose}
          className="flex-1 py-2 bg-dark-700 hover:bg-dark-600 text-white font-medium rounded-lg transition-colors"
        >
          Cancel
        </button>
      </div>
    </div>
  )
}
