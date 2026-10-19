import { Crosshair, MapPin } from '@phosphor-icons/react'
import { useEffect, useRef, useState } from 'react'
import type { GeoJSONSource, Map as MapLibreMap } from 'maplibre-gl'

import { useI18n } from '../lib/i18n'

export interface LatLng {
  lat: number
  lng: number
}

interface Props {
  value: LatLng | null
  radiusKm: number
  onChange: (value: LatLng) => void
}

const BAGHDAD: LatLng = { lat: 33.3128, lng: 44.3615 }
const STYLES = {
  light: import.meta.env.VITE_MAP_STYLE_LIGHT ?? 'https://tiles.openfreemap.org/styles/positron',
  dark: import.meta.env.VITE_MAP_STYLE_DARK ?? 'https://tiles.openfreemap.org/styles/dark',
}

/** The delivery area as a polygon, for drawing on the map. */
function circle(center: LatLng, km: number): GeoJSON.Feature<GeoJSON.Polygon> {
  const points: [number, number][] = []
  const dLat = km / 110.574
  const dLng = km / (111.32 * Math.cos((center.lat * Math.PI) / 180))
  for (let i = 0; i <= 64; i++) {
    const a = (i / 64) * 2 * Math.PI
    points.push([center.lng + dLng * Math.cos(a), center.lat + dLat * Math.sin(a)])
  }
  return { type: 'Feature', properties: {}, geometry: { type: 'Polygon', coordinates: [points] } }
}

const round = (n: number) => Math.round(n * 1e6) / 1e6

/**
 * Move the map until the pin sits on the store's door. The shaded circle is
 * the delivery area. Without WebGL (old tablets, tests) it falls back to
 * typing the coordinates.
 */
export function LocationPicker({ value, radiusKm, onChange }: Props) {
  const { t } = useI18n()
  const container = useRef<HTMLDivElement>(null)
  const map = useRef<MapLibreMap | null>(null)
  // The map's event handlers read the newest props through this.
  const zoomHelp = { windows: t('mapZoomWindows'), mac: t('mapZoomMac'), mobile: t('mapZoomMobile') }
  const latest = useRef({ value, radiusKm, onChange, zoomHelp })
  useEffect(() => {
    latest.current = { value, radiusKm, onChange, zoomHelp }
  })
  const [failed, setFailed] = useState(false)
  const [moving, setMoving] = useState(false)
  const [locating, setLocating] = useState(false)
  // Without a map: the coordinates as typed.
  const [typed, setTyped] = useState({ lat: value ? String(value.lat) : '', lng: value ? String(value.lng) : '' })

  useEffect(() => {
    let cancelled = false
    let created: MapLibreMap | null = null
    ;(async () => {
      try {
        const [{ default: maplibregl }] = await Promise.all([
          import('maplibre-gl'),
          import('maplibre-gl/dist/maplibre-gl.css'),
        ])
        if (cancelled || !container.current) return
        const start = latest.current.value ?? BAGHDAD
        const dark = window.matchMedia?.('(prefers-color-scheme: dark)').matches
        created = new maplibregl.Map({
          container: container.current,
          style: dark ? STYLES.dark : STYLES.light,
          center: [start.lng, start.lat],
          zoom: latest.current.value ? 15 : 11,
          attributionControl: { compact: true },
          // Scrolling the form scrolls the page; zooming needs Ctrl/⌘ or two fingers.
          cooperativeGestures: true,
          locale: {
            'CooperativeGesturesHandler.WindowsHelpText': latest.current.zoomHelp.windows,
            'CooperativeGesturesHandler.MacHelpText': latest.current.zoomHelp.mac,
            'CooperativeGesturesHandler.MobileHelpText': latest.current.zoomHelp.mobile,
          },
        })
        created.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-left')
        map.current = created
        const here = () => {
          const c = created!.getCenter()
          return { lat: round(c.lat), lng: round(c.lng) }
        }
        const drawArea = () => {
          const source = created!.getSource('area') as GeoJSONSource | undefined
          source?.setData(circle(here(), latest.current.radiusKm))
        }
        created.on('load', () => {
          created!.addSource('area', { type: 'geojson', data: circle(here(), latest.current.radiusKm) })
          created!.addLayer({ id: 'area-fill', type: 'fill', source: 'area', paint: { 'fill-color': '#22379b', 'fill-opacity': 0.08 } })
          created!.addLayer({
            id: 'area-line',
            type: 'line',
            source: 'area',
            paint: { 'line-color': '#22379b', 'line-width': 2, 'line-dasharray': [2, 2] },
          })
        })
        created.on('movestart', () => setMoving(true))
        created.on('move', drawArea)
        created.on('moveend', (event) => {
          setMoving(false)
          // Only moves the person made (or "my location") choose the spot, not the first view.
          if (event.originalEvent || (event as { chosen?: boolean }).chosen) latest.current.onChange(here())
        })
        created.on('error', (event) => {
          // A missing tile is fine; a map that can't draw at all isn't.
          if (!created!.loaded() && /webgl/i.test(String(event.error?.message))) setFailed(true)
        })
      } catch {
        if (!cancelled) setFailed(true)
      }
    })()
    return () => {
      cancelled = true
      created?.remove()
      map.current = null
    }
  }, [])

  // Redraw the delivery area when the radius changes.
  useEffect(() => {
    const source = map.current?.getSource('area') as GeoJSONSource | undefined
    if (map.current && source) {
      const c = map.current.getCenter()
      source.setData(circle({ lat: c.lat, lng: c.lng }, radiusKm))
    }
  }, [radiusKm])

  const useMyLocation = () => {
    if (!navigator.geolocation) return
    setLocating(true)
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocating(false)
        const spot = { lat: round(position.coords.latitude), lng: round(position.coords.longitude) }
        if (map.current) map.current.flyTo({ center: [spot.lng, spot.lat], zoom: 16 }, { chosen: true })
        else {
          setTyped({ lat: String(spot.lat), lng: String(spot.lng) })
          onChange(spot)
        }
      },
      () => setLocating(false),
      { enableHighAccuracy: true, timeout: 10000 },
    )
  }

  return (
    <div className="location-picker">
      {failed ? (
        <div className="coords">
          <p className="help">{t('mapUnavailable')}</p>
          <div className="form-grid">
            {(['lat', 'lng'] as const).map((axis) => (
              <label key={axis}>
                {t(axis === 'lat' ? 'latitude' : 'longitude')}
                <input
                  className="text-input"
                  dir="ltr"
                  inputMode="decimal"
                  value={typed[axis]}
                  onChange={(e) => {
                    const next = { ...typed, [axis]: e.target.value }
                    setTyped(next)
                    const lat = Number(next.lat)
                    const lng = Number(next.lng)
                    if (next.lat.trim() && next.lng.trim() && Number.isFinite(lat) && Number.isFinite(lng)) {
                      onChange({ lat, lng })
                    }
                  }}
                />
              </label>
            ))}
          </div>
        </div>
      ) : (
        <div className="map-frame">
          <div ref={container} className="map" aria-label={t('storeLocation')} role="application" />
          <span className={`map-pin ${moving ? 'lifted' : ''}`} aria-hidden="true">
            <MapPin size={40} weight="fill" />
          </span>
          {!value && <p className="map-hint">{t('mapHint')}</p>}
        </div>
      )}
      <div className="location-row">
        <button type="button" className="secondary small-button" onClick={useMyLocation} disabled={locating}>
          <Crosshair size={18} weight="light" aria-hidden="true" />
          {t('useMyLocation')}
        </button>
        {value && (
          <span className="muted small" dir="ltr">
            {value.lat.toFixed(5)}, {value.lng.toFixed(5)}
          </span>
        )}
      </div>
    </div>
  )
}
