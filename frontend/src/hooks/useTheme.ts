import { useContext } from 'react'
import { ThemeContext } from '../contexts/ThemeContext'
import type { ThemeContextType } from '../types/index'

// Custom hook to use theme context
export const useTheme = (): ThemeContextType => {
  const context = useContext(ThemeContext)
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}
