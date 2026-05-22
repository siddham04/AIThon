import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist', 'src/pages/_archive/**']),
  {
    files: ['**/*.{js,jsx}'],
    extends: [
      js.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    rules: {
      'react-hooks/set-state-in-effect': 'off',
      'react-hooks/refs': 'off',
      'react-refresh/only-export-components': 'off',
    },
  },
  {
    files: [
      'src/pages/MissionControl.jsx',
      'src/pages/AiWorkspace.jsx',
      'src/pages/WinningDemoScreen.jsx',
      'src/pages/DeliveryCommandCenter.jsx',
      'src/components/workspace/WorkspaceChat.jsx',
      'src/components/workspace/WorkspaceArtifact.jsx',
      'src/components/export/JiraCsvPreview.jsx',
      'src/components/traceability/TraceabilityFlowAnimator.jsx',
      'src/components/layout/AppShell.jsx',
      'src/lib/workspaceActions.js',
      'src/lib/winningDemoFlow.js',
    ],
    rules: {
      'react-hooks/set-state-in-effect': 'error',
      'react-hooks/refs': 'error',
    },
  },
  {
    files: ['middleware.js'],
    languageOptions: { globals: globals.node },
  },
])
