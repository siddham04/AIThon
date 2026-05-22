import { useParams } from 'react-router-dom'
import WorkspaceChat from '../components/workspace/WorkspaceChat'
import { SDLC_COPILOT_STARTERS } from '../lib/sdlcAgents'

export default function CopilotChat() {
  const { id } = useParams()
  return (
    <div className="p5-copilot-wrap">
      <WorkspaceChat
        projectId={id}
        examplePrompts={SDLC_COPILOT_STARTERS}
        variant="copilot"
        loadSuggestedFromApi
      />
    </div>
  )
}
