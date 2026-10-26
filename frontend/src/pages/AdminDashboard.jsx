import { useEffect, useMemo, useState } from 'react'
import NcrtcLogo from '../components/NcrtcLogo.jsx'
import './AdminDashboard.css'
import {
  createDepot,
  createRoute,
  createUser,
  createVehicle,
  deleteDepot,
  deleteRoute,
  deleteUser,
  deleteVehicle,
  getCurrentUser,
  getDepots,
  getFleetVehicles,
  getRouteStops,
  getRoutes,
  getUsers,
} from '../services/api.js'

const TOKEN_KEY = 'ncrtc_access_token'

function getToken() {
  return window.sessionStorage.getItem(TOKEN_KEY) || window.localStorage.getItem(TOKEN_KEY)
}

function formatDateTime(date) {
  return new Intl.DateTimeFormat('en-IN', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
    hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata',
  }).format(date)
}

function icon(name) {
  const common = { fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round', strokeLinejoin: 'round' }
  const paths = {
    vehicle: <><path d="M5 19V7a3 3 0 0 1 3-3h8a3 3 0 0 1 3 3v12"/><path d="M5 12h14M8 19v2m8-2v2M8 8h3m5 0h.01"/></>,
    driver: <><circle cx="9" cy="8" r="3.2"/><path d="M3.5 20v-1.4a5.5 5.5 0 0 1 11 0V20M18 8v8m-4-4h8"/></>,
    route: <><circle cx="6" cy="18" r="2.5"/><circle cx="18" cy="6" r="2.5"/><path d="M8.5 18h3a4 4 0 0 0 4-4V10a4 4 0 0 1 4-4"/></>,
    depot: <><path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-6v-7h-4v7H4a1 1 0 0 1-1-1Z"/><path d="M8 11h8"/></>,
    actions: <><path d="M12 2v5m0 10v5M4.9 4.9l3.5 3.5m7.2 7.2 3.5 3.5M2 12h5m10 0h5M4.9 19.1l3.5-3.5m7.2-7.2 3.5-3.5"/></>,
    activity: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
    notice: <><path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/></>,
    users: <><circle cx="9" cy="8" r="3"/><path d="M3 20v-1.5a6 6 0 0 1 12 0V20m1-10a3 3 0 1 0 0-6m1 11a5 5 0 0 1 4 5"/></>,
    requests: <><path d="M5 4h14v16H5zM9 4V2h6v2M8 9h8m-8 4h8m-8 4h5"/></>,
    search: <><circle cx="10.8" cy="10.8" r="6.5"/><path d="m16 16 4.5 4.5"/></>,
    calendar: <><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4m10-4v4M3 10h18"/></>,
    bell: <><path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/></>,
  }
  return <svg viewBox="0 0 24 24" aria-hidden="true" {...common}>{paths[name] || paths.actions}</svg>
}

function initials(name = '') {
  return name.trim().split(/\s+/).slice(0, 2).map((part) => part[0]?.toUpperCase()).join('') || 'AD'
}

export default function AdminDashboard() {
  const [token] = useState(getToken)
  const [user, setUser] = useState(null)
  const [vehicles, setVehicles] = useState([])
  const [depots, setDepots] = useState([])
  const [routes, setRoutes] = useState([])
  const [stops, setStops] = useState([])
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [modal, setModal] = useState(null)
  const [modalError, setModalError] = useState('')
  const [saving, setSaving] = useState(false)
  const [noticeOpen, setNoticeOpen] = useState(false)
  const [accountOpen, setAccountOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [searchOpen, setSearchOpen] = useState(false)
  const [toast, setToast] = useState('')
  const [now, setNow] = useState(() => new Date())
  const [routeStops, setRouteStops] = useState([])
  const [stopDraft, setStopDraft] = useState({ stop_id: '', planned_offset_min: '0' })
  const [userFilter, setUserFilter] = useState('')

  async function refreshData() {
    if (!token) return
    const [vehicleRows, depotRows, routeRows, stopRows, userRows] = await Promise.all([
      getFleetVehicles(token), getDepots(token), getRoutes(token), getRouteStops(token), getUsers(token),
    ])
    setVehicles(vehicleRows)
    setDepots(depotRows)
    setRoutes(routeRows)
    setStops(stopRows)
    setUsers(userRows)
    setLoadError('')
  }

  useEffect(() => {
    if (!token) {
      window.location.replace('/sign-in')
      return undefined
    }
    let active = true
    async function initialize() {
      try {
        const currentUser = await getCurrentUser(token)
        if (!active) return
        if (currentUser.role !== 'admin') {
          window.location.replace(currentUser.role === 'control_operator' ? '/control-room' : '/welcome')
          return
        }
        setUser(currentUser)
        await refreshData()
      } catch (error) {
        if (!active) return
        if (/401|expired|invalid access token/i.test(error.message || '')) {
          window.sessionStorage.removeItem(TOKEN_KEY)
          window.localStorage.removeItem(TOKEN_KEY)
          window.location.replace('/sign-in?expired=1')
        } else {
          setLoadError(error.message || 'Unable to load Admin data.')
        }
      } finally {
        if (active) setLoading(false)
      }
    }
    initialize()
    return () => { active = false }
  }, [token])

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 30_000)
    return () => window.clearInterval(timer)
  }, [])

  useEffect(() => {
    if (!toast) return undefined
    const timer = window.setTimeout(() => setToast(''), 3500)
    return () => window.clearTimeout(timer)
  }, [toast])

  const depotNames = useMemo(() => new Map(depots.map((depot) => [String(depot.id), depot.name])), [depots])
  const drivers = useMemo(() => users.filter((item) => item.role === 'driver'), [users])
  const unassignedManagers = useMemo(() => users.filter((item) => item.role === 'depot_manager' && item.depot_id == null), [users])
  const searchResults = useMemo(() => {
    const query = search.trim().toLowerCase()
    if (query.length < 2) return []
    const records = [
      ...vehicles.map((item) => ({ kind: 'vehicles', label: item.reg_no, detail: depotNames.get(String(item.depot_id)) || 'Vehicle', id: item.id })),
      ...users.map((item) => ({ kind: 'users', role: item.role, label: item.full_name, detail: `${item.username} · ${item.role.replaceAll('_', ' ')}`, id: item.id })),
      ...routes.map((item) => ({ kind: 'routes', label: item.name, detail: item.code, id: item.id })),
      ...depots.map((item) => ({ kind: 'depots', label: item.name, detail: item.code, id: item.id })),
    ]
    return records.filter((item) => `${item.label} ${item.detail}`.toLowerCase().includes(query).toLowerCase()).slice(0, 8)
  }, [search, vehicles, users, routes, depots, depotNames])

  function openModal(nextModal) {
    setModal(nextModal)
    setModalError('')
    setRouteStops([])
    setStopDraft({ stop_id: '', planned_offset_min: '0' })
    setUserFilter(nextModal.type === 'manage' && nextModal.entity === 'users' ? (nextModal.role || '') : '')
  }

  function closeModal() {
    if (saving) return
    setModal(null)
    setModalError('')
  }

  async function handleCreate(event) {
    event.preventDefault()
    if (!modal || modal.type !== 'create') return
    const form = new FormData(event.currentTarget)
    setSaving(true)
    setModalError('')
    try {
      if (modal.entity === 'vehicle') {
        await createVehicle(token, {
          reg_no: String(form.get('reg_no') || '').trim(),
          depot_id: Number(form.get('depot_id')),
          status: String(form.get('status') || '').trim(),
        })
        setToast('Vehicle added successfully.')
      } else if (modal.entity === 'user') {
        const role = String(form.get('role') || '')
        const depotValue = form.get('depot_id')
        if (role === 'driver' && !depotValue) throw new Error('Select a depot for this driver.')
        await createUser(token, {
          username: String(form.get('username') || '').trim(),
          full_name: String(form.get('full_name') || '').trim(),
          password: String(form.get('password') || ''),
          role,
          depot_id: depotValue ? Number(depotValue) : null,
          phone: String(form.get('phone') || '').trim() || null,
          driving_license_number: String(form.get('driving_license_number') || '').trim() || null,
        })
        setToast(`${role.replaceAll('_', ' ')} created successfully.`)
      } else if (modal.entity === 'depot') {
        await createDepot(token, {
          code: String(form.get('code') || '').trim(),
          name: String(form.get('name') || '').trim(),
          location_lat: Number(form.get('location_lat')),
          location_lng: Number(form.get('location_lng')),
          depot_manager_id: Number(form.get('depot_manager_id')),
        })
        setToast('Depot added and manager assigned successfully.')
      } else if (modal.entity === 'route') {
        if (!routeStops.length) throw new Error('Add at least one stop to the route.')
        await createRoute(token, {
          code: String(form.get('code') || '').trim(),
          name: String(form.get('name') || '').trim(),
          depot_id: Number(form.get('depot_id')),
          route_stops: routeStops.map((item, index) => ({ ...item, sequence: index + 1 })),
        })
        setToast('Route created successfully.')
      }
      setModal(null)
      try { await refreshData() } catch (refreshError) { setLoadError(refreshError.message || 'Created successfully, but Admin data could not refresh.') }
    } catch (error) {
      setModalError(error.message || 'The request could not be completed.')
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(entity, record) {
    const recordName = entity === 'vehicles' ? record.reg_no
      : entity === 'depots' ? record.name
        : entity === 'routes' ? record.name
          : record.full_name
    if (!window.confirm(`Delete ${recordName}? This cannot be undone.`)) return
    setSaving(true)
    setModalError('')
    try {
      if (entity === 'vehicles') await deleteVehicle(token, record.id)
      else if (entity === 'depots') await deleteDepot(token, record.id)
      else if (entity === 'routes') await deleteRoute(token, record.id)
      else await deleteUser(token, record.id)
      setToast(`${recordName} deleted successfully.`)
      try { await refreshData() } catch (error) { setLoadError(error.message || 'Deleted successfully, but Admin data could not refresh.') }
    } catch (error) {
      setModalError(error.message || 'The record could not be deleted.')
    } finally {
      setSaving(false)
    }
  }

  function signOut() {
    window.sessionStorage.removeItem(TOKEN_KEY)
    window.localStorage.removeItem(TOKEN_KEY)
    window.sessionStorage.removeItem('ncrtc_username')
    window.location.assign('/')
  }

  function selectSearchResult(result) {
    setSearchOpen(false)
    setSearch('')
    if (result.kind === 'users') openModal({ type: 'manage', entity: 'users', role: result.role })
    else openModal({ type: 'manage', entity: result.kind })
  }

  function addRouteStop() {
    if (!stopDraft.stop_id) {
      setModalError('Choose a stop before adding it to the route.')
      return
    }
    if (routeStops.some((item) => String(item.stop_id) === String(stopDraft.stop_id))) {
      setModalError('A stop can appear only once in a route.')
      return
    }
    setModalError('')
    setRouteStops((current) => [...current, {
      stop_id: Number(stopDraft.stop_id),
      planned_offset_min: Number(stopDraft.planned_offset_min),
    }])
    setStopDraft({ stop_id: '', planned_offset_min: '0' })
  }

  function renderManager() {
    const entity = modal.entity
    const rows = entity === 'vehicles' ? vehicles
      : entity === 'depots' ? depots
        : entity === 'routes' ? routes
          : users.filter((item) => !userFilter || item.role === userFilter)
    const title = entity === 'vehicles' ? 'Manage Vehicles'
      : entity === 'depots' ? 'Manage Depots'
        : entity === 'routes' ? 'Manage Routes'
          : userFilter ? `Manage ${userFilter.replaceAll('_', ' ')}` : 'Manage Users'
    return (
      <>
        <div className="admin-modal-heading"><div><h2>{title}</h2><p>Records shown here are loaded from the NCRTC APIs.</p></div>
          {entity === 'users' && <button className="admin-secondary-button" type="button" onClick={() => openModal({ type: 'create', entity: 'user', role: userFilter || 'control_operator' })}>Add User</button>}
        </div>
        {entity === 'users' && <label className="admin-filter-label">Role<select value={userFilter} onChange={(event) => setUserFilter(event.target.value)}><option value="">All users</option><option value="driver">Driver</option><option value="control_operator">Control room operator</option><option value="depot_manager">Depot manager</option><option value="admin">Administrator</option></select></label>}
        {modalError && <p className="admin-form-error" role="alert">{modalError}</p>}
        <div className="admin-manage-table-wrap"><table className="admin-manage-table">
          <thead><tr>{entity === 'vehicles' ? <><th>Registration</th><th>Depot</th><th>Status</th></> : entity === 'depots' ? <><th>Depot</th><th>Code</th><th>Vehicles</th></> : entity === 'routes' ? <><th>Route</th><th>Code</th><th>Depot</th></> : <><th>Name</th><th>Username</th><th>Role</th><th>Depot</th></>}<th>Action</th></tr></thead>
          <tbody>{rows.map((record) => <tr key={record.id}>
            {entity === 'vehicles' ? <><td>{record.reg_no}</td><td>{depotNames.get(String(record.depot_id)) || '—'}</td><td>{record.status}</td></>
              : entity === 'depots' ? <><td>{record.name}</td><td>{record.code}</td><td>{vehicles.filter((item) => item.depot_id === record.id).length}</td></>
                  : entity === 'routes' ? <><td>{record.name}</td><td>{record.code}</td><td>{depotNames.get(String(record.depot_id)) || '-'}</td></>
                  : <><td>{record.full_name}</td><td>{record.username}</td><td>{record.role.replaceAll('_', ' ')}</td><td>{depotNames.get(String(record.depot_id)) || '—'}</td></>}
            <td><button className="admin-delete-button" type="button" disabled={saving} onClick={() => handleDelete(entity, record)}>Delete</button></td>
          </tr>)}
          {!rows.length && <tr><td className="admin-empty-cell" colSpan={entity === 'users' ? 5 : 4}>No matching records.</td></tr>}</tbody>
        </table></div>
      </>
    )
  }

  function renderCreateForm() {
    if (modal.entity === 'vehicle') return (
      <><h2>Add Vehicle</h2><p className="admin-modal-description">Register a vehicle in an existing depot.</p>
        <label>Registration number<input name="reg_no" required maxLength="20" /></label>
        <label>Depot<select name="depot_id" required defaultValue=""><option value="" disabled>Select depot</option>{depots.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        <label>Status<input name="status" required maxLength="30" placeholder="active" /></label>
      </>
    )
    if (modal.entity === 'user') return (
      <><h2>Add User</h2><p className="admin-modal-description">Create a driver, control-room operator, or depot manager.</p>
        <label>Role<select name="role" required defaultValue={modal.role || 'driver'}><option value="driver">Driver</option><option value="control_operator">Control room operator</option><option value="depot_manager">Depot manager</option></select></label>
        <label>Full name<input name="full_name" required maxLength="150" /></label>
        <label>Username<input name="username" required maxLength="100" autoComplete="off" /></label>
        <label>Temporary password<input name="password" required type="password" autoComplete="new-password" /></label>
        <label>Depot<select name="depot_id" defaultValue=""><option value="">{modal.role === 'control_operator' ? 'No depot for system-wide user' : 'Select depot or leave unassigned'}</option>{depots.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        <label>Phone<input name="phone" maxLength="20" /></label>
        <label>Driving licence number<input name="driving_license_number" maxLength="30" /></label>
      </>
    )
    if (modal.entity === 'depot') return (
      <><h2>Add Depot</h2><p className="admin-modal-description">A depot manager must be assigned as part of depot creation.</p>
        <label>Depot code<input name="code" required maxLength="20" /></label>
        <label>Depot name<input name="name" required maxLength="100" /></label>
        <div className="admin-form-columns"><label>Latitude<input name="location_lat" required type="number" min="-90" max="90" step="any" /></label><label>Longitude<input name="location_lng" required type="number" min="-180" max="180" step="any" /></label></div>
        <label>Depot manager<select name="depot_manager_id" required defaultValue=""><option value="" disabled>Select an unassigned manager</option>{unassignedManagers.map((item) => <option key={item.id} value={item.id}>{item.full_name} · {item.username}</option>)}</select></label>
        {!unassignedManagers.length && <p className="admin-inline-note">No unassigned depot managers. Create one with Manage Users, then return here.</p>}
      </>
    )
    return (
      <><h2>Create Route</h2><p className="admin-modal-description">Choose an existing depot and order its existing stops.</p>
        <label>Route code<input name="code" required maxLength="20" /></label>
        <label>Route name<input name="name" required maxLength="100" /></label>
        <label>Depot<select name="depot_id" required defaultValue=""><option value="" disabled>Select depot</option>{depots.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        <div className="admin-route-stop-editor"><strong>Route stops</strong><div className="admin-form-columns"><label>Stop<select value={stopDraft.stop_id} onChange={(event) => setStopDraft((state) => ({ ...state, stop_id: event.target.value }))}><option value="">Select stop</option>{stops.filter((stop) => !routeStops.some((item) => item.stop_id === stop.id)).map((stop) => <option key={stop.id} value={stop.id}>{stop.name}</option>)}</select></label><label>Offset (minutes)<input type="number" min="0" step="1" value={stopDraft.planned_offset_min} onChange={(event) => setStopDraft((state) => ({ ...state, planned_offset_min: event.target.value }))} /></label></div><button className="admin-secondary-button" type="button" onClick={addRouteStop}>Add stop</button>
          {routeStops.length > 0 && <ol>{routeStops.map((item, index) => <li key={item.stop_id}><span>{index + 1}. {stops.find((stop) => stop.id === item.stop_id)?.name || `Stop ${item.stop_id}`} · +{item.planned_offset_min} min</span><button type="button" onClick={() => setRouteStops((current) => current.filter((row) => row.stop_id !== item.stop_id))}>Remove</button></li>)}</ol>}
        </div>
      </>
    )
  }

  if (loading) return <main className="admin-loading" aria-live="polite">Loading Admin Dashboard…</main>
  if (!user) return <main className="admin-loading">{loadError ? <p role="alert">{loadError}</p> : 'Checking administrator access…'}</main>

  const actions = [
    ['vehicle', 'Add Vehicle', 'vehicle', () => openModal({ type: 'create', entity: 'vehicle' })],
    ['driver', 'Add Driver', 'driver', () => openModal({ type: 'create', entity: 'user', role: 'driver' })],
    ['depot', 'Add Depot', 'depot', () => openModal({ type: 'create', entity: 'depot' })],
    ['route', 'Create Route', 'route', () => openModal({ type: 'create', entity: 'route' })],
    ['notice', 'Publish Notice', 'notice', () => openModal({ type: 'placeholder', title: 'Publish Notice', message: 'The CMS notice API is not registered. No notice has been published.' })],
    ['users', 'Manage Users', 'users', () => openModal({ type: 'manage', entity: 'users' })],
    ['requests', 'Requests', 'requests', () => openModal({ type: 'placeholder', title: 'Requests', message: 'A requests API is not available in this backend.' })],
  ]

  return (
    <main className="admin-page">
      <header className="admin-topbar">
        <a className="admin-brand" href="/" aria-label="NCRTC overview"><NcrtcLogo className="admin-logo" /></a>
        <div className="admin-search-wrap">
          <label className="admin-global-search">{icon('search')}<input value={search} onFocus={() => setSearchOpen(true)} onBlur={() => window.setTimeout(() => setSearchOpen(false), 150)} onChange={(event) => { setSearch(event.target.value); setSearchOpen(true) }} onKeyDown={(event) => { if (event.key === 'Escape') setSearchOpen(false); if (event.key === 'Enter' && searchResults[0]) selectSearchResult(searchResults[0]) }} placeholder="Search vehicles, drivers, routes, depots, users or notices…" aria-label="Search system records" />{search && <button type="button" aria-label="Clear search" onClick={() => { setSearch(''); setSearchOpen(true) }}>×</button>}</label>
          {searchOpen && search.trim().length >= 2 && <div className="admin-search-results" role="listbox">
            {searchResults.map((result) => <button key={`${result.kind}-${result.id}`} type="button" role="option" onMouseDown={(event) => event.preventDefault()} onClick={() => selectSearchResult(result)}><span><strong>{result.label}</strong><small>{result.detail}</small></span><i>{result.kind === 'users' ? result.role.replaceAll('_', ' ') : result.kind.slice(0, -1)}</i></button>)}
            {!searchResults.length && <p>No matches in available vehicle, user, route, or depot APIs. Notice search is unavailable.</p>}
          </div>}
        </div>
        <div className="admin-header-tools">
          <div className="admin-popover-anchor"><button className="admin-notification-button" type="button" aria-label="Notifications" aria-expanded={noticeOpen} onClick={() => setNoticeOpen((value) => !value)}>{icon('bell')}</button>
            {noticeOpen && <div className="admin-notification-popover"><strong>Notifications unavailable</strong><span>No notification API is registered.</span></div>}
          </div>
          <div className="admin-popover-anchor"><button className="admin-account-button" type="button" aria-haspopup="menu" aria-expanded={accountOpen} onClick={() => setAccountOpen((value) => !value)}><span className="admin-avatar">{initials(user.full_name)}</span><span><strong>{user.full_name}</strong><small>{user.username}</small></span><i>⌄</i></button>
            {accountOpen && <div className="admin-account-popover" role="menu"><button type="button" role="menuitem" onClick={signOut}>Sign out</button></div>}
          </div>
        </div>
      </header>

      <div className="admin-content">
        <div className="admin-title-row"><div><h1>Admin Dashboard</h1><p>Manage system master data, users, routes, depots and official notices.</p></div><div className="admin-datetime">{icon('calendar')}<span>{formatDateTime(now)}</span></div></div>
        {loadError && <p className="admin-load-error" role="alert">{loadError}</p>}
        <section className="admin-kpis" aria-label="System totals">
          <button className="admin-kpi vehicle" type="button" onClick={() => openModal({ type: 'manage', entity: 'vehicles' })}><span className="admin-kpi-icon">{icon('vehicle')}</span><span><small>Total Vehicles</small><strong>{vehicles.length}</strong><em>Registered vehicles</em></span><b>›</b></button>
          <button className="admin-kpi driver" type="button" onClick={() => openModal({ type: 'manage', entity: 'users', role: 'driver' })}><span className="admin-kpi-icon">{icon('driver')}</span><span><small>Total Drivers</small><strong>{drivers.length}</strong><em>Registered drivers</em></span><b>›</b></button>
          <button className="admin-kpi route" type="button" onClick={() => openModal({ type: 'manage', entity: 'routes' })}><span className="admin-kpi-icon">{icon('route')}</span><span><small>Total Routes</small><strong>{routes.length}</strong><em>Configured routes</em></span><b>›</b></button>
          <button className="admin-kpi depot" type="button" onClick={() => openModal({ type: 'manage', entity: 'depots' })}><span className="admin-kpi-icon">{icon('depot')}</span><span><small>Total Depots</small><strong>{depots.length}</strong><em>Configured depots</em></span><b>›</b></button>
        </section>

        <section className="admin-card admin-quick-actions">
          <div className="admin-section-heading"><span className="admin-section-icon blue">{icon('actions')}</span><div><h2>Quick Actions</h2><p>Perform common administrative tasks</p></div></div>
          <div className="admin-action-grid">{actions.map(([key, label, glyph, action]) => <button className={`admin-action-tile ${key}`} key={key} type="button" onClick={action}><span>{icon(glyph)}</span><strong>{label}</strong></button>)}</div>
        </section>

        <div className="admin-lower-grid">
          <section className="admin-card admin-data-panel">
            <div className="admin-section-heading"><span className="admin-section-icon blue">{icon('activity')}</span><div><h2>Recent Activity</h2><p>Latest changes in the system</p></div><button className="admin-view-all" type="button" onClick={() => openModal({ type: 'placeholder', title: 'Recent Activity', message: 'An activity feed API is not available. No activity records are being shown as system history.' })}>View All</button></div>
            <div className="admin-table-scroll"><table className="admin-dashboard-table"><thead><tr><th>Time</th><th>Activity</th><th>Details</th><th>Performed By</th></tr></thead><tbody><tr><td className="admin-empty-row" colSpan="4">Activity feed API unavailable. No system activity is currently reported.</td></tr></tbody></table></div>
          </section>
          <section className="admin-card admin-data-panel">
            <div className="admin-section-heading"><span className="admin-section-icon blue">{icon('notice')}</span><div><h2>Latest Notices</h2><p>Recently published notices</p></div><button className="admin-view-all" type="button" onClick={() => openModal({ type: 'placeholder', title: 'Latest Notices', message: 'The CMS notices API is not registered, so no notices can be listed here.' })}>View All</button></div>
            <div className="admin-table-scroll"><table className="admin-dashboard-table notices"><thead><tr><th>Title</th><th>Published On</th><th>Target Audience</th><th>Status</th></tr></thead><tbody><tr><td className="admin-empty-row" colSpan="4">Notices API unavailable. No notice records are being shown.</td></tr></tbody></table></div>
          </section>
        </div>
      </div>

      {modal && <div className="admin-modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && closeModal()}>
        <section className={`admin-modal ${modal.type === 'manage' ? 'wide' : ''}`} role="dialog" aria-modal="true" aria-label={modal.type === 'manage' ? 'Manage records' : modal.title || 'Admin action'}>
          <button className="admin-modal-close" type="button" aria-label="Close dialog" onClick={closeModal}>×</button>
          {modal.type === 'manage' ? renderManager() : modal.type === 'create' ? <form className="admin-create-form" onSubmit={handleCreate}>
            {renderCreateForm()}
            {modalError && <p className="admin-form-error" role="alert">{modalError}</p>}
            <div className="admin-modal-actions"><button className="admin-secondary-button" type="button" onClick={closeModal} disabled={saving}>Cancel</button><button className="admin-primary-button" type="submit" disabled={saving || (modal.entity === 'depot' && unassignedManagers.length === 0)}>{saving ? 'Saving…' : 'Save'}</button></div>
          </form> : <div className="admin-placeholder"><span>{icon(modal.title === 'Requests' ? 'requests' : 'notice')}</span><h2>{modal.title}</h2><p>{modal.message}</p><button className="admin-primary-button" type="button" onClick={closeModal}>Close</button></div>}
        </section>
      </div>}
      {toast && <div className="admin-toast" role="status">{toast}</div>}
    </main>
  )
}
