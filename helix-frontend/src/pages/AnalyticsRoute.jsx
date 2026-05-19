import { useParams } from 'react-router-dom'
import Analytics from './Analytics'

export default function AnalyticsRoute() {
  const { id } = useParams()
  return <Analytics key={id} />
}
