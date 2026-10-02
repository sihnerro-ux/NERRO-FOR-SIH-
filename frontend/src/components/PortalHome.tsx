import { useState } from 'react'
import { ArrowRight, ArrowUpRight, CloudRain, MapPinned, Route, ShieldCheck, Truck, WifiOff, Check, ChevronDown } from 'lucide-react'
import { AccessibilityBar, PortalIdentity } from './PortalIdentity'
import { LoginScreen } from './LoginScreen'
import { RegionStories } from './RegionStories'
import type { AuthUser } from '../types/api'

const services = [
  { icon: Route, title: 'Plan a better route', text: 'Compare available roads with weather, field inputs and risk advisory.', role: 2, label: 'Logistics workspace' },
  { icon: MapPinned, title: 'Report from the field', text: 'Pin an incident, attach evidence and sync when you reconnect.', role: 1, label: 'Field officer workspace' },
  { icon: Truck, title: 'Keep deliveries moving', text: 'Review your assignment, share GPS and acknowledge route updates.', role: 5, label: 'Driver workspace' },
  { icon: ShieldCheck, title: 'See the whole picture', text: 'Review reports and coordinate accessibility decisions in one place.', role: 0, label: 'Control-room workspace' },
]
const states = ['Arunachal Pradesh', 'Assam', 'Manipur', 'Meghalaya', 'Mizoram', 'Nagaland', 'Sikkim', 'Tripura']

function Landscape() {
  return <div className="landscape-panel" aria-label="Illustration of a connected mountain supply route, not a live map">
    <div className="landscape-label"><span className="landscape-dot" /> CONNECTING THE LAST MILE <small>Illustrative network</small></div>
    <svg className="route-landscape" viewBox="0 0 600 470" role="img" aria-label="Illustrated mountain roads connecting a warehouse and hospital">
      <defs><linearGradient id="sky" x2="0" y2="1"><stop stopColor="#d9ede4"/><stop offset="1" stopColor="#f6f7ed"/></linearGradient><linearGradient id="hill" x2="0" y2="1"><stop stopColor="#227862"/><stop offset="1" stopColor="#114735"/></linearGradient></defs>
      <rect width="600" height="470" rx="20" fill="url(#sky)"/><circle cx="465" cy="98" r="44" fill="#f4b877"/>
      <path d="M0 235 90 107 152 180 242 64 364 226 455 137 600 243V470H0Z" fill="#b3cfc2"/>
      <path d="m182 140 60-76 64 86-45-17-19 14-17-23Z" fill="#f6faf5"/>
      <path d="M0 288 121 195 235 287 369 151 490 249 600 214V470H0Z" fill="#7fae97"/>
      <path d="M0 356Q110 210 254 334T600 270V470H0Z" fill="url(#hill)"/>
      <path d="M58 435C132 367 257 410 235 338S357 329 369 271 486 314 527 223" fill="none" stroke="#b6d1b9" strokeWidth="24"/>
      <path className="landscape-route" d="M58 435C132 367 257 410 235 338S357 329 369 271 486 314 527 223" fill="none" stroke="#fff7dc" strokeWidth="3" strokeDasharray="8 9"/>
      <g transform="translate(95 335)"><rect x="-26" y="-22" width="52" height="39" rx="4" fill="white"/><path d="m-32-22 32-20 32 20" fill="#efad6b"/><rect x="-10" y="-6" width="20" height="23" fill="#45826c"/><circle cy="40" r="8" fill="#f4a660" stroke="white" strokeWidth="4"/></g>
      <g transform="translate(491 189)"><rect x="-25" y="-25" width="50" height="41" rx="4" fill="white"/><path d="M-9-12H9M0-21V-3" stroke="#147453" strokeWidth="6"/><rect x="-8" y="3" width="16" height="13" fill="#a6c9b8"/><circle cx="24" cy="39" r="8" fill="#fff" stroke="#17664b" strokeWidth="4"/></g>
      <g fill="#e7f2e6"><path d="m34 275 13-26 13 26Zm15 25 16-32 16 32Zm381 65 13-26 13 26Zm28 21 16-32 16 32Z"/></g>
    </svg>
    <div className="landscape-note"><ShieldCheck size={22}/><div><strong>Every journey. A more informed decision.</strong><span>Roads + weather + field evidence</span></div></div>
  </div>
}

export function PortalHome({ onAuthenticated, onWorkspace }: { onAuthenticated: (user: AuthUser) => void; onWorkspace?: () => void }) {
  const [loginRole, setLoginRole] = useState<number | null>(null)
  const enter = (role = 0) => {
    if (onWorkspace) { onWorkspace(); return }
    setLoginRole(role)
    window.scrollTo({ top: 0, behavior: 'instant' })
  }
  return <div className="public-portal">
    <AccessibilityBar />
    <header className="portal-masthead"><PortalIdentity /></header>
    <nav className="portal-nav" aria-label="Main navigation"><div><button className={loginRole === null ? 'current' : ''} onClick={() => setLoginRole(null)}>Home</button><a href="#services" onClick={() => setLoginRole(null)}>Our services</a><a href="#how-it-works" onClick={() => setLoginRole(null)}>How it works</a><a href="#region" onClick={() => setLoginRole(null)}>The region</a><a href="#help" onClick={() => setLoginRole(null)}>Help & guidance</a></div><button className="portal-signin" onClick={() => enter()}>{onWorkspace ? 'My workspace' : 'Workspace sign in'}<ArrowUpRight size={17}/></button></nav>
    {loginRole !== null ? <div id="main-content" tabIndex={-1} className="portal-login-layout"><div className="portal-login-intro"><button className="text-link" onClick={() => setLoginRole(null)}>← Back to home</button><p className="portal-kicker">ONE PLATFORM. CONNECTED TEAMS.</p><h1>Your role.<br/>Your workspace.</h1><p>Access the tools you need to move essential supplies, report conditions and coordinate the next step.</p><ul><li><Check/>Role-based operational access</li><li><Check/>Shared, traceable instructions</li><li><Check/>Clearly labelled demonstration data</li></ul><img src="/icons/nerro.PNG" alt="NERRO" /></div><LoginScreen key={loginRole} initialRole={loginRole} onAuthenticated={onAuthenticated}/></div> : <main id="main-content" tabIndex={-1} className="portal-main">
      <section className="portal-hero"><div className="hero-copy"><p className="portal-kicker"><span/> SMART LOGISTICS FOR NORTH-EAST INDIA</p><h1>Connecting places.<br/>Delivering <em>possibilities.</em></h1><p className="hero-description">From essential medicines to everyday supplies. Make better journey decisions with road intelligence, weather insights and people on the ground.</p><div className="hero-buttons"><button className="primary" onClick={() => enter()}>Enter your workspace <ArrowRight size={18}/></button><a href="#how-it-works">Discover NERRO <ArrowUpRight size={18}/></a></div><div className="hero-assurances"><span><ShieldCheck size={17}/>Verified reports matter</span><span><WifiOff size={17}/>Offline field reporting</span></div></div><Landscape/></section>
      <RegionStories />
      <div className="portal-notice"><ShieldCheck size={21}/><p><strong>Built for informed decisions.</strong> SIH demonstration platform, not an official government service. ML predictions are advisory; verified evidence guides closure decisions.</p><a href="#help">Know more <ArrowRight size={16}/></a></div>
      <section id="services" className="portal-section"><div className="portal-section-head"><div><p className="portal-kicker">YOUR TASK, MADE SIMPLER</p><h2>One platform. A workspace for everyone.</h2></div><p>Purpose-built tools for the people<br/>behind every essential delivery.</p></div><div className="portal-service-grid">{services.map(({icon: Icon, ...service}, index) => <button className="portal-service" key={service.title} onClick={() => enter(service.role)}><div className="service-number"><span><Icon size={25}/></span><small>0{index + 1}</small></div><h3>{service.title}</h3><p>{service.text}</p><span className="service-link">{service.label}<ArrowUpRight size={18}/></span></button>)}</div></section>
      <section id="how-it-works" className="portal-process"><div><p className="portal-kicker">FROM INFORMATION TO ACTION</p><h2>A clearer path,<br/>at every step.</h2><p>Connected information. Human verification. A shared plan everyone can follow.</p><a href="#help">Understand the workflow <ArrowRight size={18}/></a></div><ol>{[{title:'Plan with context',text:'Choose locations and compare available routes using weather and risk advisory.',icon:Route},{title:'Verify what changes',text:'Field teams report conditions. Authorized reviewers assess the evidence.',icon:ShieldCheck},{title:'Coordinate the journey',text:'Assign a vehicle, acknowledge updates and confirm delivery handover.',icon:Truck}].map(({title,text,icon:Icon},i)=><li key={title}><span className="process-step">0{i+1}</span><div><h3>{title}</h3><p>{text}</p></div><Icon size={23}/></li>)}</ol></section>
      <section id="region" className="portal-section region-section"><div><p className="portal-kicker">EIGHT STATES. A SHARED PURPOSE.</p><h2>Across the North Eastern Region.</h2><p>Designed for connected operations across the region. Data coverage varies; representative assets and synthetic model inputs remain labelled.</p></div><div className="state-chips">{states.map(state=><span key={state}><MapPinned size={15}/>{state}</span>)}</div></section>
      <section id="help" className="portal-section portal-help"><div><p className="portal-kicker">BEFORE YOU BEGIN</p><h2>A little clarity goes a long way.</h2><p>Know what the platform can do, and where people remain in control.</p><CloudRain size={48}/></div><div>{[
        ['Is this an official government portal?', 'No. NERRO is an independently developed SIH prototype for problem statement 26002. Reference imagery does not indicate government endorsement.'],
        ['How do I choose my workspace?', 'Select a service above or Workspace sign in. Demo profiles help you test the available roles; permissions are enforced by the backend.'],
        ['Are all predictions and map records live?', 'No. Weather can use live forecasts, field reports come from users, and the model is trained on synthetic data. Check timestamps and source labels before making decisions.'],
        ['Can I test from outside North-East India?', 'Yes. Drivers can choose the clearly labelled NER demo GPS option. Your actual phone location is never silently moved into NER.'],
        ['What happens without a network?', 'Field reports can be queued for synchronization. Offline basemap coverage and locked-screen GPS tracking are not provided by this prototype.'],
      ].map(([q,a])=><details key={q}><summary>{q}<ChevronDown size={18}/></summary><p>{a}</p></details>)}</div></section>
    </main>}
    <footer className="portal-footer"><div><strong>NERRO</strong><span>North East · Route · Risk · Optimisation</span></div><p>Better information. Connected teams. Essential supplies.</p><small>SIH prototype · Not an official government portal</small><a href="#main-content">Back to top ↑</a></footer>
  </div>
}
