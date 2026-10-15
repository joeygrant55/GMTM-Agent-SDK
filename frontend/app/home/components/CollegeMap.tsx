'use client'

// Interactive colleges map (Joey 2026-10-15, option A): drag, pinch or +/- to zoom, tap a state circle
// to zoom in, tap a dot to pick a school. Same bundled US outline and server map positions as before:
// no map tiles or outside map service, so nobody else sees where she lives. Keyboard and screen reader
// users get the same schools from the list next to the map; the dots are pointer-only shortcuts.
import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'

export interface MapProgram { id: string; school: string; state: string; map: { x: number; y: number } | null; saved: boolean; sent_at: string | null }
type Point = { x: number; y: number }
type View = { k: number; tx: number; ty: number }

const focus = 'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-jr-lime'
const ASPECT = 1.6 // the outline is 960 x 600
// 300 miles in the outline's units: 300 / 3958.8 mi (earth radius) x 1261.4 (projection scale) = 95.6 of 960.
// ponytail: one radius for the whole map; the equal-area projection stretches it a few percent at the edges.
const RING = 95.6 / 960
const CLUSTER_BELOW = 900 // map width in px: under this, schools group into one circle per state
const LABEL_FROM = 1800 // map width in px: from this, saved and picked schools show their name

const short = (school: string) => {
  const t = school.replace(/ (University|College|Community College)$/, '')
  return t.length > 18 ? `${t.slice(0, 17)}…` : t
}

export function CollegeMap({ programs, origin, selected, onSelect, onView, zoomTo, children }: {
  programs: MapProgram[]; origin: Point | null; selected: string | null
  onSelect: (id: string | null) => void
  onView: (visible: string[]) => void
  zoomTo: { id: string; at: number } | null
  children?: ReactNode
}) {
  const box = useRef<HTMLDivElement>(null)
  const [size, setSize] = useState({ w: 0, h: 0 })
  const [view, setView] = useState<View | null>(null)
  const [preset, setPreset] = useState<'near' | 'region' | 'all' | null>(origin ? 'region' : 'all')
  const pointers = useRef(new Map<number, Point>())
  const gesture = useRef<{ view: View; a: Point; b?: Point; f: number } | null>(null)
  const moved = useRef(false)

  useEffect(() => {
    const el = box.current
    if (!el) return
    const observer = new ResizeObserver(([entry]) => setSize({ w: entry.contentRect.width, h: entry.contentRect.height }))
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  const { w, h } = size
  const center = useCallback((p: Point, k: number): View => ({ k, tx: w / 2 - (p.x / 100) * w * k, ty: h / 2 - (p.y / 100) * (w / ASPECT) * k }), [w, h])
  const fitAll = useCallback((): View => center({ x: 50, y: 50 }, Math.min(1, (h * ASPECT) / w)), [center, w, h])
  // Near me: the 300-mile ring fills most of the map. My region: about 1.8 times wider (dots on desktop, state circles on a phone).
  const nearK = useCallback(() => (0.85 * Math.min(w, h)) / (2 * RING * w), [w, h])
  const go = useCallback((which: 'near' | 'region' | 'all') => {
    setPreset(which)
    setView(which === 'all' || !origin ? fitAll() : center(origin, which === 'near' ? nearK() : nearK() / 1.8))
  }, [origin, fitAll, center, nearK])

  // First size: open on her part of the country (or the whole US without a city). A new size (a phone
  // turned sideways) fits the same choice again, so the map never sits half off the screen.
  const fitted = useRef('')
  useEffect(() => {
    if (!w || !h || fitted.current === `${w}x${h}`) return
    fitted.current = `${w}x${h}`
    go(preset || (origin ? 'region' : 'all'))
  }, [w, h, preset, origin, go])

  const zoomAt = useCallback((p: Point, k: number) => {
    setPreset(null)
    setView(center(p, Math.max(fitAll().k, Math.min(40, k))))
  }, [center, fitAll])
  const mapPoint = useCallback((sx: number, sy: number, v: View): Point => ({ x: ((sx - v.tx) / (w * v.k)) * 100, y: ((sy - v.ty) / ((w / ASPECT) * v.k)) * 100 }), [w])
  const zoomBy = useCallback((factor: number, at?: Point) => {
    if (!view) return
    const screen = at || { x: w / 2, y: h / 2 }
    const p = mapPoint(screen.x, screen.y, view)
    const k = Math.max(fitAll().k, Math.min(40, view.k * factor))
    setPreset(null)
    // Keep the point under the finger (or the center) still.
    setView({ k, tx: screen.x - (p.x / 100) * w * k, ty: screen.y - (p.y / 100) * (w / ASPECT) * k })
  }, [view, w, h, mapPoint, fitAll])

  // The list asked for a school: zoom to it.
  useEffect(() => {
    const p = zoomTo && programs.find(item => item.id === zoomTo.id)
    if (p?.map && view) zoomAt(p.map, Math.max(view.k, 2400 / w))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [zoomTo])

  // Trackpad pinch (ctrl + wheel) zooms; a plain wheel still scrolls the page.
  useEffect(() => {
    const el = box.current
    if (!el) return
    const wheel = (e: WheelEvent) => {
      if (!e.ctrlKey) return
      e.preventDefault()
      const r = el.getBoundingClientRect()
      zoomBy(Math.exp(-e.deltaY / 100), { x: e.clientX - r.left, y: e.clientY - r.top })
    }
    el.addEventListener('wheel', wheel, { passive: false })
    return () => el.removeEventListener('wheel', wheel)
  }, [zoomBy])

  const local = (e: React.PointerEvent) => { const r = box.current!.getBoundingClientRect(); return { x: e.clientX - r.left, y: e.clientY - r.top } }
  const start = () => {
    const [a, b] = Array.from(pointers.current.values())
    gesture.current = view ? { view, a, b, f: b ? Math.hypot(a.x - b.x, a.y - b.y) : 0 } : null
  }
  const down = (e: React.PointerEvent) => {
    pointers.current.set(e.pointerId, local(e))
    if (pointers.current.size === 1) moved.current = false
    start()
  }
  const move = (e: React.PointerEvent) => {
    if (!pointers.current.has(e.pointerId) || !gesture.current) return
    pointers.current.set(e.pointerId, local(e))
    const g = gesture.current
    const [a, b] = Array.from(pointers.current.values())
    if (b && g.b) {
      // Pinch: zoom about the midpoint, and follow the midpoint as it moves.
      const mid0 = { x: (g.a.x + g.b.x) / 2, y: (g.a.y + g.b.y) / 2 }, mid = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }
      const k = Math.max(fitAll().k, Math.min(40, g.view.k * (Math.hypot(a.x - b.x, a.y - b.y) / (g.f || 1))))
      const p = mapPoint(mid0.x, mid0.y, g.view)
      moved.current = true
      setPreset(null)
      setView({ k, tx: mid.x - (p.x / 100) * w * k, ty: mid.y - (p.y / 100) * (w / ASPECT) * k })
      return
    }
    const dx = a.x - g.a.x, dy = a.y - g.a.y
    if (!moved.current && Math.abs(dx) + Math.abs(dy) < 6) return
    moved.current = true
    setPreset(null)
    setView({ ...g.view, tx: g.view.tx + dx, ty: g.view.ty + dy })
  }
  const up = (e: React.PointerEvent) => {
    pointers.current.delete(e.pointerId)
    if (pointers.current.size) start(); else gesture.current = null
  }
  const tap = (fn: () => void) => () => { if (!moved.current) fn() }

  const v = view
  const mw = v ? w * v.k : 0
  const at = (p: Point) => ({ x: v!.tx + (p.x / 100) * mw, y: v!.ty + (p.y / 100) * (mw / ASPECT) })
  const inside = (s: Point, pad = 0) => s.x >= -pad && s.x <= w + pad && s.y >= -pad && s.y <= h + pad
  const placed = programs.filter(p => p.map)
  const visible = v ? placed.filter(p => inside(at(p.map!))).map(p => p.id) : []
  const visibleKey = visible.join(',')
  const ready = !!v
  useEffect(() => { if (ready) onView(visibleKey ? visibleKey.split(',') : []) }, [visibleKey, ready, onView])

  const clustered = mw < CLUSTER_BELOW
  // Names for the picked school, then saved and emailed ones; a name that would touch another is left off.
  const named = new Set<string>()
  if (v && !clustered) {
    const boxes: Array<{ x: number; y: number; w: number }> = []
    const want = placed.filter(p => selected === p.id || ((p.saved || p.sent_at) && mw >= LABEL_FROM))
      .sort((a, b) => Number(b.id === selected) - Number(a.id === selected))
    for (const p of want) {
      const s = at(p.map!), box = { x: s.x + 12, y: s.y - 8, w: short(p.school).length * 6.4 + 14 }
      if (inside(s) && !boxes.some(o => box.x < o.x + o.w && o.x < box.x + box.w && Math.abs(box.y - o.y) < 16)) { boxes.push(box); named.add(p.id) }
    }
  }
  const states = clustered ? Object.values(placed.reduce<Record<string, MapProgram[]>>((all, p) => ((all[p.state] ||= []).push(p), all), {})) : []
  const chip = (on: boolean) => `min-h-11 rounded-xl border px-3 text-sm font-semibold sm:px-4 ${focus} ${on ? 'border-jr-lime bg-jr-done text-jr-lime' : 'border-jr-edge text-jr-text hover:border-jr-muted'}`

  return <div className="flex flex-col gap-3">
    <div role="group" aria-label="How far from home" className="grid grid-cols-3 gap-2 sm:flex">
      <button type="button" disabled={!origin} aria-pressed={preset === 'near'} onClick={() => go('near')} className={`${chip(preset === 'near')} disabled:opacity-40`}>Near me</button>
      <button type="button" disabled={!origin} aria-pressed={preset === 'region'} onClick={() => go('region')} className={`${chip(preset === 'region')} disabled:opacity-40`}>My region</button>
      <button type="button" aria-pressed={preset === 'all'} onClick={() => go('all')} className={chip(preset === 'all')}>Anywhere</button>
    </div>
    <div ref={box} role="group" aria-label="Map of college programs. Every school on the map is also in the list."
      onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={up} onPointerLeave={up}
      onDoubleClick={e => { const r = box.current!.getBoundingClientRect(); zoomBy(1.8, { x: e.clientX - r.left, y: e.clientY - r.top }) }}
      className="relative h-[420px] w-full touch-none select-none overflow-hidden rounded-[20px] border border-jr-line bg-[#0F1418] lg:h-[560px]">
      {v && <>
        <img src="/us-states.svg" alt="" aria-hidden="true" draggable={false} className="pointer-events-none absolute max-w-none"
          style={{ left: v.tx, top: v.ty, width: mw, height: mw / ASPECT }} />
        {origin && (() => {
          const o = at(origin), r = RING * mw
          return <div aria-hidden="true" className="pointer-events-none">
            <span className="absolute rounded-full border border-dashed border-jr-lime/60 bg-jr-lime/[0.06]" style={{ left: o.x - r, top: o.y - r, width: 2 * r, height: 2 * r }} />
            <span className="absolute z-30 h-3.5 w-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-jr-text shadow-[0_0_0_4px_rgba(244,244,245,0.25)]" style={{ left: o.x, top: o.y }} />
          </div>
        })()}
        <div aria-hidden="true">
          {clustered ? states.map(group => {
            const c = { x: group.reduce((s, p) => s + p.map!.x, 0) / group.length, y: group.reduce((s, p) => s + p.map!.y, 0) / group.length }
            const s = at(c), d = Math.round(24 + Math.min(group.length, 18) * 1.3)
            const mine = group.some(p => p.saved || p.sent_at)
            return inside(s, d) && <button key={group[0].state} type="button" tabIndex={-1} onClick={tap(() => zoomAt(c, 2400 / w))}
              className={`absolute z-10 flex -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border-2 border-jr-ground text-xs font-bold ${mine ? 'bg-jr-lime text-jr-ground' : 'bg-[#2A2F36] text-jr-text'}`}
              style={{ left: s.x, top: s.y, width: d, height: d }}>{group.length}</button>
          }) : placed.map(p => {
            const s = at(p.map!)
            if (!inside(s, 40)) return null
            const mine = p.saved || !!p.sent_at, on = selected === p.id
            const size = on ? 18 : mine ? 13 : 10
            return <button key={p.id} type="button" tabIndex={-1} onClick={tap(() => onSelect(p.id))}
              className={`absolute flex h-11 w-11 -translate-x-1/2 -translate-y-1/2 items-center justify-center ${on ? 'z-30' : mine ? 'z-20' : 'z-10'}`} style={{ left: s.x, top: s.y }}>
              <span className={`block rounded-full border-2 ${on ? 'border-jr-text' : mine ? 'border-jr-lime' : 'border-jr-dim'} ${mine ? 'bg-jr-lime' : 'bg-jr-ground'} ${p.sent_at ? 'shadow-[0_0_0_3px_#1B2410]' : ''}`} style={{ width: size, height: size }} />
              {named.has(p.id) && <span className="absolute left-8 top-3 whitespace-nowrap text-[11px] font-semibold text-jr-lime [text-shadow:0_1px_2px_#000]">{short(p.school)}{p.sent_at ? ' ✓' : ''}</span>}
            </button>
          })}
        </div>
      </>}
      <div className="absolute right-2.5 top-2.5 z-40 flex flex-col gap-1.5">
        <button type="button" aria-label="Zoom in" onClick={() => zoomBy(1.6)} className={`h-11 w-11 rounded-xl border border-jr-edge bg-jr-card text-xl font-semibold text-jr-text ${focus}`}>+</button>
        <button type="button" aria-label="Zoom out" onClick={() => zoomBy(1 / 1.6)} className={`h-11 w-11 rounded-xl border border-jr-edge bg-jr-card text-xl font-semibold text-jr-text ${focus}`}>−</button>
      </div>
      <p aria-hidden="true" className="absolute left-2.5 top-2.5 z-40 rounded-full bg-jr-ground/85 px-3 py-1.5 text-xs text-jr-soft">
        {clustered ? 'Tap a circle to zoom in' : 'Drag to move · Tap a dot'}
      </p>
      {children}
    </div>
    <p className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-jr-muted" aria-hidden="true">
      {origin && <span><span className="mr-1.5 inline-block h-2.5 w-2.5 rounded-full bg-jr-text" />You</span>}
      <span><span className="mr-1.5 inline-block h-2.5 w-2.5 rounded-full bg-jr-lime" />Saved or emailed</span>
      {origin && <span><span className="mr-1.5 inline-block h-2.5 w-2.5 rounded-full border border-dashed border-jr-lime" />300 miles</span>}
    </p>
  </div>
}
