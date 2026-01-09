import { useState } from 'react'
import { useWorkspaceStore } from '../store/workspace'
import { api, Workspace } from '../lib/api'

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
  const [ragMode, setRagMode] = useState<'global' | 'precise' | 'comprehensive'>((workspace.rag_mode as 'global' | 'precise' | 'comprehensive') || 'global')
  const [saving, setSaving] = useState(false)
  const { setCurrentWorkspace, setWorkspaces, workspaces } = useWorkspaceStore()

  const handleSave = async () => {
    setSaving(true)
    try {
      const updated = await api.workspaces.update(workspace.id, {
        name,
        description,
        system_prompt: systemPrompt,
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

      <div>
        <label className="block text-sm font-medium text-dark-300 mb-2">RAG Quality</label>
        <div className="space-y-2">
          <label className="flex items-center gap-3 cursor-pointer p-3 rounded-lg hover:bg-dark-700 border border-dark-600">
            <input
              type="radio"
              checked={ragMode === 'global'}
              onChange={() => setRagMode('global')}
              className="w-4 h-4 text-blue-600"
            />
            <div>
              <span className="text-sm text-white font-medium">⚖️ Balanced</span>
              <span className="text-xs text-dark-500 ml-2">(recommended)</span>
              <p className="text-xs text-dark-400 mt-1">Standard quality, good for most use cases</p>
            </div>
          </label>
          <label className="flex items-center gap-3 cursor-pointer p-3 rounded-lg hover:bg-dark-700 border border-dark-600">
            <input
              type="radio"
              checked={ragMode === 'precise'}
              onChange={() => setRagMode('precise')}
              className="w-4 h-4 text-blue-600"
            />
            <div>
              <span className="text-sm text-white font-medium">🎯 Precise</span>
              <p className="text-xs text-dark-400 mt-1">Fast, focused answers with fewer documents</p>
            </div>
          </label>
          <label className="flex items-center gap-3 cursor-pointer p-3 rounded-lg hover:bg-dark-700 border border-dark-600">
            <input
              type="radio"
              checked={ragMode === 'comprehensive'}
              onChange={() => setRagMode('comprehensive')}
              className="w-4 h-4 text-blue-600"
            />
            <div>
              <span className="text-sm text-white font-medium">📚 Comprehensive</span>
              <p className="text-xs text-dark-400 mt-1">Thorough, detailed answers with more documents</p>
            </div>
          </label>
        </div>
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
