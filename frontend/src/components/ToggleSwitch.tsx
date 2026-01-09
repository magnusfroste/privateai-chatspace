interface ToggleSwitchProps {
  enabled: boolean
  onChange: (enabled: boolean) => void
  label: string
  size?: 'sm' | 'md'
}

export default function ToggleSwitch({ 
  enabled, 
  onChange, 
  label,
  size = 'sm'
}: ToggleSwitchProps) {
  const switchSize = size === 'sm' 
    ? 'w-8 h-4' 
    : 'w-10 h-5'
  const dotSize = size === 'sm'
    ? 'w-3 h-3'
    : 'w-4 h-4'
  const dotTranslate = size === 'sm'
    ? 'translate-x-4'
    : 'translate-x-5'

  return (
    <button
      type="button"
      onClick={() => onChange(!enabled)}
      className="flex items-center gap-2 group"
    >
      <div
        className={`${switchSize} rounded-full transition-colors duration-200 ease-in-out relative ${
          enabled 
            ? 'bg-blue-600' 
            : 'bg-dark-600 group-hover:bg-dark-500'
        }`}
      >
        <div
          className={`${dotSize} absolute top-0.5 left-0.5 rounded-full bg-white shadow transition-transform duration-200 ease-in-out ${
            enabled ? dotTranslate : 'translate-x-0'
          }`}
        />
      </div>
      <span className={`text-sm transition-colors ${
        enabled ? 'text-white' : 'text-dark-400 group-hover:text-dark-300'
      }`}>
        {label}
      </span>
    </button>
  )
}
