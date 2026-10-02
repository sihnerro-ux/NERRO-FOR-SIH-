import { useEffect, useState } from 'react'
import { Accessibility, ArrowUpRight } from 'lucide-react'

export function PortalIdentity() {
  return <div className="portal-identity">
    <img className="national-emblem" src="/icons/national%20emblem.png" alt="National Emblem of India" />
    <div className="identity-divider" />
    <img className="nerro-logo" src="/icons/nerro.PNG" alt="NERRO — North East Route Risk Optimisation" />
    <div className="identity-copy"><strong>North East. Better connected.</strong><span>Logistics & accessibility intelligence</span><small>SIH prototype · Problem statement 26002</small></div>
    <img className="tricolour-art" src="/icons/flag.png" alt="Indian tricolour artwork" />
  </div>
}

export function AccessibilityBar({ target = 'main-content' }: { target?: string }) {
  const [size, setSize] = useState(() => {
    try { return Number(localStorage.getItem('nerro-text-size')) === 20 ? 20 : 17 } catch { return 17 }
  })
  const [contrast, setContrast] = useState(false)
  useEffect(() => {
    document.documentElement.style.fontSize = `${size}px`
    try { localStorage.setItem('nerro-text-size', String(size)) } catch { /* Optional preference. */ }
  }, [size])
  useEffect(() => { document.documentElement.classList.toggle('high-contrast', contrast) }, [contrast])
  return <div className="accessibility-bar"><a href={`#${target}`}>Skip to main content <ArrowUpRight size={13} /></a><span className="prototype-caption">Built for North-East India · Demonstration platform</span><div><button aria-label="Use standard text size" aria-pressed={size === 17} onClick={() => setSize(17)}>A</button><button aria-label="Use larger text size" aria-pressed={size === 20} onClick={() => setSize(20)}>A+</button><button aria-label="Toggle high contrast" aria-pressed={contrast} onClick={() => setContrast(!contrast)}><Accessibility size={17} /><span>Contrast</span></button></div></div>
}
