import { useCallback, useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Activity,
  ArrowLeft,
  AlertTriangle,
  Bell,
  Boxes,
  ChevronRight,
  CircleGauge,
  CloudRain,
  Download,
  Map,
  MapPin,
  LogOut,
  LayoutGrid,
  Menu,
  Navigation,
  PackageCheck,
  Radio,
  RefreshCw,
  Route,
  Search,
  ShieldAlert,
  Truck,
  Users,
} from 'lucide-react'
import { OperationsMap } from './components/OperationsMap'
import { DeliveriesView } from './components/DeliveriesView'
import { FleetView } from './components/FleetView'
import { FieldOperationsView } from './components/FieldOperationsView'
import { IncidentReviewView } from './components/IncidentReviewView'
import { AnalyticsView } from './components/AnalyticsView'
import { AlertsView } from './components/AlertsView'
import { AdministrationView } from './components/AdministrationView'
import { PortalHome } from './components/PortalHome'
import { AccessibilityBar } from './components/PortalIdentity'
import { RoutePlannerPanel } from './components/RoutePlannerPanel'
import { DriverJourneyView, type DemoLocation } from './components/DriverJourneyView'
import { api } from './services/api'
import { loadQueuedReports, queueReport, saveQueuedReports, type QueuedFieldReport } from './services/offlineReports'
import { connectOperationsStream, type OperationsEvent, type StreamStatus } from './services/realtime'
import type { AuthUser, FieldIncidentReportRequest, RoadSegment, RouteCandidate, RouteLocation, RoutePreference, UserRole, VehicleRegistrationRequest } from './types/api'

const allReadRoles: UserRole[] = ['CONTROL_ROOM_ADMIN', 'LOGISTICS_OPERATOR', 'DISTRICT_AUTHORITY', 'VIEWER']
const navItems = [
  { label: 'Journey', icon: Navigation, roles: ['DRIVER'] as UserRole[] },
  { label: 'Overview', icon: CircleGauge, roles: allReadRoles },
  { label: 'Live map', icon: Map, roles: allReadRoles },
  { label: 'Route planner', icon: Route, roles: ['CONTROL_ROOM_ADMIN', 'LOGISTICS_OPERATOR', 'DISTRICT_AUTHORITY'] as UserRole[] },
  { label: 'Deliveries', icon: Boxes, roles: ['CONTROL_ROOM_ADMIN', 'LOGISTICS_OPERATOR'] as UserRole[] },
  { label: 'Fleet', icon: Truck, roles: ['CONTROL_ROOM_ADMIN', 'LOGISTICS_OPERATOR'] as UserRole[] },
  { label: 'Field reports', icon: ShieldAlert, roles: ['CONTROL_ROOM_ADMIN', 'FIELD_OFFICER'] as UserRole[] },
  { label: 'Incident review', icon: ShieldAlert, roles: ['CONTROL_ROOM_ADMIN', 'DISTRICT_AUTHORITY'] as UserRole[] },
  { label: 'Analytics', icon: Activity, roles: allReadRoles },
  { label: 'Alerts', icon: Bell, roles: ['CONTROL_ROOM_ADMIN', 'FIELD_OFFICER', 'LOGISTICS_OPERATOR', 'DISTRICT_AUTHORITY', 'VIEWER'] as UserRole[] },
  { label: 'Administration', icon: Users, roles: ['CONTROL_ROOM_ADMIN'] as UserRole[] },
]

const featureDescriptions: Record<string, string> = {
  Journey: 'Route instructions, GPS sharing and handover',
  Overview: 'Live operating picture and critical priorities',
  'Live map': 'Road access, incidents, assets and vehicles',
  'Route planner': 'Compare risk-aware road options',
  Deliveries: 'Dispatch, assignment and delivery progress',
  Fleet: 'Vehicle availability and telemetry health',
  'Field reports': 'Capture verified on-ground conditions',
  'Incident review': 'Review evidence and confirm decisions',
  Analytics: 'Network performance and data confidence',
  Alerts: 'Operational notifications and acknowledgements',
  Administration: 'Users, data sources and audit controls',
}

const metricCards = [
  { key: 'active_vehicles', label: 'Active vehicles', icon: Truck, tone: 'mint' },
  { key: 'critical_deliveries', label: 'Critical deliveries', icon: PackageCheck, tone: 'blue' },
  { key: 'blocked_segments', label: 'Blocked segments', icon: ShieldAlert, tone: 'red' },
  { key: 'high_risk_segments', label: 'High-risk segments', icon: AlertTriangle, tone: 'orange' },
  { key: 'delayed_deliveries', label: 'Delayed deliveries', icon: Activity, tone: 'amber' },
]

type Language = 'en' | 'hi'
type AppSection = 'Overview' | 'Journey' | 'Deliveries' | 'Fleet' | 'Field reports' | 'Incident review' | 'Analytics' | 'Alerts' | 'Administration'

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed'; platform: string }>
}

const copy = {
  en: { greeting: 'Good evening, Control Room', subtitle: 'Live accessibility and essential-supply movement across North Eastern India.', reset: 'Reset demo', report: 'Report field incident', route: 'Plan emergency route', map: 'Operational map', alerts: 'Needs attention', connectivity: 'Connectivity', deliveries: 'Essential deliveries', activeAlerts: 'ACTIVE ALERTS', acknowledge: 'Acknowledge' },
  hi: { greeting: 'नमस्ते, नियंत्रण कक्ष', subtitle: 'पायलट कॉरिडोर में सड़क पहुंच और आवश्यक आपूर्ति की लाइव स्थिति।', reset: 'डेमो रीसेट करें', report: 'फील्ड घटना दर्ज करें', route: 'आपातकालीन मार्ग बनाएं', map: 'संचालन मानचित्र', alerts: 'ध्यान आवश्यक', connectivity: 'कनेक्टिविटी', deliveries: 'आवश्यक डिलीवरी', activeAlerts: 'सक्रिय अलर्ट', acknowledge: 'स्वीकार करें' },
} as const

function localizedAlert(title: string, message: string, language: Language) {
  if (language === 'en') return { title, message }
  const translated: Record<string, { title: string; message: string }> = {
    'Rainfall risk increasing': { title: 'बारिश का जोखिम बढ़ रहा है', message: 'भालुकपोंग के पास NH 13 सावधानी स्थिति में है। आने वाली फील्ड रिपोर्ट पर नज़र रखें।' },
    'Field report awaiting verification': { title: 'फील्ड रिपोर्ट सत्यापन की प्रतीक्षा में', message: 'रिपोर्ट दर्ज हो गई है। सत्यापन तक सड़क की आधिकारिक पहुंच स्थिति नहीं बदलेगी।' },
    'Field report confirmed': { title: 'फील्ड रिपोर्ट की पुष्टि हुई', message: 'नियंत्रण कक्ष ने रिपोर्ट सत्यापित कर दी है और सड़क की स्थिति अपडेट कर दी गई है।' },
    'Field report downgraded': { title: 'फील्ड रिपोर्ट का जोखिम घटाया गया', message: 'समीक्षा के बाद सड़क को सावधानी स्थिति में रखा गया है।' },
    'Field report rejected': { title: 'फील्ड रिपोर्ट अस्वीकृत', message: 'नियंत्रण कक्ष ने इस रिपोर्ट को अस्वीकार कर दिया है।' },
    'Medicine delivery rerouted': { title: 'दवा डिलीवरी का मार्ग बदला गया', message: 'आवश्यक दवा की डिलीवरी के लिए वैकल्पिक मार्ग चुना गया है।' },
  }
  return translated[title] ?? { title, message }
}

function timeLabel(value: string) {
  return new Intl.DateTimeFormat('en-IN', { hour: '2-digit', minute: '2-digit' }).format(new Date(value))
}

function App() {
  const [homeOpen, setHomeOpen] = useState(false)
  const queryClient = useQueryClient()
  const [selectedRoadId, setSelectedRoadId] = useState<string | null>(null)
  const [activeSection, setActiveSection] = useState<AppSection>('Overview')
  const [featureMenuOpen, setFeatureMenuOpen] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [plannerOpen, setPlannerOpen] = useState(false)
  const [preference, setPreference] = useState<RoutePreference>('SAFETY_FIRST')
  const [selectedRoute, setSelectedRoute] = useState<RouteCandidate | null>(null)
  const [disruptionSummary, setDisruptionSummary] = useState<Awaited<ReturnType<typeof api.simulateHeavyRain>>['disruption_summary']>(null)
  const [deliveryImpacts, setDeliveryImpacts] = useState<Awaited<ReturnType<typeof api.simulateHeavyRain>>['delivery_impacts']>([])
  const [reportOpen, setReportOpen] = useState(false)
  const [fieldReport, setFieldReport] = useState<FieldIncidentReportRequest>({
    incident_type: 'LANDSLIDE', severity: 'WARNING', reported_accessibility: 'CAUTION',
    matched_segment_id: null, description: '', reporter_name: 'Field officer',
  })
  const [isOnline, setIsOnline] = useState(() => navigator.onLine)
  const [queuedReports, setQueuedReports] = useState<QueuedFieldReport[]>([])
  const [syncingReports, setSyncingReports] = useState(false)
  const [fieldReportNotice, setFieldReportNotice] = useState<string | null>(null)
  const [weatherNotice, setWeatherNotice] = useState<{ status: 'LIVE' | 'CACHED'; message: string } | null>(null)
  const [fleetNotice, setFleetNotice] = useState<string | null>(null)
  const [language, setLanguage] = useState<Language>(() => window.localStorage.getItem('ner-logistics-language') === 'hi' ? 'hi' : 'en')
  const [authUser, setAuthUser] = useState<AuthUser | null>(api.storedUser)
  const [authChecked, setAuthChecked] = useState(false)
  const [streamStatus, setStreamStatus] = useState<StreamStatus>('DISCONNECTED')
  const [realtimeNotice, setRealtimeNotice] = useState<string | null>(null)
  const [installPrompt, setInstallPrompt] = useState<BeforeInstallPromptEvent | null>(null)
  const text = copy[language]

  const isDriver = authUser?.role === 'DRIVER'
  const overviewQuery = useQuery({ queryKey: ['overview'], queryFn: api.overview, enabled: Boolean(authUser) && !isDriver, networkMode: 'always', refetchInterval: isOnline ? 15000 : false })
  const mapQuery = useQuery({ queryKey: ['map-snapshot'], queryFn: api.mapSnapshot, enabled: Boolean(authUser) && !isDriver, networkMode: 'always', refetchInterval: isOnline ? 10000 : false })
  const driverJourneyQuery = useQuery({ queryKey: ['driver-journey'], queryFn: api.driverJourney, enabled: Boolean(authUser) && isDriver, networkMode: 'always', refetchInterval: isOnline ? 10000 : false })
  const analyticsQuery = useQuery({ queryKey: ['analytics'], queryFn: api.analytics, enabled: Boolean(authUser) && activeSection === 'Analytics', refetchInterval: 30000 })
  const alertsQuery = useQuery({ queryKey: ['alerts', language], queryFn: () => api.alerts(language), enabled: Boolean(authUser) && activeSection === 'Alerts', refetchInterval: 15000 })
  const administrationQuery = useQuery({ queryKey: ['administration'], queryFn: api.administration, enabled: authUser?.role === 'CONTROL_ROOM_ADMIN' && activeSection === 'Administration', refetchInterval: 30000 })

  useEffect(() => { window.localStorage.setItem('ner-logistics-language', language) }, [language])

  useEffect(() => {
    loadQueuedReports()
      .then(setQueuedReports)
      .catch(() => setFieldReportNotice('Offline storage is unavailable in this browser.'))
  }, [])

  useEffect(() => {
    if (!authUser) return
    setPlannerOpen(false)
    setActiveSection(authUser.role === 'DRIVER' ? 'Journey' : authUser.role === 'FIELD_OFFICER' ? 'Field reports' : authUser.role === 'DISTRICT_AUTHORITY' ? 'Incident review' : 'Overview')
  }, [authUser?.id])

  useEffect(() => {
    if (!authUser) return
    const eventMessages: Partial<Record<OperationsEvent['type'], string>> = {
      FIELD_REPORT_SUBMITTED: 'New field report received in real time.',
      FIELD_REPORT_REVIEWED: 'A field report verification decision was received.',
      GPS_POSITION_RECEIVED: 'Live vehicle GPS position updated.',
      VEHICLE_REGISTERED: 'A new GPS vehicle was registered.',
      DELIVERY_DISPATCHED: 'A new risk-assessed delivery was dispatched.',
      DELIVERY_VEHICLE_ASSIGNED: 'A GPS vehicle was assigned to a delivery.',
      WEATHER_REFRESHED: 'Operational weather observations were refreshed.',
    }
    return connectOperationsStream((event) => {
      if (event.type === 'CONNECTED') return
      void queryClient.invalidateQueries({ queryKey: ['map-snapshot'] })
      void queryClient.invalidateQueries({ queryKey: ['overview'] })
      void queryClient.invalidateQueries({ queryKey: ['analytics'] })
      void queryClient.invalidateQueries({ queryKey: ['alerts'] })
      void queryClient.invalidateQueries({ queryKey: ['administration'] })
      void queryClient.invalidateQueries({ queryKey: ['driver-journey'] })
      setRealtimeNotice(eventMessages[event.type] ?? 'Operational data updated.')
    }, setStreamStatus)
  }, [authUser?.id, queryClient])

  const updateData = (payload: Awaited<ReturnType<typeof api.simulateHeavyRain>>) => {
    queryClient.setQueryData(['overview'], payload.overview)
    queryClient.setQueryData(['map-snapshot'], payload.map_snapshot)
    setDisruptionSummary(payload.disruption_summary ?? null)
    setDeliveryImpacts(payload.delivery_impacts ?? [])
  }

  const rainMutation = useMutation({ mutationFn: api.simulateHeavyRain, onSuccess: updateData })
  const weatherMutation = useMutation({
    mutationFn: api.refreshWeather,
    onSuccess: (payload) => {
      queryClient.setQueryData(['overview'], payload.overview)
      queryClient.setQueryData(['map-snapshot'], payload.map_snapshot)
      setWeatherNotice({ status: payload.status, message: payload.message })
    },
    onError: () => setWeatherNotice({ status: 'CACHED', message: 'Weather refresh failed. The last persisted forecast remains in use.' }),
  })
  const queueFieldReport = (report: FieldIncidentReportRequest, message: string) => {
    const queued = queueReport(report)
    setQueuedReports((current) => {
      const updated = [...current, queued]
      void saveQueuedReports(updated).catch(() => setFieldReportNotice('The report could not be written to offline storage.'))
      return updated
    })
    setReportOpen(false)
    setFieldReport((current) => ({ ...current, description: '' }))
    setFieldReportNotice(message)
  }

  const fieldReportMutation = useMutation({
    mutationFn: api.submitFieldReport,
    onSuccess: (payload) => {
      updateData(payload)
      setReportOpen(false)
      setFieldReport((current) => ({ ...current, description: '' }))
      setFieldReportNotice('Field report submitted for control-room verification.')
    },
    onError: (_error, report) => queueFieldReport(report, 'Connection interrupted. Report saved offline and will sync automatically.'),
  })
  const verificationMutation = useMutation({
    mutationFn: ({ incidentId, decision }: { incidentId: string; decision: 'CONFIRM' | 'DOWNGRADE' | 'REJECT' }) =>
      api.verifyFieldReport(incidentId, { decision }),
    onSuccess: updateData,
  })
  const acknowledgementMutation = useMutation({
    mutationFn: api.acknowledgeAlert,
    onSuccess: (payload) => { updateData(payload); void queryClient.invalidateQueries({ queryKey: ['alerts'] }) },
  })
  const resetMutation = useMutation({
    mutationFn: api.resetSimulation,
    onSuccess: (payload) => {
      updateData(payload)
      setSelectedRoute(null)
      setDeliveryImpacts([])
    },
  })
  const landslideMutation = useMutation({
    mutationFn: () => api.simulationEvent('confirmed-landslide'),
    onSuccess: updateData,
  })
  const routeMutation = useMutation({
    mutationFn: api.planRoute,
    onSuccess: (result) => {
      const route = result.routes.find((item) => item.id === result.recommended_route_id) ?? result.routes[0] ?? null
      setSelectedRoute(route)
      if (route) window.setTimeout(() => document.getElementById('operational-map')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 0)
    },
  })
  const dispatchMutation = useMutation({
    mutationFn: api.createDelivery,
    onSuccess: (payload) => {
      queryClient.setQueryData(['overview'], payload.overview)
      queryClient.setQueryData(['map-snapshot'], payload.map_snapshot)
      setPlannerOpen(false)
      setActiveSection('Deliveries')
      setRealtimeNotice(`${payload.delivery.id} created on the selected risk-assessed route${payload.delivery.vehicle_id === 'UNASSIGNED' ? '; assign a GPS vehicle before departure.' : ' and assigned to a live GPS vehicle.'}`)
    },
  })
  const deliveryAssignmentMutation = useMutation({
    mutationFn: ({ deliveryId, vehicleId }: { deliveryId: string; vehicleId: string }) => api.assignDeliveryVehicle(deliveryId, vehicleId),
    onSuccess: (payload) => {
      queryClient.setQueryData(['overview'], payload.overview)
      queryClient.setQueryData(['map-snapshot'], payload.map_snapshot)
      setRealtimeNotice(`${payload.delivery.id} assigned to its live GPS vehicle and ready for tracking.`)
    },
  })

  const gpsMutation = useMutation({
    mutationFn: ({ vehicleId, position }: { vehicleId: string; position: GeolocationPosition }) => api.ingestVehiclePosition(vehicleId, {
      latitude: position.coords.latitude,
      longitude: position.coords.longitude,
      speed_kph: position.coords.speed === null ? 0 : Math.max(0, position.coords.speed * 3.6),
      heading: position.coords.heading === null ? 0 : ((position.coords.heading % 360) + 360) % 360,
      accuracy_m: position.coords.accuracy,
      recorded_at: new Date(position.timestamp).toISOString(),
      source: 'BROWSER_GPS',
    }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['map-snapshot'] })
      void queryClient.invalidateQueries({ queryKey: ['overview'] })
      void queryClient.invalidateQueries({ queryKey: ['driver-journey'] })
      setFleetNotice('Live GPS position accepted and shown on the operational map.')
    },
    onError: () => setFleetNotice('GPS position was not accepted. Check that the device is inside the NER boundary.'),
  })

  const demoGpsMutation = useMutation({
    mutationFn: ({ vehicleId, longitude, latitude }: { vehicleId: string; longitude: number; latitude: number }) => api.ingestVehiclePosition(vehicleId, {
      latitude, longitude, speed_kph: 28, heading: 0, accuracy_m: 15,
      recorded_at: new Date().toISOString(), source: 'DEMO_GPS_OVERRIDE',
    }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['driver-journey'] })
      void queryClient.invalidateQueries({ queryKey: ['map-snapshot'] })
      void queryClient.invalidateQueries({ queryKey: ['overview'] })
      setFleetNotice('Demo GPS advanced along the assigned route. This position remains marked simulated.')
    },
    onError: (error) => setFleetNotice(error instanceof Error ? error.message : 'The demo GPS position could not be advanced.'),
  })

  const registerVehicleMutation = useMutation({
    mutationFn: api.registerVehicle,
    onSuccess: (payload) => {
      void queryClient.invalidateQueries({ queryKey: ['map-snapshot'] })
      void queryClient.invalidateQueries({ queryKey: ['overview'] })
      void queryClient.invalidateQueries({ queryKey: ['driver-journey'] })
      setFleetNotice(payload.vehicle.data_mode === 'LIVE' ? 'Vehicle registered from the device\'s real GPS position.' : 'Vehicle registered with an explicitly simulated NER demo position.')
    },
    onError: () => setFleetNotice('Vehicle registration failed. Check the registration, assignment and GPS position.'),
  })

  const driverActionMutation = useMutation({
    mutationFn: api.driverJourneyAction,
    onSuccess: (payload) => {
      queryClient.setQueryData(['driver-journey'], payload)
      for (const key of ['driver-journey', 'overview', 'map-snapshot', 'analytics']) {
        void queryClient.invalidateQueries({ queryKey: [key] })
      }
      setFleetNotice(payload.message)
    },
    onError: (error) => setFleetNotice(error instanceof Error ? error.message : 'The journey action could not be completed.'),
  })

  const readBrowserGps = (onSuccess: (position: GeolocationPosition) => void) => {
    if (!navigator.geolocation) {
      setFleetNotice('This browser does not provide geolocation. Connect the vehicle through the GPS ingestion API.')
      return
    }
    setFleetNotice('Waiting for this device to provide an accurate GPS position...')
    navigator.geolocation.getCurrentPosition(onSuccess, () => setFleetNotice('GPS permission was denied or the position is unavailable.'), {
      enableHighAccuracy: true, timeout: 15000, maximumAge: 5000,
    })
  }

  const registerVehicleFromGps = (draft: Pick<VehicleRegistrationRequest, 'registration' | 'vehicle_class'> & Partial<Pick<VehicleRegistrationRequest, 'active_delivery_id'>>) => {
    readBrowserGps((position) => registerVehicleMutation.mutate({
      ...draft,
      active_delivery_id: draft.active_delivery_id ?? null,
      latitude: position.coords.latitude,
      longitude: position.coords.longitude,
      accuracy_m: position.coords.accuracy,
      recorded_at: new Date(position.timestamp).toISOString(),
      source: 'BROWSER_GPS_REGISTRATION',
    }))
  }

  const registerVehicleAtDemoLocation = (draft: Pick<VehicleRegistrationRequest, 'registration' | 'vehicle_class'>, location: DemoLocation) => registerVehicleMutation.mutate({
    ...draft, active_delivery_id: null, latitude: location.latitude, longitude: location.longitude,
    accuracy_m: 15, recorded_at: new Date().toISOString(), source: `DEMO_GPS_OVERRIDE:${location.label}`,
  })

  const advanceDemoVehicle = (vehicleId: string) => {
    const journey = driverJourneyQuery.data
    const coordinates = journey?.delivery?.route_geometry?.coordinates
    const vehicle = journey?.vehicle
    if (!vehicle) return
    const nextProgress = Math.min(95, (journey?.delivery?.progress_percent ?? 0) + 15)
    const coordinate = coordinates?.[Math.min(coordinates.length - 1, Math.round((coordinates.length - 1) * nextProgress / 100))] ?? [vehicle.longitude, vehicle.latitude]
    demoGpsMutation.mutate({ vehicleId, longitude: coordinate[0], latitude: coordinate[1] })
  }

  const shareVehicleGps = (vehicleId: string) => readBrowserGps((position) => gpsMutation.mutate({ vehicleId, position }))

  const openPlanner = () => {
    setActiveSection('Overview')
    setSelectedRoute(null)
    routeMutation.reset()
    setPlannerOpen(true)
  }

  const calculateRoute = (source: RouteLocation, destination: RouteLocation) => routeMutation.mutate({
    source_location: source, destination_location: destination, cargo_type: 'EMERGENCY_MEDICINES',
    priority: 'CRITICAL', vehicle_class: 'REFRIGERATED_TRUCK', preference,
  })

  const openFieldReport = () => {
    setPlannerOpen(false)
    setActiveSection('Field reports')
  }

  const captureFieldReportGps = () => {
    if (!navigator.geolocation) {
      setFieldReportNotice('GPS is not available in this browser. Enter coordinates manually.')
      return
    }
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        if (coords.latitude < 21 || coords.latitude > 30.5 || coords.longitude < 87.5 || coords.longitude > 98.5) {
          setFieldReportNotice('Current GPS position is outside the NER operating boundary.')
          return
        }
        setFieldReport((current) => ({ ...current, latitude: coords.latitude, longitude: coords.longitude }))
        setFieldReportNotice(`GPS location captured (±${Math.round(coords.accuracy)} m).`)
      },
      () => setFieldReportNotice('GPS permission was denied. Enter coordinates manually.'),
      { enableHighAccuracy: true, timeout: 12000, maximumAge: 30000 },
    )
  }

  const syncQueuedReports = useCallback(async () => {
    if (!navigator.onLine || syncingReports || queuedReports.length === 0) return
    setSyncingReports(true)
    let remaining = [...queuedReports]
    try {
      for (const queued of queuedReports) {
        const payload = await api.submitFieldReport(queued.report)
        updateData(payload)
        remaining = remaining.filter((item) => item.id !== queued.id)
      }
      setFieldReportNotice('Offline field reports synchronized for review.')
    } catch {
      setFieldReportNotice('Some offline reports could not sync yet. They remain safely queued.')
    } finally {
      await saveQueuedReports(remaining)
      setQueuedReports(remaining)
      setSyncingReports(false)
    }
  }, [queuedReports, syncingReports])

  useEffect(() => {
    const online = () => setIsOnline(true)
    const offline = () => setIsOnline(false)
    window.addEventListener('online', online)
    window.addEventListener('offline', offline)
    return () => { window.removeEventListener('online', online); window.removeEventListener('offline', offline) }
  }, [])

  useEffect(() => {
    const beforeInstall = (event: Event) => {
      event.preventDefault()
      setInstallPrompt(event as BeforeInstallPromptEvent)
    }
    const installed = () => setInstallPrompt(null)
    window.addEventListener('beforeinstallprompt', beforeInstall)
    window.addEventListener('appinstalled', installed)
    return () => {
      window.removeEventListener('beforeinstallprompt', beforeInstall)
      window.removeEventListener('appinstalled', installed)
    }
  }, [])

  useEffect(() => { if (isOnline && queuedReports.length > 0) void syncQueuedReports() }, [isOnline, queuedReports.length, syncQueuedReports])

  useEffect(() => {
    if (!api.hasSession()) {
      setAuthUser(null)
      setAuthChecked(true)
      return
    }
    api.me().then(setAuthUser).catch(() => {
      const stored = api.storedUser()
      if (!navigator.onLine && stored) setAuthUser(stored)
      else { api.clearSession(); setAuthUser(null) }
    }).finally(() => setAuthChecked(true))
  }, [])

  const selectedRoad: RoadSegment | undefined = useMemo(
    () => mapQuery.data?.road_segments.find((road) => road.id === selectedRoadId),
    [mapQuery.data, selectedRoadId],
  )
  const unverifiedReports = useMemo(
    () => mapQuery.data?.incidents.filter((incident) => incident.verification === 'UNVERIFIED' && (authUser?.role !== 'DISTRICT_AUTHORITY' || String(incident.context_snapshot.district ?? '').toLowerCase() === authUser.district?.toLowerCase())) ?? [],
    [mapQuery.data, authUser],
  )

  const loading = isDriver ? driverJourneyQuery.isLoading : overviewQuery.isLoading || mapQuery.isLoading
  const failed = isDriver ? driverJourneyQuery.isError : overviewQuery.isError || mapQuery.isError

  if (!authChecked) return <div className="session-loading">Validating secure session…</div>
  if (!authUser || homeOpen) return <PortalHome onAuthenticated={(user) => { setAuthUser(user); setHomeOpen(false) }} onWorkspace={authUser ? () => setHomeOpen(false) : undefined} />

  const isAdmin = authUser.role === 'CONTROL_ROOM_ADMIN'
  const canReport = isAdmin || authUser.role === 'FIELD_OFFICER'
  const canRoute = isAdmin || authUser.role === 'LOGISTICS_OPERATOR' || authUser.role === 'DISTRICT_AUTHORITY'
  const canVerify = isAdmin || authUser.role === 'DISTRICT_AUTHORITY'
  const canAcknowledge = isAdmin || authUser.role === 'LOGISTICS_OPERATOR' || authUser.role === 'DISTRICT_AUTHORITY'
  const canRefreshWeather = isAdmin || authUser.role === 'DISTRICT_AUTHORITY'
  const hasLiveWeather = mapQuery.data?.road_segments.some((road) => road.data_mode === 'LIVE') ?? false
  const hasLiveGps = (mapQuery.data?.vehicles.some((vehicle) => vehicle.data_mode === 'LIVE') ?? false) || driverJourneyQuery.data?.vehicle?.data_mode === 'LIVE'
  const driverVehicleMode = driverJourneyQuery.data?.vehicle?.data_mode ?? null
  const liveModeLabel = hasLiveWeather && hasLiveGps ? 'LIVE FEEDS' : hasLiveWeather ? 'LIVE WEATHER' : hasLiveGps ? 'LIVE GPS' : 'SIMULATED'
  const heading = activeSection === 'Journey'
    ? { eyebrow: 'DRIVER OPERATIONS', title: 'Assigned journey', subtitle: 'Share live GPS, follow risk-aware route instructions and keep the control room informed.' }
    : activeSection === 'Deliveries'
    ? { eyebrow: 'LOGISTICS OPERATIONS', title: 'Essential deliveries', subtitle: 'Track priority cargo, assignments, ETA changes and completion across the active corridor.' }
    : activeSection === 'Fleet'
      ? { eyebrow: 'FLEET TELEMETRY', title: 'Vehicle operations', subtitle: 'Monitor live and simulated positions, GPS freshness, assignments and telemetry provenance.' }
      : activeSection === 'Field reports'
        ? { eyebrow: 'FIELD OPERATIONS', title: 'Report accessibility incident', subtitle: 'Select any NER location and combine field evidence with weather, terrain, infrastructure and ML context.' }
        : activeSection === 'Incident review'
          ? { eyebrow: 'DISTRICT AUTHORITY', title: 'Incident verification queue', subtitle: 'Review field evidence and apply authoritative accessibility decisions without treating ML output as confirmed fact.' }
          : activeSection === 'Analytics'
            ? { eyebrow: 'OPERATIONAL INTELLIGENCE', title: 'NER logistics analytics', subtitle: 'Connectivity, disruption, delivery and data-confidence indicators calculated from the shared operational state.' }
            : activeSection === 'Alerts'
              ? { eyebrow: 'REAL-TIME NOTIFICATIONS', title: 'Operational alert inbox', subtitle: 'Review and acknowledge multilingual weather, incident, routing and GPS notifications.' }
              : activeSection === 'Administration'
                ? { eyebrow: 'PLATFORM GOVERNANCE', title: 'System administration', subtitle: 'Inspect role assignments, integrations, secure persistence, spatial capability, ML status and audit history.' }
      : { eyebrow: 'OPERATIONS OVERVIEW', title: text.greeting, subtitle: text.subtitle }

  const workspaceLabel = authUser.role === 'DRIVER' ? 'DRIVER OPERATIONS' : authUser.role === 'FIELD_OFFICER' ? 'FIELD OPERATIONS' : authUser.role === 'DISTRICT_AUTHORITY' ? 'DISTRICT AUTHORITY' : authUser.role === 'LOGISTICS_OPERATOR' ? 'LOGISTICS CONTROL' : authUser.role === 'VIEWER' ? 'READ-ONLY MONITORING' : 'COMMAND CENTRE'
  const visibleNavItems = navItems.filter((item) => item.roles.includes(authUser.role))
  const featureGroups = [
    { label: 'Command', items: ['Overview', 'Live map', 'Route planner'] },
    { label: 'Operations', items: ['Journey', 'Deliveries', 'Fleet'] },
    { label: 'Field intelligence', items: ['Field reports', 'Incident review'] },
    { label: 'Platform', items: ['Analytics', 'Alerts', 'Administration'] },
  ]

  const showOperationalMap = () => {
    setActiveSection('Overview')
    window.setTimeout(() => document.getElementById('operational-map')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 0)
  }

  const returnToDashboard = () => {
    setPlannerOpen(false)
    setActiveSection('Overview')
    window.setTimeout(() => document.getElementById('workspace-content')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 0)
  }

  const navigate = (label: string) => {
    setFeatureMenuOpen(false)
    setSidebarOpen(false)
    if (label === 'Route planner') { if (canRoute) openPlanner(); return }
    setPlannerOpen(false)
    if (label === 'Journey' || label === 'Deliveries' || label === 'Fleet' || label === 'Analytics' || label === 'Alerts' || label === 'Administration') { setActiveSection(label); return }
    if (label === 'Field reports') { if (canReport) setActiveSection('Field reports'); return }
    if (label === 'Incident review') { if (canVerify) setActiveSection('Incident review'); return }
    if (label === 'Live map') { showOperationalMap(); return }
    if (label === 'Overview') setActiveSection('Overview')
  }

  const logout = () => {
    api.clearSession()
    setAuthUser(null)
    queryClient.clear()
  }

  const installFieldApp = async () => {
    if (!installPrompt) return
    await installPrompt.prompt()
    await installPrompt.userChoice
    setInstallPrompt(null)
  }

  return (
    <div className="app-shell platform-shell">
      {sidebarOpen && <button className="sidebar-backdrop" aria-label="Close navigation" onClick={() => setSidebarOpen(false)} />}
      <aside className={`sidebar ${sidebarOpen ? 'sidebar-open' : ''}`} id="workspace-navigation">
        <button className="sidebar-close" aria-label="Close workspace navigation" onClick={() => setSidebarOpen(false)}>Close ×</button>
        <div className="brand">
          <button className="workspace-brand" onClick={() => setHomeOpen(true)} aria-label="NERRO home"><img src="/icons/nerro.PNG" alt="NERRO"/><span>North East intelligence</span></button>
        </div>
        <nav>
          <p className="nav-label">{workspaceLabel}</p>
          {navItems.filter((item) => item.roles.includes(authUser.role)).map(({ label, icon: Icon }) => {
            const active = label === 'Route planner' ? plannerOpen : label === activeSection && !plannerOpen
            return <button aria-current={active ? 'page' : undefined} className={`nav-item ${active ? 'active' : ''}`} key={label} onClick={() => navigate(label)}>
              <Icon size={18} /><span>{label}</span>{active && <span className="active-dot" />}
            </button>
          })}
        </nav>
        <div className="sidebar-foot">
          <div className="network-card"><Radio size={16} /><div><strong>{authUser.role === 'DRIVER' ? driverVehicleMode === 'LIVE' ? 'Vehicle GPS connected' : driverVehicleMode === 'SIMULATED' ? 'Demo GPS active' : 'Waiting for GPS registration' : authUser.role === 'FIELD_OFFICER' ? isOnline ? 'Reporting online' : 'Offline capture active' : streamStatus === 'CONNECTED' ? 'Real-time connected' : 'Reconnecting operations'}</strong><span>{authUser.role === 'DRIVER' ? `${driverVehicleMode === 'LIVE' ? 'live phone telemetry' : driverVehicleMode === 'SIMULATED' ? 'explicitly simulated telemetry' : 'no vehicle registered'} · ${streamStatus.toLowerCase()}` : authUser.role === 'FIELD_OFFICER' ? isOnline ? `${streamStatus.toLowerCase()} · live enrichment available` : `${queuedReports.length} report${queuedReports.length === 1 ? '' : 's'} queued` : `${liveModeLabel.toLowerCase()} · ${streamStatus.toLowerCase()}`}</span></div></div>
          <button className="profile" onClick={logout} title="Sign out"><div className="avatar"><Users size={18}/></div><div><strong>{authUser.role.replaceAll('_', ' ').toLowerCase()}</strong><span>Sign out of workspace</span></div><LogOut size={16} /></button>
        </div>
      </aside>

      <main>
        <AccessibilityBar target="workspace-content"/>
        <header className="topbar">
          <div className="platform-brand">
            <button className="brand-home" onClick={() => setHomeOpen(true)} aria-label="NERRO home"><img src="/icons/nerro.PNG" alt="NERRO" /></button>
            <div><strong>NERRO</strong><span>Operations intelligence</span></div>
          </div>
          <button className="mobile-menu" aria-label="Toggle workspace navigation" aria-expanded={sidebarOpen} onClick={() => setSidebarOpen(!sidebarOpen)}><Menu /></button>
          <div className="corridor"><MapPin size={16} /><span>{authUser.role === 'DRIVER' ? 'Assigned vehicle journey' : authUser.role === 'FIELD_OFFICER' ? 'NER field reporting workspace' : authUser.role === 'DISTRICT_AUTHORITY' ? `${authUser.district ?? 'NER'} authority workspace` : 'North Eastern Region operations'}</span><ChevronRight size={15} /></div>
          <div className="top-actions">
            <button className={`feature-trigger ${featureMenuOpen ? 'active' : ''}`} aria-expanded={featureMenuOpen} aria-controls="feature-launcher" onClick={() => setFeatureMenuOpen((open) => !open)}><LayoutGrid size={17} /> Features</button>
            <button className="language-toggle" onClick={() => setHomeOpen(true)}>Home</button>
            {authUser.role !== 'FIELD_OFFICER' && authUser.role !== 'DRIVER' && <label className="search"><Search size={17} /><input aria-label="Search" placeholder="Search vehicle, delivery or road" /></label>}
            {authUser.role === 'FIELD_OFFICER' && installPrompt && <button className="install-app" onClick={() => void installFieldApp()}><Download size={15} /> Install app</button>}
            <button className="language-toggle" onClick={() => setLanguage(language === 'en' ? 'hi' : 'en')} title="Change language">{language === 'en' ? 'हिंदी' : 'EN'}</button>
            <span className={`mode-badge ${authUser.role === 'FIELD_OFFICER' || authUser.role === 'DRIVER' ? isOnline ? 'live' : '' : hasLiveWeather || hasLiveGps ? 'live' : ''}`}><span /> {authUser.role === 'FIELD_OFFICER' || authUser.role === 'DRIVER' ? isOnline ? 'ONLINE' : 'OFFLINE' : liveModeLabel}</span>
            {authUser.role !== 'FIELD_OFFICER' && authUser.role !== 'DRIVER' && authUser.role !== 'VIEWER' && <button className="icon-button" aria-label="Open alerts" onClick={() => navigate('Alerts')}><Bell size={18} /><i /></button>}
            <button className="session-button" onClick={logout} title="Sign out"><div className="avatar"><Users size={16}/></div><span>{authUser.role.replaceAll('_', ' ').toLowerCase()}</span><LogOut size={15} /></button>
          </div>
        </header>

        {featureMenuOpen && <button className="feature-menu-scrim" aria-label="Close feature menu" onClick={() => setFeatureMenuOpen(false)} />}
        <section className={`feature-launcher ${featureMenuOpen ? 'open' : ''}`} id="feature-launcher" aria-label="Platform features">
          <div className="feature-launcher-head"><div><span>{workspaceLabel}</span><h2>Navigate your workspace</h2></div><p>Every tool available to your role, organized by workflow.</p></div>
          <div className="feature-groups">
            {featureGroups.map((group) => {
              const items = visibleNavItems.filter((item) => group.items.includes(item.label))
              if (!items.length) return null
              return <div className="feature-group" key={group.label}><p>{group.label}</p><div>{items.map(({ label, icon: Icon }) => {
                const active = label === 'Route planner' ? plannerOpen : label === activeSection && !plannerOpen
                return <button className={active ? 'active' : ''} key={label} onClick={() => navigate(label)}><Icon size={18} /><span><strong>{label}</strong><small>{featureDescriptions[label]}</small></span><ChevronRight size={15} /></button>
              })}</div></div>
            })}
          </div>
          <div className="feature-launcher-footer"><Radio size={15} /><span>{streamStatus === 'CONNECTED' ? 'Real-time operations stream connected' : 'Reconnecting to operations stream'}</span></div>
        </section>

        <div className="page" id="workspace-content" tabIndex={-1}>
          <section className="page-heading" key={`${activeSection}-${plannerOpen}`}>
            <div><p className="eyebrow">{heading.eyebrow}</p><h1>{heading.title}</h1><p>{heading.subtitle}</p></div>
            {activeSection === 'Overview' && <div className="heading-actions">
              {canRefreshWeather && <button className="secondary" onClick={() => weatherMutation.mutate()} disabled={weatherMutation.isPending}><CloudRain size={16} /> {weatherMutation.isPending ? 'Refreshing weather...' : 'Refresh live weather'}</button>}
              {isAdmin && <button className="secondary" onClick={() => resetMutation.mutate()} disabled={resetMutation.isPending}><RefreshCw size={16} /> {text.reset}</button>}
              {canReport && queuedReports.length > 0 && <button className="secondary" onClick={() => void syncQueuedReports()} disabled={!isOnline || syncingReports}><Radio size={16} />{syncingReports ? 'Syncing reports…' : `Sync ${queuedReports.length} offline report${queuedReports.length > 1 ? 's' : ''}`}</button>}
              {canReport && <button className="secondary" onClick={openFieldReport}><ShieldAlert size={16} /> {text.report}</button>}
              {canRoute && <button className="primary" onClick={openPlanner}><Route size={16} /> {text.route}</button>}
            </div>}
            {activeSection !== 'Overview' && visibleNavItems.some((item) => item.label === 'Overview') && <button className="dashboard-return" onClick={returnToDashboard}><ArrowLeft size={17} /> Back to dashboard</button>}
          </section>

          {authUser.role === 'FIELD_OFFICER' && !isOnline && <div className="offline-mode-banner"><Radio size={17} /><span><strong>Offline field mode</strong>The report form and last synchronized roads, facilities, and incidents remain available. New reports stay on this device and sync automatically after reconnection. Basemap tiles require connectivity.</span></div>}
          {failed && <div className="error-banner"><AlertTriangle size={18} /><span>{isOnline ? 'Operational services are unavailable. Check the backend service and retry.' : 'No synchronized operational snapshot is available on this device yet. Reconnect once to prepare offline field mode.'}</span></div>}
          {loading && <div className="loading-card">Loading operational picture…</div>}

          {weatherNotice && <div className={`weather-notice ${weatherNotice.status.toLowerCase()}`}><CloudRain size={17} /><span><strong>{weatherNotice.status === 'LIVE' ? 'Live weather received' : 'Cached weather in use'}</strong>{weatherNotice.message}</span><button onClick={() => setWeatherNotice(null)} aria-label="Dismiss weather notice">×</button></div>}
          {realtimeNotice && <div className="realtime-notice"><Radio size={16} /><span><strong>Real-time update</strong>{realtimeNotice}</span><button onClick={() => setRealtimeNotice(null)} aria-label="Dismiss real-time update">×</button></div>}

          {activeSection === 'Journey' && driverJourneyQuery.data && <DriverJourneyView
            journey={driverJourneyQuery.data}
            busy={gpsMutation.isPending || demoGpsMutation.isPending || registerVehicleMutation.isPending || driverActionMutation.isPending}
            notice={fleetNotice}
            onRegister={registerVehicleFromGps}
            onRegisterDemo={registerVehicleAtDemoLocation}
            onShareGps={shareVehicleGps}
            onAdvanceDemoGps={advanceDemoVehicle}
            onAction={(action, description) => driverActionMutation.mutate({ action, description, instruction_updated_at: driverJourneyQuery.data?.delivery?.instruction_updated_at })}
          />}

          {overviewQuery.data && mapQuery.data && activeSection === 'Overview' && (
            <>
              <section className="metrics-grid">
                {metricCards.map(({ key, label, icon: Icon, tone }) => (
                  <article className="metric-card" key={key}>
                    <div className={`metric-icon ${tone}`}><Icon size={19} /></div>
                    <div><span>{label}</span><strong>{overviewQuery.data.metrics[key] ?? 0}</strong></div>
                    <small>Current corridor</small>
                  </article>
                ))}
              </section>

              {plannerOpen && <RoutePlannerPanel
                isLoading={routeMutation.isPending}
                result={routeMutation.data}
                error={routeMutation.error}
                preference={preference}
                selectedRouteId={selectedRoute?.id ?? null}
                onPreference={setPreference}
                onPlan={calculateRoute}
                onSelectRoute={setSelectedRoute}
                vehicles={mapQuery.data.vehicles}
                canDispatch={isAdmin || authUser.role === 'LOGISTICS_OPERATOR'}
                isDispatching={dispatchMutation.isPending}
                dispatchError={dispatchMutation.error}
                onDispatch={(request) => dispatchMutation.mutate(request)}
                onClose={() => { setPlannerOpen(false); setSelectedRoute(null); routeMutation.reset() }}
              />}

              {reportOpen && <section className="field-report-panel" aria-label="Field incident report">
                <div className="field-report-head"><div><p className="eyebrow">FIELD REPORTING</p><h2>Submit geo-tagged incident</h2><p>{isOnline ? 'Reports remain unverified until a control-room officer confirms them.' : 'Offline mode: this report will be stored securely in this browser and synced later.'}</p></div><button className="planner-close" onClick={() => setReportOpen(false)} aria-label="Close report form">×</button></div>
                <div className="field-report-grid">
                  <label>Incident type<select value={fieldReport.incident_type} onChange={(event) => setFieldReport({ ...fieldReport, incident_type: event.target.value })}><option>LANDSLIDE</option><option>FLOODING</option><option>ROAD_DAMAGE</option><option>TRAFFIC_CONGESTION</option></select></label>
                  <label>Severity<select value={fieldReport.severity} onChange={(event) => setFieldReport({ ...fieldReport, severity: event.target.value as FieldIncidentReportRequest['severity'] })}><option value="INFO">Info</option><option value="WARNING">Warning</option><option value="CRITICAL">Critical</option></select></label>
                  <label>Monitored road (optional)<select value={fieldReport.matched_segment_id ?? ''} onChange={(event) => setFieldReport({ ...fieldReport, matched_segment_id: event.target.value || null })}><option value="">GPS/manual location only</option>{mapQuery.data.road_segments.map((road) => <option key={road.id} value={road.id}>{road.id} · {road.road_name}</option>)}</select></label>
                  <label>Reported access<select value={fieldReport.reported_accessibility} onChange={(event) => setFieldReport({ ...fieldReport, reported_accessibility: event.target.value as FieldIncidentReportRequest['reported_accessibility'] })}><option value="CAUTION">Caution</option><option value="HIGH_RISK">High risk</option><option value="PARTIAL">Partial access</option><option value="BLOCKED">Blocked (requires verification)</option></select></label>
                  <label>Latitude<input type="number" min="21" max="30.5" step="0.000001" value={fieldReport.latitude ?? ''} onChange={(event) => setFieldReport({ ...fieldReport, latitude: event.target.value ? Number(event.target.value) : undefined })} placeholder="e.g. 25.5788" /></label>
                  <label>Longitude<input type="number" min="87.5" max="98.5" step="0.000001" value={fieldReport.longitude ?? ''} onChange={(event) => setFieldReport({ ...fieldReport, longitude: event.target.value ? Number(event.target.value) : undefined })} placeholder="e.g. 91.8933" /></label>
                  <label className="field-report-description">Description<textarea value={fieldReport.description} minLength={10} onChange={(event) => setFieldReport({ ...fieldReport, description: event.target.value })} placeholder="Describe the on-ground situation, impact and nearby landmark." /></label>
                </div>
                <div className="field-report-actions"><button className="secondary" type="button" onClick={captureFieldReportGps}><MapPin size={16} /> Use current GPS</button><small>Provide GPS/manual coordinates or link a monitored road. Reports remain unverified until reviewed.</small><button className="primary" onClick={() => isOnline ? fieldReportMutation.mutate(fieldReport) : queueFieldReport(fieldReport, 'Offline report saved. It will sync automatically when connectivity returns.')} disabled={fieldReportMutation.isPending || fieldReport.description.trim().length < 10 || (!fieldReport.matched_segment_id && (fieldReport.latitude === undefined || fieldReport.longitude === undefined))}><ShieldAlert size={16} />{fieldReportMutation.isPending ? 'Submitting…' : isOnline ? 'Submit for verification' : 'Save offline report'}</button></div>
              </section>}

              {fieldReportNotice && <div className="field-report-notice">{fieldReportNotice}<button onClick={() => setFieldReportNotice(null)} aria-label="Dismiss notice">×</button></div>}

              {(deliveryImpacts.length > 0 ? deliveryImpacts : disruptionSummary ? [disruptionSummary] : []).map((impact) => <section key={`${impact.delivery_id}-${impact.route_id ?? impact.outcome}`} className={`disruption-banner ${impact.outcome === 'REROUTED' ? 'rerouted' : impact.outcome === 'AT_RISK' ? 'reassessed' : 'held'}`}>
                <ShieldAlert size={21} />
                <div><p>{impact.outcome === 'REROUTED' ? 'AFFECTED DELIVERY — AUTOMATICALLY REROUTED' : impact.outcome === 'AT_RISK' ? 'AFFECTED DELIVERY — ROUTE REASSESSED' : 'AFFECTED DELIVERY — DISPATCH ACTION REQUIRED'}</p><strong>{impact.message}</strong></div>
                <span>{impact.delivery_id}{impact.delay_minutes !== undefined ? ` · +${impact.delay_minutes} min` : ''}</span>
              </section>)}

              {unverifiedReports.length > 0 && <section className="review-panel">
                <div className="review-panel-head"><div><p className="eyebrow">CONTROL-ROOM VERIFICATION</p><h2>{unverifiedReports.length} field report{unverifiedReports.length > 1 ? 's' : ''} awaiting review</h2></div><ShieldAlert size={20} /></div>
                <div className="review-list">{unverifiedReports.map((incident) => (
                  <article className="review-card" key={incident.id}>
                    <div><strong>{incident.incident_type.replaceAll('_', ' ')}</strong><span>{incident.matched_segment_id ?? `${incident.location.coordinates[1].toFixed(4)}, ${incident.location.coordinates[0].toFixed(4)}`} · reported {incident.reported_accessibility.replace('_', ' ')}</span><p>{incident.description}</p></div>
                    {canVerify && <div className="review-actions">
                      <button onClick={() => verificationMutation.mutate({ incidentId: incident.id, decision: 'CONFIRM' })} disabled={verificationMutation.isPending}>Confirm</button>
                      <button onClick={() => verificationMutation.mutate({ incidentId: incident.id, decision: 'DOWNGRADE' })} disabled={verificationMutation.isPending}>Downgrade</button>
                      <button onClick={() => verificationMutation.mutate({ incidentId: incident.id, decision: 'REJECT' })} disabled={verificationMutation.isPending}>Reject</button>
                    </div>}
                  </article>
                ))}</div>
              </section>}

              <section className="operations-grid">
                <article className="map-card" id="operational-map">
                  <div className="card-head">
                    <div><span className="live-dot" /> <strong>{text.map}</strong><p>{selectedRoute ? `${selectedRoute.label} · ${selectedRoute.distance_km} km · ${selectedRoute.risk_score}% predicted risk` : 'NER-wide roads, incidents, facilities and GPS vehicles'}</p></div>
                    <div className="legend"><span><i className="open" /> Open</span><span><i className="caution" /> Caution</span><span><i className="risk" /> High risk</span><span><i className="blocked" /> Blocked</span></div>
                  </div>
                  <div className="map-wrap">
                    <OperationsMap
                      snapshot={mapQuery.data}
                      selectedRoadId={selectedRoadId}
                      onSelectRoad={setSelectedRoadId}
                      highlightedRoadIds={selectedRoute?.segment_ids}
                      plannedRouteCoordinates={selectedRoute?.geometry.coordinates}
                      plannedRouteSegments={selectedRoute?.intelligence_segments}
                      deliveries={overviewQuery.data.priority_deliveries}
                    />
                    {selectedRoad && (
                      <div className="road-inspector">
                        <div className="inspector-top"><span>{selectedRoad.id}</span><b className={`status status-${selectedRoad.risk_band.toLowerCase()}`}>{selectedRoad.accessibility.replace('_', ' ')}</b></div>
                        <h3>{selectedRoad.road_name}</h3>
                        <p>{selectedRoad.from_node} → {selectedRoad.to_node}</p>
                        <div className="risk-row"><div><span>Risk score</span><strong>{selectedRoad.risk_score}%</strong></div><div className="risk-track"><i style={{ width: `${selectedRoad.risk_score}%` }} /></div></div>
                        {selectedRoad.ml_advisory_status === 'AVAILABLE' && selectedRoad.ml_risk_probability !== null && (
                          <div className="ml-advisory">
                            <span>ML advisory</span><b>{Math.round(selectedRoad.ml_risk_probability * 100)}% · {selectedRoad.ml_risk_band}</b>
                            {selectedRoad.ml_predicted_delay_minutes !== null && <small>Predicted delay: {Math.round(selectedRoad.ml_predicted_delay_minutes)} min</small>}
                          </div>
                        )}
                        <dl><div><dt>Rainfall / 24h</dt><dd>{selectedRoad.rainfall_mm_24h} mm</dd></div><div><dt>Road condition</dt><dd>{selectedRoad.road_condition}</dd></div><div><dt>Confidence</dt><dd>{selectedRoad.confidence}%</dd></div></dl>
                        <small>{selectedRoad.source} · updated {timeLabel(selectedRoad.updated_at)}</small>
                      </div>
                    )}
                  </div>
                </article>

                <aside className="right-column">
                  <article className="panel alerts-panel">
                    <div className="panel-title"><div><span>{text.activeAlerts}</span><h2>{text.alerts}</h2></div><b>{overviewQuery.data.critical_alerts.length}</b></div>
                    <div className="alert-list">
                      {overviewQuery.data.critical_alerts.map((alert) => (
                        <button className={`alert-row ${alert.severity.toLowerCase()}`} key={alert.id} onClick={canAcknowledge ? () => acknowledgementMutation.mutate(alert.id) : undefined} disabled={canAcknowledge && acknowledgementMutation.isPending} title={canAcknowledge ? 'Acknowledge alert' : 'Read-only alert'}>
                          <div className="alert-symbol">{alert.severity === 'CRITICAL' ? <ShieldAlert size={18} /> : <CloudRain size={18} />}</div>
                          <div>{(() => { const localized = localizedAlert(alert.title, alert.message, language); return <><strong>{localized.title}</strong><p>{localized.message}</p></> })()}<span>{timeLabel(alert.created_at)} · {alert.related_entity_id}</span></div>
                          {canAcknowledge && <span className="acknowledge-label">{text.acknowledge}</span>}
                        </button>
                      ))}
                    </div>
                    {isAdmin && <button
                      className="rain-action"
                      onClick={() => rainMutation.mutate()}
                      disabled={rainMutation.isPending || overviewQuery.data.metrics.high_risk_segments > 0}
                    ><CloudRain size={17} />{overviewQuery.data.metrics.high_risk_segments > 0 ? 'Heavy rain event active' : 'Simulate heavy rainfall'}</button>}
                    {isAdmin && <button
                      className="landslide-action"
                      onClick={() => landslideMutation.mutate()}
                      disabled={landslideMutation.isPending || overviewQuery.data.metrics.blocked_segments > 0}
                    ><ShieldAlert size={17} />{overviewQuery.data.metrics.blocked_segments > 0 ? 'Landslide confirmed' : 'Confirm Bhalukpong landslide'}</button>}
                  </article>

                  <article className="panel connectivity-panel">
                    <div className="panel-title"><div><span>NER DATA COVERAGE</span><h2>Operational feeds</h2></div><Navigation size={19} /></div>
                    <div className="coverage-list">
                      <div><Map size={16} /><span><strong>Monitored road segments</strong><small>Optional map layer</small></span><b>{mapQuery.data.road_segments.length}</b></div>
                      <div><ShieldAlert size={16} /><span><strong>Field and incident reports</strong><small>Used when assessing nearby routes</small></span><b>{mapQuery.data.incidents.length}</b></div>
                      <div><Truck size={16} /><span><strong>GPS vehicles</strong><small>Map refreshes every 10 seconds</small></span><b>{mapQuery.data.vehicles.length}</b></div>
                      <div><MapPin size={16} /><span><strong>Hospitals and logistics assets</strong><small>NER-wide prototype catalog</small></span><b>{mapQuery.data.facilities.filter((item) => item.facility_type !== 'BRIDGE_MONITOR').length}</b></div>
                      <div><Navigation size={16} /><span><strong>Bridge and crossing monitors</strong><small>Separate accessibility layer</small></span><b>{mapQuery.data.facilities.filter((item) => item.facility_type === 'BRIDGE_MONITOR').length}</b></div>
                    </div>
                  </article>
                </aside>
              </section>

              <section className="deliveries-section">
                <div className="section-title"><div><p className="eyebrow">PRIORITY MOVEMENTS</p><h2>{text.deliveries}</h2></div><button className="text-button" onClick={() => setActiveSection('Deliveries')}>View all deliveries <ChevronRight size={16} /></button></div>
                <div className="delivery-grid">
                  {overviewQuery.data.priority_deliveries.map((delivery) => (
                    <article className="delivery-card" key={delivery.id}>
                      <div className="delivery-top"><span className={`priority ${delivery.priority.toLowerCase()}`}>{delivery.priority}</span><span className={`delivery-status ${delivery.status.toLowerCase().replace('_', '-')}`}>{delivery.status.replace('_', ' ')}</span></div>
                      <h3>{delivery.cargo_description}</h3><p>{delivery.id} · {delivery.vehicle_id}</p>
                      <div className="journey-line"><span>{delivery.source_name}</span><i /><span>{delivery.destination_name}</span></div>
                      <div className="progress-meta"><span>{delivery.progress_percent}% complete</span><span>ETA {timeLabel(delivery.current_eta)}</span></div>
                      <div className="progress-track"><i style={{ width: `${delivery.progress_percent}%` }} /></div>
                    </article>
                  ))}
                </div>
              </section>
            </>
          )}
          {overviewQuery.data && mapQuery.data && activeSection === 'Deliveries' && <DeliveriesView deliveries={overviewQuery.data.priority_deliveries} vehicles={mapQuery.data.vehicles} canRoute={canRoute} canAssign={isAdmin || authUser.role === 'LOGISTICS_OPERATOR'} assigningDeliveryId={deliveryAssignmentMutation.isPending ? deliveryAssignmentMutation.variables?.deliveryId ?? null : null} onAssignVehicle={(deliveryId, vehicleId) => deliveryAssignmentMutation.mutate({ deliveryId, vehicleId })} onPlanRoute={openPlanner} onViewMap={showOperationalMap} />}
          {overviewQuery.data && mapQuery.data && activeSection === 'Fleet' && <FleetView vehicles={mapQuery.data.vehicles} deliveries={overviewQuery.data.priority_deliveries} telemetry={mapQuery.data.vehicle_telemetry} canManageGps={isAdmin || authUser.role === 'LOGISTICS_OPERATOR'} busy={gpsMutation.isPending || registerVehicleMutation.isPending} updatingVehicleId={gpsMutation.isPending ? gpsMutation.variables?.vehicleId ?? null : null} notice={fleetNotice} onRegister={registerVehicleFromGps} onShareGps={shareVehicleGps} onViewMap={showOperationalMap} />}
          {mapQuery.data && activeSection === 'Field reports' && <FieldOperationsView snapshot={mapQuery.data} isOnline={isOnline} queuedCount={queuedReports.length} isSubmitting={fieldReportMutation.isPending} notice={fieldReportNotice} onSubmit={(report) => isOnline ? fieldReportMutation.mutate(report) : queueFieldReport(report, 'Offline report saved. It will synchronize automatically when connectivity returns.')} />}
          {mapQuery.data && activeSection === 'Incident review' && <IncidentReviewView incidents={mapQuery.data.incidents.filter((incident) => authUser.role !== 'DISTRICT_AUTHORITY' || String(incident.context_snapshot.district ?? '').toLowerCase() === authUser.district?.toLowerCase())} isReviewing={verificationMutation.isPending} onReview={(incidentId, decision) => verificationMutation.mutate({ incidentId, decision })} />}
          {activeSection === 'Analytics' && analyticsQuery.isLoading && <div className="session-loading">Calculating operational analytics…</div>}
          {activeSection === 'Analytics' && analyticsQuery.isError && <div className="load-state error">Analytics could not be loaded from the operational database.</div>}
          {activeSection === 'Analytics' && analyticsQuery.data && <AnalyticsView data={analyticsQuery.data} />}
          {activeSection === 'Alerts' && alertsQuery.isLoading && <div className="session-loading">Loading notification inbox…</div>}
          {activeSection === 'Alerts' && alertsQuery.data && <AlertsView feed={alertsQuery.data} canAcknowledge={canAcknowledge} busy={acknowledgementMutation.isPending} onAcknowledge={(id) => acknowledgementMutation.mutate(id)} />}
          {activeSection === 'Administration' && administrationQuery.isLoading && <div className="session-loading">Loading platform governance data…</div>}
          {activeSection === 'Administration' && administrationQuery.data && <AdministrationView data={administrationQuery.data} />}
        </div>
      </main>
    </div>
  )
}

export default App
