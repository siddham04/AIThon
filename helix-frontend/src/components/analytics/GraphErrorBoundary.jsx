import { Component } from 'react'

/**
 * Isolates R3F / WebGL failures so the rest of Analytics stays usable.
 */
export default class GraphErrorBoundary extends Component {
  state = { error: null }

  static getDerivedStateFromError(error) {
    return { error }
  }

  render() {
    if (this.state.error) {
      return (
        <div className="graph-error-boundary" role="alert">
          <p className="graph-error-title">Trace graph unavailable</p>
          <p className="muted small">
            {this.state.error?.message || 'WebGL or Three.js failed to initialize.'}
          </p>
          <button
            type="button"
            className="btn ghost small"
            onClick={() => this.setState({ error: null })}
          >
            Retry
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
