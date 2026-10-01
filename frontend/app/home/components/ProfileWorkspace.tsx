'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { useUser } from '@clerk/nextjs'
import Link from 'next/link'
import { apiFetch } from '@/app/_lib/api'
import { evidenceDate, evidenceValue, prepareProfileDraft, ProfileDraftKind, ProfileEvidence, readProfileEvidence } from './profileEvidence'
import ProfileMaterialsPanel, { useProfileMaterials } from './ProfileMaterialsPanel'
import { addMaterialsToDraft, ProfileMaterialItem } from './profileMaterials'
import AthleteDebriefPanel from './AthleteDebriefPanel'
import AthleteCareerHome from './AthleteCareerHome'
import AthleteOpportunities from './AthleteOpportunities'
import { AthleteOpportunity, isOpportunityCurrent } from './opportunityEvidence'
import { CareerDraft, CareerGoal, CareerWorkspace, useCareerWorkspace, workLabels } from './careerWorkspace'
import { useCareerNavigation } from './ProfileWorkspaceShell'
import { useFindColleges } from './ProfileColleges'
import { useRouter } from 'next/navigation'

const focus = 'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-sparq-lime'
const secondary = `inline-flex min-h-11 items-center justify-center rounded-xl border border-white/20 px-4 py-2 text-sm font-semibold transition-colors hover:border-white/40 disabled:cursor-wait disabled:opacity-50 ${focus}`
const field = `mt-2 block w-full min-w-0 rounded-xl border border-white/15 bg-white/[0.03] px-4 py-3 text-sm leading-relaxed text-white placeholder:text-gray-400 focus:border-sparq-lime focus:outline-none`
const primary = `inline-flex min-h-12 items-center justify-center rounded-xl bg-sparq-lime px-6 py-3 text-sm font-bold text-sparq-charcoal transition-colors hover:bg-sparq-lime-light disabled:cursor-not-allowed disabled:opacity-40 ${focus}`

export default function ProfileWorkspace() {
  const { user, isLoaded } = useUser()
  if (!isLoaded) return <p role="status" className="mx-auto max-w-6xl px-5 py-16 text-gray-300">Loading your account…</p>
  if (!user?.id) return <div className="mx-auto max-w-6xl px-5 py-16"><h1 className="text-3xl font-bold">Your profile is private.</h1><p className="mt-3 text-gray-300">Sign in to see your own athlete evidence.</p><Link href="/sign-in" className={`${secondary} mt-6`}>Sign in</Link></div>
  return <ProfileSession key={user.id} />
}

type EditorState = Omit<CareerDraft, 'text'> & { text: string | null }
const emptyEditor = (): EditorState => ({ kind: 'summary', text: null, goal: '', destination: '', selected_evidence_ids: [], selected_material_ids: [], inputs_changed: false })
const draftSignature = (draft: EditorState | CareerDraft | null | undefined) => draft ? JSON.stringify([draft.kind, draft.text, draft.goal, draft.destination, draft.selected_evidence_ids, draft.selected_material_ids, draft.inputs_changed]) : null

function ProfileSession() {
  const [profile, setProfile] = useState<ProfileEvidence | null>(null)
  const [version, setVersion] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<{ title: string; detail: string; scope?: boolean } | null>(null)
  const active = useRef<AbortController | null>(null)
  const mounted = useRef(false)
  const [editor, setEditorState] = useState<EditorState>(emptyEditor)
  const editorTouched = useRef(false)
  const setEditor = useCallback((next: React.SetStateAction<EditorState>) => {
    editorTouched.current = true
    setEditorState(next)
  }, [])
  const hydrated = useRef<string | null>(null)
  const [reviewOpen, setReviewOpen] = useState(false)
  const reviewDialog = useRef<HTMLDialogElement>(null)

  const refresh = useCallback(async () => {
    if (!mounted.current || active.current) return
    const controller = new AbortController()
    active.current = controller
    setLoading(true)
    setProfile(null)
    setError(null)
    const timer = window.setTimeout(() => {
      controller.abort()
      if (mounted.current && active.current === controller) {
        active.current = null
        setProfile(null)
        setLoading(false)
        setError({ title: 'Your profile took too long to load.', detail: 'Please try again. No profile evidence has been changed.' })
      }
    }, 30000)
    controller.signal.addEventListener('abort', () => window.clearTimeout(timer), { once: true })
    try {
      const response = await apiFetch('/api/athlete/evidence', { signal: controller.signal, cache: 'no-store' })
      if (!mounted.current || controller.signal.aborted) return
      if (!response.ok) {
        const messages: Record<number, { title: string; detail: string }> = {
          401: { title: 'Please sign in again.', detail: 'Your session could not be confirmed. Sign in to load your private profile.' },
          403: { title: 'This profile is not available to this account.', detail: 'We could not confirm permission to show this athlete’s evidence.' },
          409: { title: 'Your profile connection needs review.', detail: 'We found a conflicting connection. Ask your organizer to review it before continuing.' },
        }
        setProfile(null)
        setError(messages[response.status] ? { ...messages[response.status], scope: true } : { title: 'Your profile is temporarily unavailable.', detail: 'We could not read your GMTM evidence. Try again in a moment.' })
        return
      }
      const data = readProfileEvidence(await response.json())
      if (!mounted.current || controller.signal.aborted) return
      setProfile(data)
      setVersion(value => value + 1)
    } catch {
      if (mounted.current && active.current === controller && !controller.signal.aborted) {
        setProfile(null)
        setError({ title: 'Your profile could not be loaded.', detail: 'We could not confirm the latest evidence. Please try again.' })
      }
    } finally {
      window.clearTimeout(timer)
      if (active.current === controller) {
        active.current = null
        if (mounted.current) setLoading(false)
      }
    }
  }, [])

  const scopeLost = useCallback(() => {
    hydrated.current = null
    editorTouched.current = false
    setEditorState(emptyEditor())
    active.current?.abort(); active.current = null
    setProfile(null); setReviewOpen(false)
    void refresh()
  }, [refresh])
  const workspace = useCareerWorkspace(scopeLost)
  const associationInvalid = !!workspace.snapshot && profile?.state === 'ready' && profile.owner_scope !== workspace.snapshot.owner_scope
  useEffect(() => {
    if (workspace.error?.kind !== 'link' && (associationInvalid || error?.scope || profile?.state === 'unlinked' && workspace.snapshot)) workspace.invalidateScope()
  }, [associationInvalid, error?.scope, profile?.state, workspace.snapshot, workspace.error?.kind, workspace.invalidateScope])
  const refreshAll = async () => {
    if (workspace.loading || workspace.saving) return
    active.current?.abort(); active.current = null
    setProfile(null); setError(null); setLoading(true)
    const confirmed = await workspace.reload()
    if (!mounted.current) return
    if (!confirmed) { setLoading(false); return }
    void refresh()
  }
  useEffect(() => {
    const saved = workspace.snapshot
    if (saved && hydrated.current !== saved.link_revision) {
      hydrated.current = saved.link_revision
      if (!editorTouched.current) setEditorState(saved.draft ? { ...saved.draft } : emptyEditor())
    }
  }, [workspace.snapshot])
  useEffect(() => {
    if (!reviewOpen || !reviewDialog.current) return
    reviewDialog.current.showModal()
    return () => reviewDialog.current?.close()
  }, [reviewOpen])
  const reviewSaved = async () => {
    const latest = await workspace.reload()
    if (latest && mounted.current) setReviewOpen(true)
  }
  const saveDraft = async () => {
    if (editor.text === null) return null
    return workspace.save({ draft: { ...editor, text: editor.text } })
  }
  const removeDraft = async () => {
    const before = editor
    const saved = await workspace.save({ draft: null })
    if (saved && mounted.current) setEditor(current => current === before ? emptyEditor() : current)
  }

  useEffect(() => {
    mounted.current = true
    void refresh()
    return () => { mounted.current = false; active.current?.abort(); active.current = null }
  }, [refresh])

  return (
    <div className="py-6 sm:py-5">
      {workspace.loading && <p role="status" className="mb-4 text-sm text-gray-400">Loading your saved work…</p>}
      {workspace.error && <div role="alert" className="mb-6 flex flex-wrap items-center justify-between gap-3 border-l-2 border-amber-300 bg-white/[0.03] px-4 py-3 text-sm">
        <p>{workspace.error.message}</p>
        <button type="button" disabled={workspace.loading || workspace.saving} onClick={() => void (workspace.snapshot ? reviewSaved() : workspace.reload())} className={secondary}>{workspace.snapshot ? 'Review saved version' : 'Reload saved work'}</button>
      </div>}
      {!workspace.loading && !workspace.error && workspace.snapshot && <p role="status" className="sr-only">Saved work loaded.</p>}
      {loading && !profile && !error && <div role="status" className="py-16"><p className="text-xs uppercase tracking-[0.18em] text-sparq-lime">Your private profile</p><h1 className="mt-4 text-3xl font-bold">Bringing your evidence together…</h1><p className="mt-3 text-gray-400">Reading the details already in your GMTM profile.</p></div>}
      {error && <section role="alert" className="max-w-xl rounded-2xl border border-white/15 p-6 sm:p-8"><h1 className="text-2xl font-bold">{error.title}</h1><p className="mt-3 leading-relaxed text-gray-300">{error.detail}</p><div className="mt-6 flex flex-wrap gap-3"><button type="button" disabled={loading} onClick={() => void refresh()} className={secondary}>{loading ? 'Loading…' : 'Try again'}</button><Link href="/connect" className={secondary}>Check connection</Link>{error.title === 'Please sign in again.' && <Link href="/sign-in" className={secondary}>Sign in</Link>}</div></section>}
      {!error && profile?.state === 'unlinked' && <section className="max-w-xl py-8"><p className="text-xs uppercase tracking-[0.18em] text-sparq-lime">Your private profile</p><h1 className="mt-4 text-3xl font-bold">Bring your GMTM profile with you.</h1><p className="mt-4 leading-relaxed text-gray-300">Your account does not have a confirmed athlete connection yet. Use your organizer’s secure invitation, or check an existing connection.</p><Link href="/connect" className={`${secondary} mt-6`}>Check connection</Link></section>}
      {!error && profile?.state === 'source_unavailable' && <section role="alert" className="max-w-xl py-8"><h1 className="text-3xl font-bold">Your GMTM evidence is unavailable.</h1><p className="mt-4 leading-relaxed text-gray-300">We could not read your source profile. This does not mean your results are missing.</p><button type="button" disabled={loading} onClick={() => void refresh()} className={`${secondary} mt-6`}>{loading ? 'Loading…' : 'Try again'}</button></section>}
      {!error && (!workspace.loading || workspace.snapshot) && workspace.error?.kind !== 'link' && !associationInvalid && profile?.state === 'ready' && <ProfileReadout key={version} profile={profile} refreshing={loading} onRefresh={() => void refreshAll()} workspace={workspace} editor={editor} setEditor={setEditor} onSaveDraft={saveDraft} onRemoveDraft={removeDraft} />}
      {!loading && !error?.scope && workspace.error?.kind !== 'link' && profile?.state !== 'ready' && profile?.state !== 'unlinked' && (workspace.snapshot?.draft || editor.text !== null) && <SavedDraftRecovery editor={editor} setEditor={setEditor} workspace={workspace} onSave={saveDraft} />}
      <dialog ref={reviewDialog} aria-labelledby="saved-review-title" onCancel={() => setReviewOpen(false)} onClose={() => setReviewOpen(false)} className="w-[calc(100%-2rem)] max-w-2xl rounded-2xl border border-white/15 bg-sparq-charcoal-light p-6 text-white backdrop:bg-black/70">
        <h2 id="saved-review-title" className="text-2xl font-semibold">Your saved version</h2>
        <p className="mt-3 text-sm text-gray-400">Your local edits are still here. Compare before choosing what to keep.</p>
        <p className="mt-5 text-sm text-gray-300">{workspace.snapshot?.goal?.text || 'No saved goal.'}</p>
        <pre className="mt-4 max-h-[45dvh] overflow-auto whitespace-pre-wrap break-words rounded-lg bg-black/20 p-4 font-sans text-sm leading-relaxed">{workspace.snapshot?.draft?.text || 'No saved draft.'}</pre>
        <div className="mt-6 flex flex-wrap gap-3">
          <button type="button" autoFocus onClick={() => setReviewOpen(false)} className={primary}>Keep my edits</button>
          <button type="button" onClick={() => { editorTouched.current = false; setEditorState(workspace.snapshot?.draft ? { ...workspace.snapshot.draft } : emptyEditor()); setReviewOpen(false) }} className={secondary}>Use saved draft</button>
        </div>
      </dialog>
    </div>
  )
}

function SavedDraftRecovery({ editor, setEditor, workspace, onSave }: { editor: EditorState; setEditor: React.Dispatch<React.SetStateAction<EditorState>>; workspace: ReturnType<typeof useCareerWorkspace>; onSave: () => Promise<CareerWorkspace | null> }) {
  return <section className="mt-8 max-w-3xl border-t border-white/10 pt-8" aria-labelledby="saved-draft-recovery">
    <h2 id="saved-draft-recovery" className="text-2xl font-semibold">{workspace.snapshot?.draft ? 'Your saved draft is here.' : 'Your draft is here.'}</h2>
    {workspace.snapshot?.goal && <p className="mt-3 text-gray-300">{workspace.snapshot.goal.text}</p>}
    <p className="mt-3 text-sm leading-relaxed text-gray-400">You can keep writing while GMTM is unavailable. The evidence in this draft has not been refreshed.</p>
    <label htmlFor="recovery-draft" className="mt-5 block text-sm">Your saved text</label>
    <textarea id="recovery-draft" rows={12} maxLength={20000} value={editor.text || ''} onChange={event => setEditor(value => ({ ...value, text: event.target.value }))} className={field} />
    <button type="button" disabled={workspace.saving || workspace.blocked || workspace.loading} onClick={() => void onSave()} className={primary + ' mt-4'}>{workspace.saving ? 'Saving…' : 'Save draft'}</button>
    <p role="status" className="mt-3 text-sm text-gray-400">{editor.text === workspace.snapshot?.draft?.text ? 'Saved.' : 'Unsaved changes.'}</p>
  </section>
}

function ProfileReadout({ profile, refreshing, onRefresh, workspace, editor, setEditor, onSaveDraft, onRemoveDraft }: {
  profile: ProfileEvidence; refreshing: boolean; onRefresh: () => void
  workspace: ReturnType<typeof useCareerWorkspace>; editor: EditorState
  setEditor: React.Dispatch<React.SetStateAction<EditorState>>
  onSaveDraft: () => Promise<CareerWorkspace | null>; onRemoveDraft: () => Promise<void>
}) {
  const athlete = profile.athlete!
  const selected = editor.selected_evidence_ids
  const selectedMaterials = editor.selected_material_ids
  const setSelected = (next: string[] | ((previous: string[]) => string[])) => setEditor(value => ({ ...value, selected_evidence_ids: typeof next === 'function' ? next(value.selected_evidence_ids) : next }))
  const setSelectedMaterials = (next: string[] | ((previous: string[]) => string[])) => setEditor(value => ({ ...value, selected_material_ids: typeof next === 'function' ? next(value.selected_material_ids) : next }))
  const materialSource = useProfileMaterials()
  const materialsScopeMismatch = materialSource.scopeInvalid || !!materialSource.snapshot && (
    materialSource.snapshot.state === 'unlinked' ||
    materialSource.snapshot.state === 'ready' && (!profile.owner_scope || materialSource.snapshot.owner_scope !== profile.owner_scope) ||
    materialSource.snapshot.state === 'source_unavailable' && !!materialSource.snapshot.owner_scope && materialSource.snapshot.owner_scope !== profile.owner_scope
  )
  const materials = { ...materialSource, snapshot: materialsScopeMismatch ? null : materialSource.snapshot, error: materialSource.error || materialsScopeMismatch }
  useEffect(() => { if (materialsScopeMismatch) workspace.invalidateScope() }, [materialsScopeMismatch, workspace.invalidateScope])
  const [showAllResults, setShowAllResults] = useState(false)
  const kind = editor.kind, goal = editor.goal, destination = editor.destination, draft = editor.text, inputsChanged = editor.inputs_changed
  const setKind = (kind: ProfileDraftKind) => setEditor(value => ({ ...value, kind }))
  const setGoal = (goal: string) => setEditor(value => ({ ...value, goal }))
  const setDestination = (destination: string) => setEditor(value => ({ ...value, destination }))
  const setDraft = (text: string | null) => setEditor(value => ({ ...value, text }))
  const setInputsChanged = (inputs_changed: boolean) => setEditor(value => ({ ...value, inputs_changed }))
  const { view, setView, revision: navigationRevision } = useCareerNavigation()
  const router = useRouter()
  // Girls first: an eligible athlete's main action is finding colleges.
  const findColleges = useFindColleges()
  const [goalOpen, setGoalOpen] = useState(false)
  const [goalForm, setGoalForm] = useState<CareerGoal>({ text: '', destination: null, timeframe: null })
  const goalDialog = useRef<HTMLDialogElement>(null)
  const navigationAction = useRef<(() => void) | null>(null)
  const [copyStatus, setCopyStatus] = useState('')
  const [copying, setCopying] = useState(false)
  const [composerOpen, setComposerOpen] = useState(false)
  const [guidanceOpen, setGuidanceOpen] = useState(false)
  const [detailsOpen, setDetailsOpen] = useState(true)
  const [profileOpen, setProfileOpen] = useState(false)
  const [debriefVersion, setDebriefVersion] = useState(0)
  const sheet = useRef<HTMLDialogElement>(null)
  const composerHeading = useRef<HTMLHeadingElement>(null)
  const writeButton = useRef<HTMLButtonElement>(null)
  const askButton = useRef<HTMLButtonElement>(null)
  const draftInput = useRef<HTMLTextAreaElement>(null)
  const [pendingOpportunity, setPendingOpportunity] = useState<AthleteOpportunity | null>(null)
  const [opportunityNotice, setOpportunityNotice] = useState('')
  const opportunityDialog = useRef<HTMLDialogElement>(null)
  const lifetime = useRef(false)
  const draftRevision = useRef(0)
  const currentDraft = useRef(draft)
  currentDraft.current = draft
  useEffect(() => { setCopyStatus('') }, [draft])
  useEffect(() => { lifetime.current = true; return () => { lifetime.current = false } }, [])
  useEffect(() => {
    if (!pendingOpportunity || !opportunityDialog.current) return
    const dialog = opportunityDialog.current
    dialog.showModal()
    return () => dialog.close()
  }, [pendingOpportunity])
  const changed = () => { if (draft !== null) setInputsChanged(true); setCopyStatus('') }
  useEffect(() => {
    const dialog = sheet.current
    if (!dialog || !profileOpen) return
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    dialog.showModal()
    return () => { dialog.close(); document.body.style.overflow = previousOverflow }
  }, [profileOpen])
  const openComposer = (nextKind: ProfileDraftKind, question: string) => {
    const open = () => {
      setComposerOpen(true)
      if (kind !== nextKind) { setKind(nextKind); setDestination(''); setDetailsOpen(true); changed() }
      const intent = question || workspace.snapshot?.goal?.text || ''
      if (!goal.trim() && intent.length <= 600) { setGoal(intent); changed() }
      requestAnimationFrame(() => { if (lifetime.current) composerHeading.current?.focus() })
    }
    if (view !== 'home') { navigationAction.current = open; setView('home') } else open()
  }
  const backToSPARQ = () => {
    setComposerOpen(false); setGuidanceOpen(false)
    requestAnimationFrame(() => { if (lifetime.current) document.getElementById('profile-main')?.focus() })
  }
  const featureClip = async (item: ProfileMaterialItem) => {
    if (!item.can_include || item.kind !== 'footage' || !item.source_url || workspace.loading || workspace.saving) return
    await workspace.save({ featured_source_id: item.id })
  }
  const editGoal = () => {
    setGoalForm(workspace.snapshot?.goal ? { ...workspace.snapshot.goal } : { text: '', destination: null, timeframe: null })
    setGoalOpen(true)
  }
  const saveGoal = async () => {
    const next = { text: goalForm.text.trim(), destination: goalForm.destination?.trim() || null, timeframe: goalForm.timeframe?.trim() || null }
    if (!next.text) return
    const saved = await workspace.save({ goal: next })
    if (saved && lifetime.current) setGoalOpen(false)
  }
  const removeGoal = async () => {
    const saved = await workspace.save({ goal: null })
    if (saved && lifetime.current) setGoalOpen(false)
  }
  useEffect(() => {
    if (!goalOpen || !goalDialog.current) return
    goalDialog.current.showModal()
    return () => goalDialog.current?.close()
  }, [goalOpen])
  useEffect(() => {
    setComposerOpen(false); setGuidanceOpen(false); setGoalOpen(false)
    setProfileOpen(view === 'portfolio')
    const pending = navigationAction.current
    navigationAction.current = null
    pending?.()
  }, [navigationRevision, view])
  const closeProfile = () => { setProfileOpen(false); if (view === 'portfolio') setView('home') }
  const showGuidance = () => {
    setGuidanceOpen(true); setComposerOpen(false)
    requestAnimationFrame(() => { if (lifetime.current) {
      const heading = document.getElementById('profile-debrief-title')
      heading?.setAttribute('tabindex', '-1'); heading?.focus()
    } })
  }
  const prepare = () => {
    const includedMaterials = materials.snapshot?.state === 'ready'
      ? materials.snapshot.items.filter(item => item.can_include && selectedMaterials.includes(item.id)) : []
    setDraft(addMaterialsToDraft(prepareProfileDraft(profile, selected, goal, destination, kind), includedMaterials, kind))
    setSelected(value => value.filter(id => profile.evidence.some(item => item.id === id)))
    setSelectedMaterials(includedMaterials.map(item => item.id))
    draftRevision.current += 1
    setInputsChanged(false)
    setDetailsOpen(false)
    setCopyStatus('')
    requestAnimationFrame(() => { if (lifetime.current) draftInput.current?.focus() })
  }
  const copy = async () => {
    if (draft === null || !draft.trim() || copying) return
    const revision = draftRevision.current
    const copyingText = draft
    setCopying(true)
    setCopyStatus('')
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable')
      await navigator.clipboard.writeText(draft)
      if (lifetime.current && revision === draftRevision.current && copyingText === currentDraft.current) setCopyStatus('Copied to clipboard. Nothing has been sent.')
    } catch {
      if (lifetime.current && revision === draftRevision.current && copyingText === currentDraft.current) setCopyStatus('Clipboard access is unavailable. Select the text below and copy it manually.')
    } finally { if (lifetime.current) setCopying(false) }
  }
  const savedGoal = workspace.snapshot?.goal || null
  const savedDestination = savedGoal?.destination?.trim() || ''
  const hasDraft = draft !== null
  const nextPending = !hasDraft && !!savedGoal && materials.loading
  const eligibleFeature = materials.snapshot?.state === 'ready' ? materials.snapshot.items.find(item => item.id === workspace.snapshot?.featured_source_id && item.can_include && item.kind === 'footage' && item.source_url) : undefined
  const nextMove = hasDraft
    ? { title: 'Pick up where you left off.', detail: 'Your words are here. Keep shaping them for your next opportunity.', label: 'Continue my draft' }
    : !savedGoal
      ? { title: 'Choose your next chapter.', detail: 'Set a goal so your next move has a purpose.', label: 'Set my goal' }
      : savedDestination
        ? { title: 'Make your introduction count.', detail: 'Use your selected work to introduce yourself to the recipient you chose.', label: 'Prepare introduction' }
        : { title: 'Put your work to use.', detail: 'Turn your selected footage and results into an athlete summary.', label: 'Create my summary' }
  const takeNextMove = () => {
    if (workspace.loading || workspace.saving || nextPending) return
    if (hasDraft) { setDetailsOpen(false); openComposer(kind, ''); return }
    if (!savedGoal) { editGoal(); return }
    setEditor(value => {
      // An existing buffer always wins, including deliberately erased text.
      if (value.text !== null) return value
      const nextKind = savedDestination ? 'introduction' : 'summary'
      const nextDestination = savedDestination
      const requestedMaterials = new Set(value.selected_material_ids)
      if (eligibleFeature) requestedMaterials.add(eligibleFeature.id)
      const includedMaterials = materials.snapshot?.state === 'ready'
        ? materials.snapshot.items.filter(item => item.can_include && requestedMaterials.has(item.id)) : []
      const selectedEvidence = value.selected_evidence_ids.filter(id => profile.evidence.some(item => item.id === id))
      return { ...value, kind: nextKind, goal: savedGoal.text, destination: nextDestination,
        selected_evidence_ids: selectedEvidence, selected_material_ids: includedMaterials.map(item => item.id),
        text: addMaterialsToDraft(prepareProfileDraft(profile, selectedEvidence, savedGoal.text, nextDestination, nextKind), includedMaterials, nextKind),
        inputs_changed: false }
    })
    draftRevision.current += 1
    setCopyStatus(''); setDetailsOpen(false); setComposerOpen(true)
    requestAnimationFrame(() => { if (lifetime.current) draftInput.current?.focus() })
  }
  const savedDraft = workspace.snapshot?.draft
  const draftDirty = draft !== null && draftSignature(editor) !== draftSignature(savedDraft)
  const sourceIds = new Set([ ...profile.evidence.map(item => item.id), ...(materials.snapshot?.state === 'ready' ? materials.snapshot.items.filter(item => item.can_include).map(item => item.id) : []) ])
  const staleSelections = [...selected, ...selectedMaterials].some(id => !sourceIds.has(id))
  const removeUnavailableSelections = () => {
    setSelected(value => value.filter(id => sourceIds.has(id)))
    setSelectedMaterials(value => value.filter(id => sourceIds.has(id)))
    changed()
  }
  const identity = [athlete.sport, athlete.position, athlete.school, athlete.graduation_year === null ? null : `Class of ${athlete.graduation_year}`].filter(Boolean)

  const selectedCount = selected.length + selectedMaterials.length
  const profileContext = [athlete.sport, athlete.position].filter(Boolean).join(' · ')
  const includedClips = materials.snapshot?.items.filter(item => item.kind === 'footage' && selectedMaterials.includes(item.id)) || []

  const prepareOpportunity = (item: AthleteOpportunity, replace = false) => {
    if (workspace.blocked || !workspace.snapshot
        || workspace.snapshot.owner_scope !== profile.owner_scope) return
    if (workspace.loading || workspace.saving || materials.loading) {
      setOpportunityNotice('Your profile is still loading or saving. Try preparing the introduction again in a moment.')
      return
    }
    if (!isOpportunityCurrent(item) || item.action.kind !== 'prepare_introduction' || !item.action.recipient || !item.action.purpose) {
      setPendingOpportunity(null)
      setOpportunityNotice('This source needs a fresh review. Find opportunities again before preparing an introduction.')
      return
    }
    if (editor.text !== null && !replace) { setPendingOpportunity(item); return }
    const purpose = item.action.purpose
    const intent = savedGoal?.text || editor.goal.trim() || 'Explore adult flag football opportunities.'
    const pickedEvidence = editor.selected_evidence_ids.filter(id => profile.evidence.some(fact => fact.id === id))
    const requestedMaterials = new Set(editor.selected_material_ids)
    if (eligibleFeature) requestedMaterials.add(eligibleFeature.id)
    const pickedMaterials = materials.snapshot?.state === 'ready' ? materials.snapshot.items.filter(material => material.can_include && requestedMaterials.has(material.id)) : []
    const base = prepareProfileDraft(profile, pickedEvidence, intent, item.action.recipient, 'introduction')
      .replace('\n\nThank you for your time.', `\n\n${purpose}\n\nThank you for your time.`)
    const text = addMaterialsToDraft(base, pickedMaterials, 'introduction')
    setEditor({ kind: 'introduction', text, goal: intent, destination: item.action.recipient,
      selected_evidence_ids: pickedEvidence, selected_material_ids: pickedMaterials.map(material => material.id), inputs_changed: false })
    setPendingOpportunity(null); setOpportunityNotice(''); setCopyStatus(''); setDetailsOpen(false)
    draftRevision.current += 1
    navigationAction.current = () => {
      setComposerOpen(true)
      requestAnimationFrame(() => { if (lifetime.current) draftInput.current?.focus() })
    }
    setView('home')
  }

  if (materialsScopeMismatch) return <p role="status" className="py-12 text-gray-300">Checking your profile connection…</p>

  return (
    <>
      <div hidden={view !== 'home' && view !== 'portfolio'}>
      <div hidden={composerOpen || guidanceOpen}>
        <AthleteCareerHome profile={profile} snapshot={materials.snapshot} loading={materials.loading} error={materials.error}
          goal={savedGoal} featuredId={workspace.snapshot?.featured_source_id || null} saving={workspace.saving || workspace.loading}
          nextMove={findColleges ? { title: 'Find colleges.', detail: 'See college flag football programs near you and why each one could fit.', label: 'Find colleges' } : nextMove}
          nextPending={findColleges ? false : nextPending} recent={workspace.snapshot?.recent_work || []}
          onNext={findColleges ? () => router.push('/home/colleges') : takeNextMove} onEditGoal={editGoal} onFeature={item => void featureClip(item)}
          onAsk={showGuidance} onBrowse={() => setProfileOpen(true)} onProgress={() => setView('progress')} />
      </div>
      <div className={`mx-auto w-full pb-12 ${composerOpen || guidanceOpen ? 'max-w-3xl pt-8 sm:pt-12' : ''}`}>
        <div hidden={composerOpen || !guidanceOpen}>
          <button ref={askButton} type="button" onClick={() => { setGuidanceOpen(false); requestAnimationFrame(() => { if (lifetime.current) document.getElementById('profile-main')?.focus() }) }} className={`mb-6 min-h-11 text-sm text-gray-400 hover:text-white ${focus}`}>Back to your content</button>
          <button type="button" onClick={() => setProfileOpen(true)} aria-haspopup="dialog" className={secondary + ' mb-6 ml-4'}>View profile</button>
          <AthleteDebriefPanel key={debriefVersion} onPrepare={openComposer} expectedOwnerScope={profile.owner_scope || undefined} onScopeMismatch={workspace.invalidateScope} />
          <div className="mt-6 border-t border-white/10 pt-4">
            <button ref={writeButton} type="button" onClick={() => openComposer(draft === null ? 'introduction' : kind, '')} className={`min-h-11 text-sm text-gray-400 hover:text-white ${focus}`}>{draft === null ? 'Write an introduction' : 'Return to your draft'}</button>
          </div>
        </div>

        <section hidden={!composerOpen} aria-labelledby="profile-output-title">
          <button type="button" onClick={backToSPARQ} className={`mb-6 min-h-11 text-sm text-gray-400 hover:text-white ${focus}`}>Back to SPARQ</button>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sparq-lime">{kind === 'introduction' ? 'Your introduction' : 'Your profile summary'}</p>
          <h2 ref={composerHeading} tabIndex={-1} id="profile-output-title" className="mt-3 text-3xl font-semibold tracking-[-0.035em] outline-none sm:text-5xl">{draft === null ? 'Make the first move.' : 'Make it yours.'}</h2>
          <p className="mt-3 text-sm leading-relaxed text-gray-400">{draft === null ? 'Choose your details. Add your goal. Find your words.' : 'Edit your text, then copy it when you’re ready.'}</p>
          <div className="my-6 flex flex-wrap items-center gap-x-5 gap-y-2 border-y border-white/10 py-3">
            <button type="button" aria-haspopup="dialog" onClick={() => setProfileOpen(true)} className={`inline-flex min-h-11 items-center gap-3 text-sm text-gray-200 ${focus}`}>Choose profile details<span className="rounded-full bg-white/10 px-2.5 py-1 text-xs tabular-nums" aria-label={`${selectedCount} selected`}>{selectedCount}</span></button>
            {draft !== null && <button type="button" aria-expanded={detailsOpen} aria-controls="profile-draft-details" onClick={() => setDetailsOpen(value => !value)} className={`min-h-11 text-sm text-gray-400 hover:text-white ${focus}`}>{detailsOpen ? 'Hide details' : 'Edit details'}</button>}
          </div>
          {includedClips.length > 0 && <div aria-label="Selected footage" className="mb-6 flex flex-wrap gap-2">{includedClips.map(item => <span key={item.id} className="inline-flex max-w-full items-center gap-2 rounded-lg bg-white/[0.04] px-3 py-2 text-xs text-gray-300"><span className="text-sparq-lime">Selected footage</span><span className="min-w-0 break-words">{item.title}</span></span>)}</div>}
          <form id="profile-draft-details" hidden={!detailsOpen} onSubmit={event => { event.preventDefault(); prepare() }}>
            <fieldset><legend className="sr-only">Output format</legend><div className="flex flex-wrap gap-2">{(['summary', 'introduction'] as const).map(value => <label key={value} className="cursor-pointer"><input type="radio" name="profile-output-format" value={value} checked={kind === value} onChange={() => { setKind(value); setDestination(''); changed() }} className="peer sr-only" /><span className="inline-flex min-h-11 items-center rounded-full border border-white/15 px-4 text-sm text-gray-400 transition-colors peer-checked:border-white/40 peer-checked:bg-white/[0.06] peer-checked:text-white peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-4 peer-focus-visible:outline-sparq-lime">{value === 'summary' ? 'Profile summary' : 'Introduction'}</span></label>)}</div></fieldset>
            <label htmlFor="profile-goal" className="mt-6 block text-sm font-medium">What are you working toward?</label><textarea id="profile-goal" value={goal} onChange={event => { setGoal(event.target.value); changed() }} maxLength={600} rows={2} required className={field} placeholder="Your next goal, in your own words" />
            <label htmlFor="profile-destination" className="mt-5 block text-sm font-medium">{kind === 'introduction' ? 'Who is this for?' : 'Intended use (optional)'}</label><input id="profile-destination" value={destination} onChange={event => { setDestination(event.target.value); changed() }} maxLength={200} required={kind === 'introduction'} className={field} placeholder={kind === 'introduction' ? 'A coach or organization you have in mind' : 'Where you plan to use this summary'} />
            <p className="mt-3 text-xs leading-relaxed text-gray-400">{selectedCount ? `${selectedCount} selected ${selectedCount === 1 ? 'record' : 'records'}, plus your profile and goal.` : 'Using your profile and goal. Add recorded results above if you want.'}</p>
            {draft !== null && <p className="mt-3 text-xs text-amber-200">Rebuilding replaces your edits.</p>}
            <button type="submit" disabled={!goal.trim() || (kind === 'introduction' && !destination.trim())} className={`${primary} my-6 w-full sm:w-auto`}>{draft === null ? 'Prepare my text' : 'Rebuild from these details'}</button>
          </form>

          {draft !== null && <div>
            <label htmlFor="profile-draft" className="sr-only">Your text — ready to edit</label>
            {inputsChanged && <p role="status" className="mb-3 text-xs leading-relaxed text-amber-200">Your selections changed. Rebuild to include them, or keep editing this version.</p>}
            <textarea id="profile-draft" ref={draftInput} value={draft} onChange={event => { setDraft(event.target.value); draftRevision.current += 1; setCopyStatus('') }} maxLength={20000} rows={12} className={`${field} resize-y p-5 leading-7 sm:p-6`} />
            <div className="mt-5 flex flex-wrap items-center gap-3"><button type="button" disabled={copying || !draft.trim()} onClick={() => void copy()} className={primary}>{copying ? 'Copying…' : 'Copy text'}</button><button type="button" onClick={() => { draftInput.current?.focus(); draftInput.current?.select(); setCopyStatus('Text selected. Use your device’s copy command.') }} className={`min-h-11 px-3 text-sm text-gray-400 hover:text-white ${focus}`}>Select all text</button></div>
            <p role="status" aria-live="polite" className="mt-3 text-xs leading-relaxed text-gray-300">{copyStatus}</p>
          </div>}
          {draft !== null && <div className="mt-6 border-t border-white/10 pt-5">
            <div className="flex flex-wrap items-center gap-3">
              <button type="button" disabled={workspace.saving || workspace.loading || workspace.blocked || !draftDirty} onClick={() => void onSaveDraft()} className={secondary}>{workspace.saving ? 'Saving…' : 'Save draft'}</button>
              {savedDraft && <button type="button" disabled={workspace.saving || workspace.loading || workspace.blocked} onClick={() => void onRemoveDraft()} className={`min-h-11 text-sm text-gray-400 hover:text-white ${focus}`}>Remove saved draft</button>}
            </div>
            <p role="status" className="mt-3 text-sm text-gray-400">{draftDirty ? 'Unsaved changes. Save to continue next time.' : 'Saved. You can come back to this draft.'}</p>
          </div>}
          {staleSelections && <p role="status" className="mt-4 text-sm text-amber-200">Some selected sources are unavailable in the current view. Your draft is preserved; review its details before using it.</p>}
          <p className="mt-6 text-xs leading-relaxed text-gray-400">Saving keeps this private. Copying does not send it.</p>
        </section>
      </div>
      </div>

      <div hidden={view !== 'opportunities'}>
        {workspace.snapshot && !workspace.blocked && <AthleteOpportunities ownerScope={workspace.snapshot.owner_scope}
          linkRevision={workspace.snapshot.link_revision} goal={savedGoal?.text || null} active={view === 'opportunities'}
          onPrepare={item => prepareOpportunity(item)} onScopeLost={workspace.invalidateScope} />}
        {(!workspace.snapshot || workspace.blocked) && <p role="status" className="py-12 text-gray-300">Reload your saved work to confirm your profile before finding opportunities.</p>}
        {opportunityNotice && <p role="status" className="mb-8 text-sm text-amber-200">{opportunityNotice}</p>}
      </div>
      <dialog ref={opportunityDialog} aria-labelledby="opportunity-draft-title" onCancel={() => setPendingOpportunity(null)} onClose={() => setPendingOpportunity(null)} className="w-[calc(100%-2rem)] max-w-lg rounded-2xl border border-white/15 bg-sparq-charcoal-light p-6 text-white backdrop:bg-black/70 sm:p-8">
        <h2 id="opportunity-draft-title" className="text-2xl font-semibold">Keep your current draft?</h2>
        <p className="mt-4 text-sm leading-relaxed text-gray-300">You already have text in progress. Preparing this introduction replaces the text in your editor. Your saved version stays unchanged until you save.</p>
        <div className="mt-6 flex flex-wrap gap-3">
          <button type="button" autoFocus onClick={() => setPendingOpportunity(null)} className={secondary}>Keep my draft</button>
          <button type="button" disabled={workspace.loading || workspace.saving || workspace.blocked || materials.loading} onClick={() => { if (pendingOpportunity) prepareOpportunity(pendingOpportunity, true) }} className={primary}>Replace with introduction</button>
        </div>
      </dialog>
      <section hidden={view !== 'progress'} className="max-w-3xl py-8 sm:py-16" aria-labelledby="career-progress">
        <p className="text-xs uppercase tracking-[0.18em] text-sparq-lime">Your progress</p>
        <h1 id="career-progress" className="mt-4 text-3xl font-semibold tracking-tight sm:text-5xl">Recent work</h1>
        <p className="mt-4 text-base text-gray-400">The steps you have saved in SPARQ.</p>
        {workspace.snapshot?.recent_work.length ? <ol className="mt-8 divide-y divide-white/10">{workspace.snapshot.recent_work.map(item => <li key={item.id} className="flex flex-wrap justify-between gap-3 py-5"><span className="font-medium">{workLabels[item.kind]}</span><time dateTime={item.at} className="text-sm text-gray-400">{evidenceDate(item.at)}</time></li>)}</ol> : <p className="mt-8 text-gray-300">{workspace.loading ? 'Loading your recent work…' : workspace.error ? 'Recent work is unavailable.' : 'Your saved steps will appear here.'}</p>}
        <button type="button" onClick={() => setView('home')} className={secondary + ' mt-6'}>Back to my home</button>
      </section>

      <dialog ref={goalDialog} aria-labelledby="career-goal-editor-title" onCancel={() => setGoalOpen(false)} onClose={() => setGoalOpen(false)} className="w-[calc(100%-2rem)] max-w-xl rounded-2xl border border-white/15 bg-sparq-charcoal-light p-6 text-white backdrop:bg-black/70 sm:p-8">
        <form onSubmit={event => { event.preventDefault(); void saveGoal() }}>
          <h2 id="career-goal-editor-title" className="text-2xl font-semibold">Your next goal</h2>
          <label htmlFor="career-goal" className="mt-6 block text-sm font-medium">What are you working toward?</label>
          <textarea autoFocus id="career-goal" disabled={workspace.saving} rows={3} required maxLength={600} value={goalForm.text} onChange={event => setGoalForm(value => ({ ...value, text: event.target.value }))} className={field} placeholder="Your next chapter, in your own words" />
          <label htmlFor="career-recipient" className="mt-5 block text-sm">Recipient or program (optional)</label>
          <input id="career-recipient" disabled={workspace.saving} maxLength={200} value={goalForm.destination || ''} onChange={event => setGoalForm(value => ({ ...value, destination: event.target.value || null }))} className={field} />
          <label htmlFor="career-timeframe" className="mt-5 block text-sm">Timeframe (optional)</label>
          <input id="career-timeframe" disabled={workspace.saving} maxLength={100} value={goalForm.timeframe || ''} onChange={event => setGoalForm(value => ({ ...value, timeframe: event.target.value || null }))} className={field} />
          <div className="mt-6 flex flex-wrap gap-3">
            <button type="submit" disabled={!goalForm.text.trim() || workspace.saving || workspace.loading || workspace.blocked} className={primary}>{workspace.saving ? 'Saving…' : 'Save goal'}</button>
            <button type="button" onClick={() => setGoalOpen(false)} className={secondary}>Cancel</button>
            {savedGoal && <button type="button" disabled={workspace.saving || workspace.loading || workspace.blocked} onClick={() => void removeGoal()} className={`min-h-11 text-sm text-gray-400 ${focus}`}>Remove goal</button>}
          </div>
          {workspace.error && <p role="alert" className="mt-4 text-sm text-amber-200">{workspace.error.message} Close this editor to review your saved version.</p>}
          {draft !== null && <p className="mt-4 text-xs text-gray-400">Your existing draft keeps its words and original goal.</p>}
        </form>
      </dialog>

      <dialog ref={sheet} aria-labelledby="profile-sheet-title" onCancel={closeProfile} onClose={closeProfile} className="fixed inset-y-0 left-auto right-0 m-0 ml-auto h-[100dvh] max-h-none w-full max-w-[540px] border-0 bg-sparq-charcoal-light p-0 text-white backdrop:bg-black/70">
        <div className="sticky top-0 z-10 flex items-center justify-between gap-4 border-b border-white/10 bg-sparq-charcoal-light px-5 py-4 sm:px-8">
          <h2 id="profile-sheet-title" className="text-lg font-semibold">Your profile</h2>
          <button type="button" autoFocus onClick={closeProfile} className={secondary}>Done</button>
        </div>
        <div className="px-5 py-6 sm:px-8">
          <p className="break-words text-2xl font-semibold tracking-tight">{athlete.name || 'Your athlete profile'}</p>
          {identity.length > 0 && <p className="mt-2 break-words text-sm leading-relaxed text-gray-300">{identity.join(' · ')}</p>}
          {(athlete.city || athlete.state) && <p className="mt-1 text-sm text-gray-400">{[athlete.city, athlete.state].filter(Boolean).join(', ')}</p>}
          <section aria-labelledby="profile-evidence-title" className="mt-8">
            <h3 id="profile-evidence-title" className="text-lg font-semibold">What your profile records</h3>
            {staleSelections && <div className="mt-4 border-l-2 border-amber-200 pl-4"><p className="text-sm text-gray-400">Some saved selections are unavailable in this view. Your draft keeps its words.</p><button type="button" onClick={removeUnavailableSelections} className={secondary + ' mt-3'}>Remove unavailable selections</button></div>}
            <p className="mt-2 text-sm leading-relaxed text-gray-400">{profile.evidence.length ? 'Select details to include in your text.' : 'No numeric performance results were returned with this profile.'}</p>
            {profile.evidence.length > 0 && <fieldset className="mt-4"><legend className="sr-only">Evidence to include</legend><div className="divide-y divide-white/10">{(showAllResults ? profile.evidence : profile.evidence.slice(0, 3)).map(item => <label key={item.id} className="flex cursor-pointer items-start gap-4 py-5"><input type="checkbox" checked={selected.includes(item.id)} onChange={event => { setSelected(value => event.target.checked ? [...value, item.id] : value.filter(id => id !== item.id)); changed() }} className={`mt-1 h-5 w-5 shrink-0 accent-sparq-lime ${focus}`} /><span className="min-w-0 flex-1"><span className="block break-words text-sm font-medium text-gray-300">{item.label}</span><span className="mt-1 block break-words text-2xl font-semibold tabular-nums">{evidenceValue(item)}</span><span className="mt-2 block break-words text-xs leading-relaxed text-gray-400">{item.source_label} · {evidenceDate(item.recorded_at)}{item.event_name ? ` · ${item.event_name}` : ''}</span></span><span className="sr-only">Include {item.label}</span></label>)}</div>{profile.evidence.length > 3 && <button type="button" aria-expanded={showAllResults} onClick={() => setShowAllResults(value => !value)} className={`${secondary} mt-3`}>{showAllResults ? 'Show fewer results' : `Show all ${profile.evidence.length} results`}</button>}<p className="mt-3 text-xs leading-relaxed text-gray-400">Recorded results; measurement verification is unconfirmed.</p></fieldset>}
            <details className="my-5"><summary className={`min-h-11 cursor-pointer py-3 text-sm text-gray-400 ${focus}`}>Sources &amp; limitations</summary><p className="text-xs leading-relaxed text-gray-400">Profile read {evidenceDate(profile.fetched_at)}. Recorded results do not confirm eligibility, selection or a coach’s interest.</p>{profile.observations.map((observation, index) => <p key={index} className="mt-3 text-xs leading-relaxed text-gray-400">{observation.detail}</p>)}{profile.limitations.length > 0 && <ul className="mt-3 list-disc space-y-2 pl-4 text-xs leading-relaxed text-gray-400">{profile.limitations.map((limit, index) => <li key={index}>{limit}</li>)}</ul>}<a href="https://gmtm.com" className={`mt-3 inline-flex min-h-11 items-center text-sm text-gray-300 underline underline-offset-4 ${focus}`}>Open GMTM for your profile and submissions</a></details>
          </section>
          <ProfileMaterialsPanel snapshot={materials.snapshot} loading={materials.loading} error={materials.error} selected={selectedMaterials}
            onToggle={(item, checked) => { setSelectedMaterials(value => checked ? [...value, item.id] : value.filter(id => id !== item.id)); changed() }}
            onRetry={() => { setSelectedMaterials([]); setDebriefVersion(value => value + 1); void materials.reload() }} />
          <div className="mt-8 border-t border-white/10 pt-6">
            <button type="button" onClick={() => { closeProfile(); openComposer(draft === null ? 'introduction' : kind, '') }} className={secondary}>{draft === null ? 'Write an introduction' : 'Return to your draft'}</button>
            {workspace.snapshot?.featured_source_id && <button type="button" disabled={workspace.saving || workspace.blocked} onClick={() => void workspace.save({ featured_source_id: null })} className={secondary + ' mt-3'}>Remove featured footage</button>}
            <p className="mb-3 mt-5 text-xs leading-relaxed text-gray-400">Refresh source details. Your goal and draft stay here.</p>
            <button type="button" disabled={refreshing} onClick={onRefresh} className={secondary}>{refreshing ? 'Refreshing…' : 'Refresh profile'}</button>
          </div>
        </div>
      </dialog>
    </>
  )
}
