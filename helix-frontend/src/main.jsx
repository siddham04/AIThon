import { createRoot } from 'react-dom/client'

if (typeof document !== 'undefined') {
  const saved = localStorage.getItem('helix_theme')
  const useDark = saved !== 'light'
  document.documentElement.classList.add(useDark ? 'dark' : 'light-forced')
  if (!useDark) document.documentElement.classList.remove('dark')
}

/* GSAP + full visual stack (glass, gradients, product + legacy screen tokens) */
import './lib/gsapInit'
import './index.css'
import './styles/hackathon-fx.css'
import './styles/light-theme.css'
import './styles/helix-design.css'
import './styles/helix-native.css'
import './styles/fx.css'
import './styles/tidy.css'
import './styles/product-five.css'
import './styles/workspace.css'
import './styles/winning-demo.css'
import App from './App.jsx'
import AppErrorBoundary from './components/errors/AppErrorBoundary.jsx'

createRoot(document.getElementById('root')).render(
  <AppErrorBoundary>
    <App />
  </AppErrorBoundary>,
)
