import { useEffect, useState } from 'react'
import { ArrowRight, MapPin, Pause, Play } from 'lucide-react'

const stories = [
  {
    topic: 'THE REGION WE CONNECT', title: 'Extraordinary landscapes. Essential journeys.',
    text: 'Across hills, valleys and remote communities, every delivery needs context. NERRO brings weather forecasts, field reports and route-risk advisory into one shared workspace.',
    note: 'The current ML model uses synthetic training data. Its advice supports, not replaces, human decisions.',
    image: 'meghalaya-valley.jpg', place: 'Laitmawsiang, Meghalaya', alt: 'Clouds drifting between steep green valleys in Laitmawsiang, Meghalaya',
    action: 'See how NERRO works', href: '#how-it-works',
    author: 'Rajesh Dutta', license: 'CC BY 2.0', licenseUrl: 'https://creativecommons.org/licenses/by/2.0/',
    source: 'https://commons.wikimedia.org/wiki/File:Nature_Scenic_Landscape_Meghalaya_Laitmawsiang_India_July_2011.jpg',
  },
  {
    topic: 'UNDERSTANDING EARTHQUAKES', title: 'A moving Earth beneath the mountains.',
    text: 'Tectonic movement around the Himalaya and Indo-Burmese region builds stress along faults. When faults suddenly slip, that energy is released as an earthquake.',
    note: 'NERRO does not predict earthquakes. Field evidence helps teams assess reported damage and road accessibility.',
    image: 'sela-lake.jpg', place: 'Sela Lake, Arunachal Pradesh', alt: 'Cloud-covered mountain slopes and a road beside Sela Lake in Arunachal Pradesh',
    action: 'Learn the science · USGS', href: 'https://www.usgs.gov/publications/seismicity-earth-1900-2010-himalaya-and-vicinity',
    author: 'Rohit Sharma', license: 'CC BY-SA 4.0', licenseUrl: 'https://creativecommons.org/licenses/by-sa/4.0/',
    source: 'https://commons.wikimedia.org/wiki/File:Sela_Lake_near_Sela_pass,_Arunachal_Pradesh,_India.jpg',
  },
  {
    topic: 'WEATHER TO ROAD AWARENESS', title: 'When the rain changes, the journey can too.',
    text: 'Heavy or prolonged rain can saturate slopes and trigger landslides. Weather forecasts add context; geotagged reports help teams understand what is happening on the ground.',
    note: 'A rainfall forecast is not proof of a blocked road. Authorized reviewers verify reports before closure decisions.',
    image: 'meghalaya-hills.jpg', place: 'Cherrapunjee, Meghalaya', alt: 'Rolling green hills beneath rain clouds near Cherrapunjee in Meghalaya',
    action: 'Explore rainfall and landslides · USGS', href: 'https://www.usgs.gov/programs/landslide-hazards/science/overview-rainfall-induced-landslides',
    author: 'Ashwin Kumar', license: 'CC BY-SA 2.0', licenseUrl: 'https://creativecommons.org/licenses/by-sa/2.0/',
    source: 'https://commons.wikimedia.org/wiki/File:Rolling_hills_Geography_Cherrapunjee_Landscape_Meghalaya_India.jpg',
  },
]

export function RegionStories() {
  const [active, setActive] = useState(0)
  const [playing, setPlaying] = useState(() => !window.matchMedia('(prefers-reduced-motion: reduce)').matches)
  const [visible, setVisible] = useState(() => !document.hidden)
  useEffect(() => {
    const motion = window.matchMedia('(prefers-reduced-motion: reduce)')
    const changeMotion = () => { if (motion.matches) setPlaying(false) }
    const changeVisibility = () => setVisible(!document.hidden)
    motion.addEventListener('change', changeMotion)
    document.addEventListener('visibilitychange', changeVisibility)
    return () => { motion.removeEventListener('change', changeMotion); document.removeEventListener('visibilitychange', changeVisibility) }
  }, [])
  useEffect(() => {
    if (!playing || !visible) return
    const timer = window.setInterval(() => setActive(index => (index + 1) % stories.length), 10000)
    return () => window.clearInterval(timer)
  }, [playing, visible])
  const story = stories[active]
  return <section className="region-stories" aria-label="North-East landscapes and learning" aria-roledescription="carousel"
    onFocusCapture={event => { if (event.target.closest('.story-copy') && event.target.matches(':focus-visible')) setPlaying(false) }}>
    <div className="story-stage" aria-live={playing ? 'off' : 'polite'}>
      {stories.map((item, index) => <img key={item.image} className={`story-photo${index === active ? ' is-active' : ''}`} src={`/images/${item.image}`} alt={index === active ? item.alt : ''} aria-hidden={index !== active} loading="lazy" decoding="async" />)}
      <div className="story-shade" />
      <div className="story-copy" key={story.topic} role="group" aria-roledescription="slide" aria-label={`${active + 1} of ${stories.length}`}>
        <p className="story-kicker">{story.topic}</p><h2>{story.title}</h2><p className="story-description">{story.text}</p>
        <a className="story-link" href={story.href} {...(story.href.startsWith('https:') ? { target: '_blank', rel: 'noopener noreferrer' } : {})}>{story.action}<ArrowRight size={18}/></a>
        <p className="story-note">{story.note}</p>
      </div>
      <span className="story-place"><MapPin size={16}/>{story.place}</span>
    </div>
    <div className="story-toolbar"><div className="story-controls">
      <button aria-label={playing ? 'Pause slideshow' : 'Play slideshow'} onClick={() => setPlaying(value => !value)}>{playing ? <Pause size={18}/> : <Play size={18}/>}</button>
      <span className="story-count">0{active + 1} / 0{stories.length}</span>
      <span className="story-count">{playing ? 'Auto slideshow' : 'Slideshow paused'}</span>
    </div>
      <span className="story-caption">Landscape photographs · not live incident imagery</span>
    </div>
    <details className="story-credits"><summary>Photography credits & licences</summary><ul>{stories.map(item => <li key={item.image}><a href={item.source} target="_blank" rel="noopener noreferrer">{item.place}</a> — {item.author} · <a href={item.licenseUrl} target="_blank" rel="noopener noreferrer">{item.license}</a></li>)}</ul><p>Wikimedia Commons thumbnails. Display-cropped with a colour overlay; source photographs are unchanged.</p></details>
  </section>
}
