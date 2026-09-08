import { CombineActivity } from './currentCombine'

const fieldTypes = new Map([
  ['video', 'Video'], ['metric', 'Measurement or count'], ['essay', 'Written response'],
  ['phone', 'Phone number'], ['email', 'Email address'], ['gender_id', 'Form selection'],
  ['date', 'Date'], ['address', 'Address'], ['height', 'Height'],
])

export default function ActivityRequirements({ activity }: { activity: CombineActivity }) {
  const fields = activity.required_fields
  const dashCaption = activity.event_id === 1318 && activity.task_id === 4907
    && fields?.some(field => field.title === '40 Yard Dash Time')
  return (
    <div role="group" aria-label="What you’ll submit" className="my-3 min-w-0 rounded-lg bg-white/[0.04] p-3 text-sm">
      <p className="font-semibold">What you’ll submit</p>
      {fields && fields.length > 0 ? (
        <ul className="mt-2 space-y-2">
          {fields.map((field, index) => (
            <li key={`${field.type}:${field.title}:${index}`} className="min-w-0 break-words">
              <span className="block text-xs text-gray-400">{fieldTypes.get(field.type) ?? 'Format unconfirmed'}</span>
              <span className="text-gray-200">{field.title}</span>
            </li>
          ))}
        </ul>
      ) : <p className="mt-2 text-gray-300">Field requirements could not be confirmed here. Review the organizer’s form in GMTM.</p>}
      {dashCaption && <p className="mt-3 text-amber-200">This is the 20-yard dash. The form’s “40 Yard Dash Time” label is a known mismatch; enter your 20-yard result in that field.</p>}
      <p className="mt-3 text-xs text-gray-400">These are the organizer’s required fields, not a confirmation of saved progress or eligibility.</p>
    </div>
  )
}
