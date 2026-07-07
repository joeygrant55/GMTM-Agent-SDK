import type { Metadata } from 'next'
import { LegalPage } from '../legal/LegalPage'

export const metadata: Metadata = {
  title: 'Privacy Policy — SPARQ Agent',
  description: 'How SPARQ collects, uses, and protects athlete data, including performance data captured at SPARQ testing events.',
}

export default function PrivacyPage() {
  return (
    <LegalPage title="Privacy Policy" updated="July 7, 2026">
      <section>
        <p>
          SPARQ Agent (&quot;SPARQ,&quot; &quot;we,&quot; &quot;us&quot;) helps student-athletes navigate
          athletic recruiting, with a focus on flag football. Because our users include minors and our
          product involves athletic performance data, we hold ourselves to a high standard on privacy.
          This policy explains what we collect, how we use it, and the choices you and your family have.
        </p>
      </section>

      <section>
        <h2>Who this covers</h2>
        <ul>
          <li><strong>Athletes</strong> who create SPARQ accounts (must be 13 or older).</li>
          <li><strong>Parents and guardians</strong> acting on behalf of athletes under 18.</li>
          <li><strong>Athletes tested at SPARQ testing events</strong> run with clubs, leagues, or schools.</li>
          <li><strong>Coaches and club staff</strong> using SPARQ team features.</li>
        </ul>
        <p>
          <strong>Children under 13:</strong> SPARQ accounts are not available to children under 13. We do
          not knowingly collect personal information from children under 13 except with verifiable parental
          consent collected at event registration, consistent with the Children&apos;s Online Privacy
          Protection Act (COPPA). If you believe a child under 13 has provided us information without
          consent, contact us and we will delete it.
        </p>
      </section>

      <section>
        <h2>What we collect</h2>
        <h3>Information you provide</h3>
        <ul>
          <li>Account details: name, email, graduation year, school or club, position, state.</li>
          <li>Recruiting profile: GPA, academic interests, recruiting goals, highlight links.</li>
          <li>Self-reported athletic stats and combine metrics.</li>
          <li>Messages you exchange with the SPARQ AI assistant.</li>
        </ul>
        <h3>Performance data captured at SPARQ testing events</h3>
        <ul>
          <li>
            Measured athletic performance (for example: sprint times, agility times, jump measurements,
            height and weight) captured by SPARQ devices or event staff, tagged with the event, date, and
            capturing device.
          </li>
          <li>
            <strong>Consent:</strong> for athletes under 18, we require parent/guardian consent at event
            registration before capturing or storing testing data. Consent can be withdrawn at any time
            (see &quot;Your choices&quot; below).
          </li>
        </ul>
        <h3>Information from other sources</h3>
        <ul>
          <li>Publicly available athletic stats (for example, MaxPreps profiles you connect).</li>
          <li>Selection and recruiting outcomes (for example, national-team trial invitations or college
              commitments) reported by governing bodies, clubs, or the athlete.</li>
        </ul>
      </section>

      <section>
        <h2>How we use it</h2>
        <ul>
          <li>To generate assessments, college matches, and recruiting guidance for the athlete.</li>
          <li>To draft and — only with the athlete&apos;s explicit approval — send outreach to college coaches.</li>
          <li>To benchmark performance against aggregate, de-identified historical data.</li>
          <li>To improve our matching and assessment models. Model improvement uses aggregated or
              de-identified data; we do not sell personal information.</li>
          <li>To operate, secure, and support the service.</li>
        </ul>
        <p>
          <strong>We do not sell personal information.</strong> We do not serve third-party advertising, and
          we do not use athlete data for advertising to minors.
        </p>
      </section>

      <section>
        <h2>When we share</h2>
        <ul>
          <li><strong>At your direction:</strong> when an athlete approves outreach to a college coach, the
              message and relevant profile details go to that coach. Public share links you create show the
              content you chose to share.</li>
          <li><strong>Your club or team:</strong> if you joined SPARQ through a club program, your club&apos;s
              coaches can see your testing results and recruiting progress for team purposes.</li>
          <li><strong>Service providers</strong> that run our infrastructure: authentication (Clerk), hosting
              (Vercel, Railway), email delivery (SendGrid), and AI processing (Anthropic). Each receives only
              what it needs to provide its service.</li>
          <li><strong>Legal requirements:</strong> if required by law or to protect the safety of our users.</li>
        </ul>
      </section>

      <section>
        <h2>Your choices</h2>
        <ul>
          <li><strong>Access and correction:</strong> you can view and edit profile data in the app.</li>
          <li><strong>Deletion:</strong> email us to delete an account and associated personal data.
              Parents/guardians of athletes under 18 may request deletion of their child&apos;s data.</li>
          <li><strong>Consent withdrawal:</strong> parents/guardians may withdraw event-testing consent at any
              time; we will stop capturing new data and, on request, delete previously captured data.</li>
          <li><strong>Email:</strong> transactional emails are required for the service; marketing email is
              opt-out via the unsubscribe link.</li>
        </ul>
      </section>

      <section>
        <h2>Retention and security</h2>
        <p>
          We retain personal data while an account is active and delete or de-identify it after deletion
          requests, subject to legal obligations. Data is encrypted in transit; access is restricted to
          authenticated users and authorized personnel. No system is perfectly secure — if a breach affects
          your data, we will notify you as required by law.
        </p>
      </section>

      <section>
        <h2>Changes and contact</h2>
        <p>
          We will post updates to this policy here and, for material changes affecting minors&apos; data,
          notify account holders by email. Questions or requests:{' '}
          <a href="mailto:hello@sparqagent.ai">hello@sparqagent.ai</a>.
        </p>
      </section>
    </LegalPage>
  )
}
