/** Strip active content from Mermaid SVG before DOM insertion. */
const FORBIDDEN_TAGS = new Set([
  'script',
  'foreignobject',
  'iframe',
  'object',
  'embed',
  'link',
])

export function mountSanitizedSvg(container, svgString) {
  if (!container) return false
  const parser = new DOMParser()
  const doc = parser.parseFromString(svgString, 'image/svg+xml')
  if (doc.querySelector('parsererror')) return false

  const root = doc.documentElement
  if (!root || root.nodeName.toLowerCase() !== 'svg') return false

  const walker = doc.createTreeWalker(root, NodeFilter.SHOW_ELEMENT)
  let node = walker.currentNode
  while (node) {
    const tag = node.nodeName.toLowerCase()
    if (FORBIDDEN_TAGS.has(tag)) {
      node.remove()
    } else {
      for (const attr of [...node.attributes]) {
        const name = attr.name.toLowerCase()
        if (name.startsWith('on') || name === 'href' && /^javascript:/i.test(attr.value)) {
          node.removeAttribute(attr.name)
        }
      }
    }
    node = walker.nextNode()
  }

  container.replaceChildren()
  container.appendChild(doc.importNode(root, true))
  return true
}
