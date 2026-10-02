export interface ProfileMaterialItem {
  id: string
  kind: 'submitted_result' | 'footage'
  title: string
  source_label: string
  recorded_at: string | null
  date_label: 'Submitted' | 'Published'
  result: { value: number; unit: string } | null
  source_url: string | null
  thumbnail_url?: string | null
  can_include: boolean
  availability: 'recorded' | 'processing' | 'unavailable' | 'unchecked'
}

export interface ProfileMaterialsSnapshot {
  owner_scope?: string | null
  state: 'ready' | 'unlinked' | 'source_unavailable'
  items: ProfileMaterialItem[]
  limitations: string[]
  fetched_at: string
}

const record = (value: unknown): value is Record<string, unknown> => !!value && typeof value === 'object' && !Array.isArray(value)
const text = (value: unknown, max: number): value is string => typeof value === 'string' && value.length <= max && !/[\u0000-\u001f\u007f]/.test(value)

// Only stored, public film posters from the documented delivery namespaces.
// No URL rewriting, image proxy, arbitrary host or fallback media fetch.
export function isProfileThumbnail(value: unknown): value is string {
  if (typeof value !== 'string' || value.length > 2048 || /[^\x21-\x7e]|[\\%?#]/.test(value)) return false
  const cdn = /^https:\/\/cdn\.gmtm\.com\/(?:videos\/film\/thumbnails\/|videos\/events\/([1-9][0-9]*)\/edited-thumbnails\/|users\/([1-9][0-9]*)\/uploads\/)([^/]+)$/.exec(value)
  // GMTM's users/undefined upload keys are never requested (2026-10-02 live smoke); the poster placeholder shows.
  const youtube = /^https:\/\/i\.ytimg\.com\/vi\/[A-Za-z0-9_-]{11}\/([^/]+)$/.exec(value)
  const file = cdn?.[3] || youtube?.[1]
  return !!file && /^[A-Za-z0-9_-][A-Za-z0-9_.-]*\.(?:png|jpg|jpeg|webp)$/i.test(file)
    && (!cdn || [cdn[1], cdn[2]].every(id => !id || Number.isSafeInteger(Number(id))))
}

function sourceDate(value: unknown): value is string {
  if (!text(value, 40) || !/^\d{4}-\d{2}-\d{2}(?:[T ](?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})?)?$/.test(value)) return false
  const day = value.slice(0, 10)
  const calendar = new Date(`${day}T00:00:00Z`)
  return Number.isFinite(calendar.getTime()) && calendar.toISOString().slice(0, 10) === day
    && Number.isFinite(Date.parse(value.length === 10 ? value : /(?:Z|[+-]\d{2}:\d{2})$/.test(value) ? value : `${value.replace(' ', 'T')}Z`))
}

export function readProfileMaterials(value: unknown): ProfileMaterialsSnapshot {
  const invalid = () => new Error('These profile materials could not be confirmed.')
  if (!record(value) || !['ready', 'unlinked', 'source_unavailable'].includes(String(value.state))
    || !(value.owner_scope === undefined || value.owner_scope === null || typeof value.owner_scope === 'string' && /^[a-f0-9]{64}$/.test(value.owner_scope))
    || !sourceDate(value.fetched_at) || !/(?:Z|\+00:00)$/.test(value.fetched_at)
    || !Array.isArray(value.items) || value.items.length > 30
    || !Array.isArray(value.limitations) || value.limitations.length > 20
    || !value.limitations.every(item => text(item, 2000))
    || (value.state !== 'ready' && value.items.length !== 0)) throw invalid()
  const ids = new Set<string>()
  let results = 0, footage = 0
  const items: ProfileMaterialItem[] = value.items.map(item => {
    if (!record(item) || !text(item.id, 120) || !item.id.trim() || ids.has(item.id)
      || !['submitted_result', 'footage'].includes(String(item.kind))
      || !text(item.title, 300) || !item.title.trim() || !text(item.source_label, 400) || !item.source_label.trim()
      || !(item.recorded_at === null || sourceDate(item.recorded_at))
      || !['Submitted', 'Published'].includes(String(item.date_label))
      || typeof item.can_include !== 'boolean'
      || !['recorded', 'processing', 'unavailable', 'unchecked'].includes(String(item.availability))
      || !(item.source_url === null || typeof item.source_url === 'string' && /^https:\/\/gmtm\.com\/film\/[1-9][0-9]{0,15}$/.test(item.source_url))) throw invalid()
    if (item.result !== null && (!record(item.result) || typeof item.result.value !== 'number'
      || !Number.isFinite(item.result.value) || !text(item.result.unit, 40) || !item.result.unit.trim())) throw invalid()
    if (item.kind === 'submitted_result') {
      results += 1
      if (item.result === null || item.date_label !== 'Submitted' || item.source_url !== null || item.availability !== 'recorded') throw invalid()
    } else {
      footage += 1
      if (item.result !== null || item.date_label !== 'Published' || item.availability === 'recorded') throw invalid()
    }
    if (item.can_include && (item.availability === 'processing' || item.availability === 'unavailable'
      || item.kind === 'footage' && item.source_url === null)) throw invalid()
    const thumbnail = item.thumbnail_url ?? null
    if (thumbnail !== null && (!isProfileThumbnail(thumbnail) || item.kind !== 'footage'
      || !item.can_include || item.availability !== 'unchecked' || item.source_url === null)) throw invalid()
    ids.add(item.id)
    return { id: item.id, kind: item.kind, title: item.title, source_label: item.source_label,
      recorded_at: item.recorded_at, date_label: item.date_label, result: item.result,
      source_url: item.source_url, thumbnail_url: thumbnail, can_include: item.can_include, availability: item.availability } as ProfileMaterialItem
  })
  if (results > 20 || footage > 10) throw invalid()
  return { state: value.state as ProfileMaterialsSnapshot['state'], owner_scope: value.owner_scope as string | null | undefined, items,
    limitations: [...value.limitations], fetched_at: value.fetched_at }
}
