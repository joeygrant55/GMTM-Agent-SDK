import type { Metadata } from 'next'
import { LegalPage } from '../legal/LegalPage'

export const metadata: Metadata = {
  title: 'Terms of Service — SPARQ Agent',
  description: 'The terms that govern use of SPARQ Agent.',
}

export default function TermsPage() {
  return (
    <LegalPage title="Terms of Service" updated="July 7, 2026">
      <section>
        <p>
          These terms govern your use of SPARQ Agent (&quot;SPARQ,&quot; &quot;we,&quot; &quot;us&quot;).
          By creating an account or using the service you agree to them. If you are under 18, a parent or
          guardian must review and agree to these terms on your behalf.
        </p>
      </section>

      <section>
        <h2>What SPARQ is</h2>
        <p>
          SPARQ is an AI-powered recruiting assistant for student-athletes, focused on flag football. It
          provides performance benchmarking (including data captured at SPARQ testing events), honest
          assessments, college program matching, and coach outreach drafted by AI and sent only with your
          approval.
        </p>
      </section>

      <section>
        <h2>Eligibility</h2>
        <ul>
          <li>You must be at least 13 to create an account.</li>
          <li>If you are under 18, you confirm a parent or guardian has consented to your use of SPARQ.</li>
          <li>Athletic testing of athletes under 18 at SPARQ events requires parent/guardian consent at
              registration.</li>
        </ul>
      </section>

      <section>
        <h2>Important limits — please read</h2>
        <ul>
          <li>
            <strong>No recruiting outcomes are guaranteed.</strong> SPARQ provides information and tools.
            We do not and cannot promise scholarships, roster spots, coach responses, or team selections.
          </li>
          <li>
            <strong>AI can be wrong.</strong> Assessments, matches, and drafted messages are generated with
            AI and may contain errors or outdated information. Verify important facts (program status,
            coach names, deadlines, eligibility rules) before acting on them.
          </li>
          <li>
            <strong>You are responsible for compliance</strong> with the rules of your school, league, state
            association, and governing bodies (including NCAA, NAIA, and NFHS rules) as they apply to you.
            SPARQ is not an agent, and using SPARQ does not affect amateur status determinations, which are
            made by governing bodies, not by us.
          </li>
        </ul>
      </section>

      <section>
        <h2>Outreach sent on your behalf</h2>
        <p>
          When you approve an outreach draft, you authorize SPARQ to send that message to the recipient you
          approved, with replies directed to your email address. You are responsible for the content of
          messages you approve. Don&apos;t approve messages that are false, harassing, or violate recruiting
          rules that apply to you.
        </p>
      </section>

      <section>
        <h2>Accounts and acceptable use</h2>
        <ul>
          <li>Keep your login credentials private; you are responsible for activity on your account.</li>
          <li>Provide accurate information — fabricated stats undermine your own recruiting and violate
              these terms.</li>
          <li>No scraping, reverse engineering, reselling of SPARQ data, impersonation, or interference
              with the service.</li>
        </ul>
      </section>

      <section>
        <h2>Subscriptions and club programs</h2>
        <ul>
          <li>Free features are provided as-is and may change.</li>
          <li>Paid subscriptions (when offered) renew automatically until canceled; you can cancel anytime,
              effective at the end of the billing period. Pricing is shown before you pay — no sales calls,
              no long-term contracts.</li>
          <li>If your access is provided through a club or school program, that organization controls the
              duration of your access under its agreement with us.</li>
        </ul>
      </section>

      <section>
        <h2>Your content and our service</h2>
        <p>
          You own the information you submit. You grant us a license to use it to operate and improve the
          service as described in our <a href="/privacy">Privacy Policy</a>. The SPARQ software, brand,
          datasets, and benchmarks are our property; these terms don&apos;t transfer any rights in them.
        </p>
      </section>

      <section>
        <h2>Disclaimers and liability</h2>
        <p>
          The service is provided &quot;as is&quot; without warranties of any kind. To the maximum extent
          permitted by law, SPARQ&apos;s total liability for claims arising from the service is limited to
          the amount you paid us in the twelve months before the claim. We are not liable for indirect,
          incidental, or consequential damages.
        </p>
      </section>

      <section>
        <h2>Termination, changes, and contact</h2>
        <p>
          You can stop using SPARQ and request account deletion at any time. We may suspend accounts that
          violate these terms. We may update these terms; material changes will be posted here with a new
          &quot;last updated&quot; date, and continued use after changes constitutes acceptance. These terms
          are governed by the laws of the State of Delaware. Questions:{' '}
          <a href="mailto:hello@sparqagent.ai">hello@sparqagent.ai</a>.
        </p>
      </section>
    </LegalPage>
  )
}
