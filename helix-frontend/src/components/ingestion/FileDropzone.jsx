import { useCallback, useRef, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'

function formatBytes(n) {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

export default function FileDropzone({ onFile, disabled }) {
  const [meta, setMeta] = useState(null)
  const [preview, setPreview] = useState('')
  const rootRef = useRef(null)

  const onDrop = useCallback(
    (accepted) => {
      const file = accepted[0]
      if (!file) return
      setMeta({ name: file.name, size: file.size })
      const reader = new FileReader()
      reader.onload = () => {
        const text = String(reader.result || '')
        setPreview(text.slice(0, 200))
      }
      reader.readAsText(file)
      onFile?.(file)
    },
    [onFile],
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: false,
    disabled,
  })

  useGSAP(
    () => {
      const el = rootRef.current
      if (!el) return
      gsap.to(el, {
        scale: isDragActive ? 1.02 : 1,
        duration: 0.35,
        ease: 'power2.out',
      })
    },
    { dependencies: [isDragActive] },
  )

  return (
    <div
      ref={rootRef}
      {...getRootProps()}
      className={`file-drop ${isDragActive ? 'drag-active' : ''}`}
    >
      <input {...getInputProps()} />
      <p className="file-drop-title">Drop a requirements file here</p>
      <p className="file-drop-hint">TXT, MD, or PDF-backed text extraction on the server</p>
      {meta && (
        <div className="file-meta">
          <strong>{meta.name}</strong>
          <span>{formatBytes(meta.size)}</span>
        </div>
      )}
      {preview && (
        <pre className="file-preview">
          {preview}
          {preview.length >= 200 ? '…' : ''}
        </pre>
      )}
    </div>
  )
}
