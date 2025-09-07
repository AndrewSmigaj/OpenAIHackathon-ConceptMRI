import { ReactNode } from 'react'

interface ActionCardProps {
  title: string
  description: string
  icon: ReactNode
  buttonText: string
  buttonColor: 'blue' | 'green' | 'purple' | 'orange'
  onClick: () => void
  disabled?: boolean
  loading?: boolean
}

const colorClasses = {
  blue: {
    iconBg: 'bg-blue-100',
    iconText: 'text-blue-600',
    button: 'bg-blue-600 hover:bg-blue-700 focus:ring-blue-500',
  },
  green: {
    iconBg: 'bg-green-100',
    iconText: 'text-green-600',
    button: 'bg-green-600 hover:bg-green-700 focus:ring-green-500',
  },
  purple: {
    iconBg: 'bg-purple-100',
    iconText: 'text-purple-600',
    button: 'bg-purple-600 hover:bg-purple-700 focus:ring-purple-500',
  },
  orange: {
    iconBg: 'bg-orange-100',
    iconText: 'text-orange-600',
    button: 'bg-orange-600 hover:bg-orange-700 focus:ring-orange-500',
  },
}

export default function ActionCard({
  title,
  description,
  icon,
  buttonText,
  buttonColor,
  onClick,
  disabled = false,
  loading = false
}: ActionCardProps) {
  const colors = colorClasses[buttonColor]
  const isDisabled = disabled || loading

  return (
    <div className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow">
      <div className="p-6">
        <div className="flex items-center mb-4">
          <div className={`w-12 h-12 ${colors.iconBg} rounded-lg flex items-center justify-center`}>
            <div className={colors.iconText}>
              {icon}
            </div>
          </div>
          <h3 className="text-xl font-semibold text-gray-900 ml-3">{title}</h3>
        </div>
        <p className="text-gray-600 mb-4">
          {description}
        </p>
        <button
          onClick={onClick}
          disabled={isDisabled}
          aria-label={`${buttonText} - ${title}`}
          className={`
            w-full py-2 px-4 text-white rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2
            ${isDisabled 
              ? 'bg-gray-400 cursor-not-allowed' 
              : colors.button
            }
          `}
        >
          {loading ? (
            <div className="flex items-center justify-center">
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
              Loading...
            </div>
          ) : (
            buttonText
          )}
        </button>
      </div>
    </div>
  )
}