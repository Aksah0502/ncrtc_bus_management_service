import { useEffect, useMemo, useRef, useState } from 'react'
import L from 'leaflet'
import { MapContainer, Marker, Polyline, Popup, TileLayer, Tooltip, useMap } from 'react-leaflet'
import NcrtcLogo from '../components/NcrtcLogo.jsx'
import { getCurrentUser, getDepots, getFleetVehicles, getLiveDetails, getLiveLocations } from '../services/api.js'
import 'leaflet/dist/leaflet.css'

const TOKEN_KEY = 'ncrtc_access_token'
const POLL_INTERVAL_MS = 5000

const demoIncidents = [
  { title: 'Engine Failure', bus: 'DL1PC 3195', route: 'R-08', time: '09:42 AM', tone: 'red' },
  { title: 'Delay Alert (> 15 mins)', bus: 'DL1PC 7765', route: 'R-15', time: '09:28 AM', tone: 'amber' },
  { title: 'Geofence Breach', bus: 'DL1PC 5521', route: 'Depot: Noida', time: '09:15 AM', tone: 'amber' },
  { title: 'Breakdown Resolved', bus: 'DL1PC 4492', route: 'R-32', time: '08:50 AM', tone: 'blue' },
  { title: 'Low Speed Alert', bus: 'DL1PC 6674', route: 'R-12', time: '08:30 AM', tone: 'amber' },
]

const vehicleIcon = L.divIcon({
  className: 'map-vehicle-icon',
  html: '<span class="vehicle-pin"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 18V7a3 3 0 0 1 3-3h8a3 3 0 0 1 3 3v11"/><path d="M5 11h14M8 18v2m8-2v2M8 8h3m5 0h.01"/></svg></span>',
  iconSize: [36, 36],
  iconAnchor: [18, 18],
})

const depotIcon = L.divIcon({
  className: 'map-depot-icon',
  html: '<span class="depot-pin"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-6v-7h-4v7H4a1 1 0 0 1-1-1Z"/><path d="M8 11h8"/></svg></span>',
  iconSize: [34, 40],
  iconAnchor: [17, 37],
})

function getToken() {
  return window.sessionStorage.getItem(TOKEN_KEY) || window.localStorage.getItem(TOKEN_KEY)
}

function isUnauthorized(error) {
  if (!/401|expired|invalid access token/i.test(error?.message || '')) return false
  window.sessionStorage.removeItem(TOKEN_KEY)
  window.localStorage.removeItem(TOKEN_KEY)
  window.location.replace('/sign-in?expired=1')
  return true
}

function initials(name = '') {
  return name.trim().split(/\s+/).slice(0, 2).map((part) => part[0]?.toUpperCase()).join('') || 'CR'
}

function formatStatus(value = '') {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase()) || 'Unknown'
}

function formatTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat('en-IN', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata' }).format(date)
}

function MapAutoCenter({ points }) {
  const map = useMap()
  const centered = useRef(false)
  useEffect(() => {
    if (centered.current || points.length === 0) return
    const lat = points.reduce((sum, point) => sum + point[0], 0) / points.length
    const lng = points.reduce((sum, point) => sum + point[1], 0) / points.length
    map.setView([lat, lng], 10, { animate: false })
    centered.current = true
  }, [map, points])
  return null
}

function InvalidateMapSize({ expanded }) {
  const map = useMap()
  useEffect(() => {
    const timer = window.setTimeout(() => map.invalidateSize(), 120)
    return () => window.clearTimeout(timer)
  }, [expanded, map])
  return null
}

function BusGlyph() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 18V7a3 3 0 0 1 3-3h8a3 3 0 0 1 3 3v11"/><path d="M5 11h14M8 18v2m8-2v2M8 8h3m5 0h.01"/></svg>
}

function MapView({ locations, depots, selectedDepot, selectedVehicleId, selectedDetails, onSelectVehicle, expanded, points }) {
  const visibleDepots = selectedDepot ? depots.filter((depot) => String(depot.id) === String(selectedDepot)) : depots
  const selectedPath = selectedDetails?.pings?.map((ping) => [ping.lat, ping.lng]) || []

  return (
    <MapContainer className="fleet-map" center={points[0]} zoom={10} scrollWheelZoom>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <MapAutoCenter points={points} />
      <InvalidateMapSize expanded={expanded} />
      {visibleDepots.filter((depot) => Number.isFinite(depot.location_lat) && Number.isFinite(depot.location_lng)).map((depot) => (
        <Marker key={`depot-${depot.id}`} position={[depot.location_lat, depot.location_lng]} icon={depotIcon}>
          <Tooltip>{depot.name}</Tooltip>
        </Marker>
      ))}
      {locations.filter((location) => Number.isFinite(location.lat) && Number.isFinite(location.lng)).map((location) => (
        <Marker key={location.vehicle_id} position={[location.lat, location.lng]} icon={vehicleIcon} eventHandlers={{ click: () => onSelectVehicle(location.vehicle_id) }}>
          <Tooltip direction="top" offset={[0, -16]}>{location.reg_no} · {location.speed_kmh == null ? '—' : `${Math.round(location.speed_kmh)} km/h`}</Tooltip>
          {selectedVehicleId === location.vehicle_id && <Popup>
            <div className="map-popup">
              <strong>{location.reg_no}</strong>
              <span>{location.speed_kmh == null ? '—' : `${Math.round(location.speed_kmh)} km/h`}</span>
              {selectedDetails?.driver_name && <span>{selectedDetails.driver_name}</span>}
              {selectedDetails?.route_code && <span>{selectedDetails.route_code}{selectedDetails.route_name ? ` · ${selectedDetails.route_name}` : ''}</span>}
            </div>
          </Popup>}
        </Marker>
      ))}
      {selectedPath.length > 1 && <Polyline positions={selectedPath} pathOptions={{ color: '#087ac1', weight: 4, opacity: 0.82 }} />}
    </MapContainer>
  )
}

function IncidentPanel() {
  return (
    <section className="dashboard-panel incident-panel">
      <div className="panel-heading">
        <span className="panel-heading-icon incident-icon">!</span>
        <h2>Recent Incidents &amp; Alerts</h2>
        <span className="demo-tag">Sample</span>
        <button className="text-action" type="button">View All</button>
      </div>
      <div className="incident-list">
        {demoIncidents.map((incident) => (
          <div className="incident-row" key={`${incident.bus}-${incident.time}`}>
            <span className={`status-dot ${incident.tone}`} />
            <div className="incident-copy"><strong>{incident.title}</strong><span>{incident.bus} <i>│</i> {incident.route}</span></div>
            <time>{incident.time}</time>
            <span className="row-chevron">›</span>
          </div>
        ))}
      </div>
      <p className="sample-note">Sample display · incident API unavailable</p>
    </section>
  )
}

export default function ControlRoomDashboard() {
  const [token] = useState(getToken)
  const [user, setUser] = useState(null)
  const [vehicles, setVehicles] = useState([])
  const [depots, setDepots] = useState([])
  const [locations, setLocations] = useState([])
  const [selectedDepot, setSelectedDepot] = useState('')
  const [selectedVehicleId, setSelectedVehicleId] = useState(null)
  const [selectedDetails, setSelectedDetails] = useState(null)
  const [detailsLoading, setDetailsLoading] = useState(false)
  const [detailsError, setDetailsError] = useState('')
  const [fleetLoading, setFleetLoading] = useState(true)
  const [fleetError, setFleetError] = useState('')
  const [liveError, setLiveError] = useState('')
  const [liveUpdatedAt, setLiveUpdatedAt] = useState(null)
  const [fleetSearch, setFleetSearch] = useState('')
  const [showAllVehicles, setShowAllVehicles] = useState(false)
  const [showActiveOnly, setShowActiveOnly] = useState(false)
  const [expandedMap, setExpandedMap] = useState(false)
  const [now, setNow] = useState(() => new Date())
  const [refreshKey, setRefreshKey] = useState(0)
  const [refreshing, setRefreshing] = useState(false)
  const unauthorized = useRef(false)

  const activeCount = useMemo(() => vehicles.filter((vehicle) => vehicle.status?.toLowerCase() === 'active').length, [vehicles])
  const depotsById = useMemo(() => new Map(depots.map((depot) => [String(depot.id), depot])), [depots])
  const filteredVehicles = useMemo(() => vehicles
    .filter((vehicle) => !showActiveOnly || vehicle.status?.toLowerCase() === 'active')
    .filter((vehicle) => {
      const query = fleetSearch.trim().toLowerCase()
      if (!query) return true
      const depotName = depotsById.get(String(vehicle.depot_id))?.name || ''
      return vehicle.reg_no.toLowerCase().includes(query) || depotName.toLowerCase().includes(query)
    }), [vehicles, showActiveOnly, fleetSearch, depotsById])
  const mapPoints = useMemo(() => {
    const depotPoints = depots.filter((depot) => Number.isFinite(depot.location_lat) && Number.isFinite(depot.location_lng)).map((depot) => [depot.location_lat, depot.location_lng])
    if (depotPoints.length) return depotPoints
    return locations.filter((location) => Number.isFinite(location.lat) && Number.isFinite(location.lng)).map((location) => [location.lat, location.lng])
  }, [depots, locations])
  const pingTimes = locations.map((item) => new Date(item.ts).getTime()).filter(Number.isFinite)
  const newestPingAge = pingTimes.length ? Math.max(0, Date.now() - Math.max(...pingTimes)) : null
  const isStale = newestPingAge !== null && newestPingAge > 60_000

  useEffect(() => {
    if (!token) {
      window.location.replace('/sign-in')
      return
    }
    let active = true
    async function initialize() {
      try {
        const currentUser = await getCurrentUser(token)
        if (!active) return
        if (currentUser.role !== 'control_operator') {
          window.location.replace('/welcome')
          return
        }
        setUser(currentUser)
        const [vehicleRows, depotRows] = await Promise.all([getFleetVehicles(token), getDepots(token)])
        if (!active) return
        setVehicles(vehicleRows)
        setDepots(depotRows)
        setFleetError('')
      } catch (error) {
        if (!active) return
        if (isUnauthorized(error)) {
          unauthorized.current = true
        } else {
          setFleetError(error.message)
        }
      } finally {
        if (active) setFleetLoading(false)
      }
    }
    initialize()
    return () => { active = false }
  }, [token])

  useEffect(() => {
    if (!user || !token || unauthorized.current) return undefined
    let cancelled = false
    let timer
    let controller
    async function poll() {
      controller = new AbortController()
      try {
        const freshLocations = await getLiveLocations(token, selectedDepot || undefined, controller.signal)
        if (cancelled) return
        setLocations(freshLocations)
        setLiveUpdatedAt(new Date())
        setLiveError('')
      } catch (error) {
        if (cancelled || error.name === 'AbortError') return
        if (isUnauthorized(error)) {
          unauthorized.current = true
          return
        }
        setLiveError(error.message)
      } finally {
        if (!cancelled) timer = window.setTimeout(poll, POLL_INTERVAL_MS)
      }
    }
    poll()
    return () => {
      cancelled = true
      window.clearTimeout(timer)
      controller?.abort()
    }
  }, [user, token, selectedDepot, refreshKey])

  useEffect(() => {
    if (!selectedVehicleId || !token) {
      setSelectedDetails(null)
      setDetailsError('')
      return undefined
    }
    const controller = new AbortController()
    setDetailsLoading(true)
    setDetailsError('')
    getLiveDetails(token, selectedVehicleId, controller.signal)
      .then((details) => { setSelectedDetails(details); setDetailsError('') })
      .catch((error) => {
        if (error.name !== 'AbortError' && !isUnauthorized(error)) setDetailsError(error.message)
      })
      .finally(() => { if (!controller.signal.aborted) setDetailsLoading(false) })
    return () => controller.abort()
  }, [selectedVehicleId, token])

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 30_000)
    return () => window.clearInterval(timer)
  }, [])

  async function refreshDashboard() {
    if (!token || refreshing) return
    setRefreshing(true)
    try {
      const [vehicleRows, depotRows] = await Promise.all([getFleetVehicles(token), getDepots(token)])
      setVehicles(vehicleRows)
      setDepots(depotRows)
      setFleetError('')
      setRefreshKey((key) => key + 1)
    } catch (error) {
      if (!isUnauthorized(error)) setFleetError(error.message)
    } finally {
      setRefreshing(false)
    }
  }

  function signOut() {
    window.sessionStorage.removeItem(TOKEN_KEY)
    window.localStorage.removeItem(TOKEN_KEY)
    window.location.assign('/')
  }

  const mapHasData = mapPoints.length > 0
  const listRows = showAllVehicles ? filteredVehicles : filteredVehicles.slice(0, 5)
  const formattedDate = new Intl.DateTimeFormat('en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric', timeZone: 'Asia/Kolkata' }).format(now)
  const formattedClock = new Intl.DateTimeFormat('en-IN', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata' }).format(now)

  if (!user) return <main className="dashboard-loading" aria-live="polite">{fleetError ? <p role="alert">{fleetError}</p> : <p>Loading control room…</p>}</main>

  return (
    <main className="control-room-page">
      <header className="dashboard-topbar">
        <a className="dashboard-brand" href="/" aria-label="NCRTC overview"><NcrtcLogo className="dashboard-logo" /></a>
        <label className="global-search"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.8" cy="10.8" r="6.5"/><path d="m16 16 4.5 4.5"/></svg><input aria-label="Search bus number, driver, route, depot" placeholder="Search bus number, driver, route, depot…" /></label>
        <button className="notification-button" type="button" aria-label="Notifications"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/></svg><span className="notification-dot"/></button>
        <button className="operator-menu" onClick={signOut} title="Sign out">
          <span className="operator-avatar">{initials(user.full_name)}</span>
          <span className="operator-label"><strong>{user.full_name}</strong><small>{user.username}</small></span>
          <span className="operator-caret">⌄</span>
        </button>
      </header>

      <div className="dashboard-content">
        <div className="dashboard-title-row">
          <div><h1>Control Room Dashboard</h1><p>Live overview of bus operations across the Delhi-NCR region</p></div>
          <div className="dashboard-actions"><div className="dashboard-clock"><svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4m10-4v4M3 10h18"/></svg><span>{formattedDate}</span><time>{formattedClock}</time></div><button className="refresh-button" onClick={refreshDashboard} disabled={refreshing}><svg className={refreshing ? 'spinning' : ''} viewBox="0 0 24 24" aria-hidden="true"><path d="M20 7v5h-5M4 17v-5h5"/><path d="M6.1 9A7 7 0 0 1 18 6l2 6M4 12l2 6a7 7 0 0 0 11.9-3"/></svg>{refreshing ? 'Refreshing' : 'Refresh'}</button></div>
        </div>

        <section className="stat-grid" aria-label="Fleet overview">
          <button className="stat-card" onClick={() => { setShowActiveOnly(false); setShowAllVehicles(true); document.getElementById('vehicle-fleet')?.scrollIntoView({ behavior: 'smooth', block: 'start' }) }}>
            <span className="stat-icon blue"><BusGlyph /></span><span className="stat-copy"><strong>Total Buses</strong><b>{fleetLoading ? '—' : vehicles.length}</b><small>{fleetLoading ? 'Loading fleet…' : 'Buses registered'}</small></span><span className="stat-chevron">›</span>
          </button>
          <button className="stat-card" onClick={() => { setShowActiveOnly(true); setShowAllVehicles(true); document.getElementById('vehicle-fleet')?.scrollIntoView({ behavior: 'smooth', block: 'start' }) }}>
            <span className="stat-icon green"><BusGlyph /></span><span className="stat-copy"><strong>Active Buses</strong><b>{fleetLoading ? '—' : activeCount}</b><small>{fleetLoading ? 'Loading fleet…' : `${vehicles.length ? ((activeCount / vehicles.length) * 100).toFixed(1) : '0.0'}% in operation`}</small></span><span className="stat-chevron">›</span>
          </button>
          <div className="stat-card stat-card-demo">
            <span className="stat-icon red"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3 9 17H3L12 3Z"/><path d="M12 9v4m0 3h.01"/></svg></span><span className="stat-copy"><strong>Open Incidents <small className="demo-tag">Sample</small></strong><b>15</b><small>Demo display · incident API unavailable</small></span><span className="stat-chevron">›</span>
          </div>
        </section>

        {fleetError && <div className="dashboard-error" role="alert">{fleetError}</div>}
        <div className={`dashboard-panels${expandedMap ? ' map-expanded-layout' : ''}`}>
          <section className="dashboard-panel map-panel">
            <div className="map-panel-heading"><span className="map-heading-icon"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3Z"/><path d="M9 3v15m6-12v15"/></svg></span><h2>Live Fleet Map</h2><span className="live-indicator"><i/> LIVE</span><button className="map-expand-button" aria-label={expandedMap ? 'Exit full screen map' : 'Expand map'} onClick={() => setExpandedMap((value) => !value)}><svg viewBox="0 0 24 24" aria-hidden="true">{expandedMap ? <path d="M8 3v5H3m13-5v5h5M3 16h5v5m13-5h-5v5"/> : <path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5"/>}</svg></button></div>
            <div className="map-toolbar">
              <label className="map-filter"><span className="sr-only">Filter by depot</span><select value={selectedDepot} onChange={(event) => setSelectedDepot(event.target.value)}><option value="">All Depots</option>{depots.map((depot) => <option key={depot.id} value={depot.id}>{depot.name}</option>)}</select><span className="select-caret">⌄</span></label>
              <div className="map-legend"><span><i className="legend-bus"/> Active vehicle</span><span><i className="legend-depot"/> Depot</span></div>
              {liveUpdatedAt && <span className="map-updated">Updated {formatTime(liveUpdatedAt)}</span>}
            </div>
            <div className="map-frame">
              {mapHasData ? <MapView locations={locations} depots={depots} selectedDepot={selectedDepot} selectedVehicleId={selectedVehicleId} selectedDetails={selectedDetails} onSelectVehicle={setSelectedVehicleId} expanded={expandedMap} points={mapPoints} /> : <div className="map-empty">{liveError ? 'Live map data could not be loaded.' : 'Waiting for vehicle or depot coordinates from the API…'}</div>}
              {liveError && <div className="map-status map-status-error" role="status">Live location update failed. Showing the last successful response.</div>}
              {!liveError && isStale && locations.length > 0 && <div className="map-status map-status-stale" role="status">Vehicle location data is stale.</div>}
              {!liveError && !isStale && locations.length === 0 && liveUpdatedAt && <div className="map-status" role="status">No active vehicle locations returned by the API.</div>}
              {selectedVehicleId && <aside className="vehicle-detail-card">
                <button className="detail-close" aria-label="Close vehicle details" onClick={() => setSelectedVehicleId(null)}>×</button>
                <strong>{selectedDetails?.reg_no || vehicles.find((item) => item.id === selectedVehicleId)?.reg_no || 'Vehicle'}</strong>
                {detailsLoading && <span>Loading vehicle details…</span>}
                {detailsError && <span className="detail-error">{detailsError}</span>}
                {selectedDetails && <><span>{selectedDetails.driver_name || '—'}</span><span>{selectedDetails.route_code ? `${selectedDetails.route_code}${selectedDetails.route_name ? ` · ${selectedDetails.route_name}` : ''}` : '—'}</span><small>{selectedDetails.pings.length} recent location points</small></>}
              </aside>}
            </div>
          </section>

          <aside className="dashboard-sidebar">
            <section className="dashboard-panel fleet-panel" id="vehicle-fleet">
              <div className="panel-heading fleet-heading"><span className="panel-heading-icon fleet-icon"><BusGlyph /></span><h2>Vehicle Fleet</h2><button className="text-action" onClick={() => setShowAllVehicles((value) => !value)}>{showAllVehicles ? 'Show Less' : 'View All'}</button></div>
              <label className="fleet-search"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.8" cy="10.8" r="6.5"/><path d="m16 16 4.5 4.5"/></svg><input value={fleetSearch} onChange={(event) => setFleetSearch(event.target.value)} placeholder="Search registration or depot…" aria-label="Search vehicles by registration or depot" /></label>
              <div className="fleet-list">
                {fleetLoading && <p className="panel-state">Loading vehicles…</p>}
                {!fleetLoading && fleetError && <p className="panel-state error-text">Could not load fleet.</p>}
                {!fleetLoading && !fleetError && listRows.length === 0 && <p className="panel-state">No vehicles match this search.</p>}
                {!fleetLoading && !fleetError && listRows.map((vehicle) => {
                  const status = vehicle.status?.toLowerCase() || 'unknown'
                  const depotName = depotsById.get(String(vehicle.depot_id))?.name || `Depot ${vehicle.depot_id}`
                  return <button key={vehicle.id} className={`fleet-row${selectedVehicleId === vehicle.id ? ' selected' : ''}`} onClick={() => setSelectedVehicleId(vehicle.id)}>
                    <span className={`fleet-bus-icon ${status}`}><BusGlyph /></span>
                    <span className="fleet-vehicle-copy"><strong>{vehicle.reg_no}</strong><small>{depotName}</small></span>
                    <span className={`fleet-status ${status}`}><i/>{formatStatus(vehicle.status)}</span>
                    <span className="fleet-more" aria-hidden="true">⋮</span>
                  </button>
                })}
              </div>
              {filteredVehicles.length > 5 && <button className="fleet-show-more" onClick={() => setShowAllVehicles((value) => !value)}>{showAllVehicles ? 'Show fewer vehicles' : `Show all ${filteredVehicles.length} vehicles`}</button>}
            </section>
            <IncidentPanel />
          </aside>
        </div>
        <footer className="dashboard-footer">Live fleet data from NCRTC APIs <span>•</span> Incident panel contains sample display data</footer>
      </div>
    </main>
  )
}
