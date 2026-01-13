import { useState, useEffect } from 'react'
import { api } from '../lib/api'
import { Settings, RotateCcw, Save, Loader2 } from 'lucide-react'
import ToggleSwitch from './ToggleSwitch'

interface Setting {
  value: any
  type: string
  description: string
  source: string
}

interface SettingsGroup {
  title: string
  icon: string
  keys: string[]
}

const SETTINGS_GROUPS: SettingsGroup[] = [
  {
    title: 'Application',
    icon: '🏠',
    keys: ['app_name']
  },
  {
    title: 'LLM Parameters',
    icon: '🤖',
    keys: ['llm_model', 'llm_temperature', 'llm_top_p', 'llm_repetition_penalty']
  },
  {
    title: 'Default RAG Settings',
    icon: '📚',
    keys: ['default_top_n', 'default_similarity_threshold', 'default_use_hybrid_search']
  },
  {
    title: 'RAG Quality Presets',
    icon: '🎯',
    keys: ['rag_precise_top_n', 'rag_precise_threshold', 'rag_comprehensive_top_n', 'rag_comprehensive_threshold']
  },
  {
    title: 'Features',
    icon: '⚡',
    keys: ['mcp_enabled', 'pdf_provider']
  },
  {
    title: 'Vector Database',
    icon: '🗄️',
    keys: ['vector_store']
  }
]

const SETTING_LABELS: Record<string, string> = {
  app_name: 'Application Name',
  llm_model: 'LLM Model',
  llm_temperature: 'Temperature',
  llm_top_p: 'Top P',
  llm_repetition_penalty: 'Repetition Penalty',
  default_top_n: 'Default Top N',
  default_similarity_threshold: 'Default Similarity Threshold',
  default_use_hybrid_search: 'Use Hybrid Search',
  rag_precise_top_n: 'Precise Mode: Top N',
  rag_precise_threshold: 'Precise Mode: Threshold',
  rag_comprehensive_top_n: 'Comprehensive Mode: Top N',
  rag_comprehensive_threshold: 'Comprehensive Mode: Threshold',
  mcp_enabled: 'MCP Tool Calling (Web Search)',
  pdf_provider: 'PDF Provider',
  vector_store: 'Vector Database',
}

export default function SystemSettings() {
  const [settings, setSettings] = useState<Record<string, Setting>>({})
  const [editedValues, setEditedValues] = useState<Record<string, any>>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState<string | null>(null)

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      const data = await api.admin.getSettings()
      setSettings(data)
      // Initialize edited values with current values
      const initial: Record<string, any> = {}
      Object.entries(data).forEach(([key, setting]) => {
        initial[key] = setting.value
      })
      setEditedValues(initial)
    } catch (err) {
      console.error('Failed to load settings:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async (key: string) => {
    setSaving(key)
    try {
      const result = await api.admin.updateSetting(key, editedValues[key])
      setSettings(prev => ({
        ...prev,
        [key]: { ...prev[key], value: result.value, source: result.source }
      }))
    } catch (err) {
      console.error('Failed to save setting:', err)
    } finally {
      setSaving(null)
    }
  }

  const handleReset = async (key: string) => {
    setSaving(key)
    try {
      const result = await api.admin.resetSetting(key)
      setSettings(prev => ({
        ...prev,
        [key]: { ...prev[key], value: result.value, source: result.source }
      }))
      setEditedValues(prev => ({ ...prev, [key]: result.value }))
    } catch (err) {
      console.error('Failed to reset setting:', err)
    } finally {
      setSaving(null)
    }
  }

  const hasChanges = (key: string) => {
    const current = settings[key]?.value
    const edited = editedValues[key]
    return String(current) !== String(edited)
  }

  const renderInput = (key: string, setting: Setting) => {
    const value = editedValues[key]
    
    if (setting.type === 'bool') {
      return (
        <ToggleSwitch
          enabled={value}
          onChange={(v) => setEditedValues(prev => ({ ...prev, [key]: v }))}
        />
      )
    }
    
    if (setting.type === 'float') {
      return (
        <input
          type="number"
          step="0.01"
          value={value ?? ''}
          onChange={(e) => setEditedValues(prev => ({ ...prev, [key]: parseFloat(e.target.value) || 0 }))}
          className="w-32 px-3 py-1.5 bg-dark-800 border border-dark-600 rounded text-white text-sm"
        />
      )
    }
    
    if (setting.type === 'int') {
      return (
        <input
          type="number"
          step="1"
          value={value ?? ''}
          onChange={(e) => setEditedValues(prev => ({ ...prev, [key]: parseInt(e.target.value) || 0 }))}
          className="w-32 px-3 py-1.5 bg-dark-800 border border-dark-600 rounded text-white text-sm"
        />
      )
    }
    
    // String - check for select options
    if (key === 'pdf_provider') {
      return (
        <select
          value={value ?? ''}
          onChange={(e) => setEditedValues(prev => ({ ...prev, [key]: e.target.value }))}
          className="px-3 py-1.5 bg-dark-800 border border-dark-600 rounded text-white text-sm"
        >
          <option value="docling-api">Docling API (GPU)</option>
          <option value="marker-api">Marker API (GPU)</option>
          <option value="pdfplumber">pdfplumber (Local)</option>
        </select>
      )
    }
    
    if (key === 'vector_store') {
      return (
        <select
          value={value ?? 'qdrant'}
          onChange={(e) => setEditedValues(prev => ({ ...prev, [key]: e.target.value }))}
          className="px-3 py-1.5 bg-dark-800 border border-dark-600 rounded text-white text-sm"
        >
          <option value="qdrant">Qdrant (Hybrid Search)</option>
          <option value="lancedb">LanceDB (Simple)</option>
        </select>
      )
    }
    
    return (
      <input
        type="text"
        value={value ?? ''}
        onChange={(e) => setEditedValues(prev => ({ ...prev, [key]: e.target.value }))}
        className="w-64 px-3 py-1.5 bg-dark-800 border border-dark-600 rounded text-white text-sm"
      />
    )
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-dark-400" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3 mb-6">
        <Settings className="w-6 h-6 text-blue-400" />
        <h2 className="text-xl font-semibold text-white">System Settings</h2>
        <span className="text-xs text-dark-400 bg-dark-700 px-2 py-1 rounded">
          Overrides .env defaults
        </span>
      </div>

      {SETTINGS_GROUPS.map(group => (
        <div key={group.title} className="bg-dark-800 rounded-lg border border-dark-700 overflow-hidden">
          <div className="px-4 py-3 bg-dark-750 border-b border-dark-700">
            <h3 className="font-medium text-white flex items-center gap-2">
              <span>{group.icon}</span>
              {group.title}
            </h3>
          </div>
          <div className="divide-y divide-dark-700">
            {group.keys.map(key => {
              const setting = settings[key]
              if (!setting) return null
              
              return (
                <div key={key} className="px-4 py-3 flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-white text-sm font-medium">
                        {SETTING_LABELS[key] || key}
                      </span>
                      {setting.source === 'database' && (
                        <span className="text-[10px] bg-blue-500/20 text-blue-400 px-1.5 py-0.5 rounded">
                          customized
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-dark-400 mt-0.5">{setting.description}</p>
                  </div>
                  
                  <div className="flex items-center gap-3">
                    {renderInput(key, setting)}
                    
                    {hasChanges(key) && (
                      <button
                        onClick={() => handleSave(key)}
                        disabled={saving === key}
                        className="p-1.5 bg-green-600 hover:bg-green-700 text-white rounded disabled:opacity-50"
                        title="Save"
                      >
                        {saving === key ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Save className="w-4 h-4" />
                        )}
                      </button>
                    )}
                    
                    {setting.source === 'database' && !hasChanges(key) && (
                      <button
                        onClick={() => handleReset(key)}
                        disabled={saving === key}
                        className="p-1.5 text-dark-400 hover:text-white hover:bg-dark-700 rounded"
                        title="Reset to default"
                      >
                        <RotateCcw className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      ))}
      
      <p className="text-xs text-dark-500 text-center">
        Settings marked "customized" override .env defaults. Click ↺ to reset to default.
      </p>
    </div>
  )
}
