import { useEffect, useState } from 'react'
import { api } from '../services/api'

interface Props {
  source: string
  className: string
  alt?: string
}

export function EvidenceImage({ source, className, alt = 'Field evidence' }: Props) {
  const [imageSource, setImageSource] = useState(source.startsWith('data:') ? source : '')

  useEffect(() => {
    if (source.startsWith('data:')) {
      setImageSource(source)
      return
    }
    let objectUrl = ''
    let cancelled = false
    api.evidenceBlob(source).then((blob) => {
      if (cancelled) return
      objectUrl = URL.createObjectURL(blob)
      setImageSource(objectUrl)
    }).catch(() => setImageSource(''))
    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [source])

  return imageSource ? <img className={className} src={imageSource} alt={alt} /> : null
}
