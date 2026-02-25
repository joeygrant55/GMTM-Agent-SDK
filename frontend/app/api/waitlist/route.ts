import { NextRequest, NextResponse } from 'next/server'

/**
 * POST /api/waitlist
 * Captures upgrade intent from Quick Scan page.
 * Sends a notification to Joey and a confirmation to the athlete.
 */
export async function POST(req: NextRequest) {
  try {
    const { email, tier, athleteName, position } = await req.json()

    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      return NextResponse.json({ error: 'Valid email required' }, { status: 400 })
    }

    const RESEND_API_KEY = process.env.RESEND_API_KEY
    if (!RESEND_API_KEY) {
      // Silently succeed if not configured (dev environment)
      console.warn('[WAITLIST] RESEND_API_KEY not set — skipping email')
      return NextResponse.json({ success: true })
    }

    const tierLabel = tier === 'starter' ? 'Starter ($29.99)'
      : tier === 'pro' ? 'Pro ($49)'
      : tier === 'elite' ? 'Elite ($79.99)'
      : 'Starter ($29.99)'

    const timestamp = new Date().toLocaleString('en-US', { timeZone: 'America/New_York' })

    // 1. Notify Joey
    await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${RESEND_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        from: 'Sammy <sammy@send.slateworks.io>',
        to: 'joey@slateworks.io',
        subject: `🏈 SPARQ upgrade intent — ${email}`,
        html: `
          <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto;">
            <h2 style="color: #CDDC39; margin: 0 0 16px;">New SPARQ Upgrade Intent</h2>
            <table style="border-collapse: collapse; width: 100%;">
              <tr><td style="padding: 8px 0; color: #999; width: 120px;">Email</td><td style="padding: 8px 0; font-weight: bold; color: #fff;">${email}</td></tr>
              <tr><td style="padding: 8px 0; color: #999;">Tier Interest</td><td style="padding: 8px 0; color: #CDDC39; font-weight: bold;">${tierLabel}</td></tr>
              ${athleteName ? `<tr><td style="padding: 8px 0; color: #999;">Athlete</td><td style="padding: 8px 0; color: #fff;">${athleteName}</td></tr>` : ''}
              ${position ? `<tr><td style="padding: 8px 0; color: #999;">Position</td><td style="padding: 8px 0; color: #fff;">${position}</td></tr>` : ''}
              <tr><td style="padding: 8px 0; color: #999;">Time (ET)</td><td style="padding: 8px 0; color: #fff;">${timestamp}</td></tr>
            </table>
            <p style="color: #666; font-size: 13px; margin-top: 24px;">
              This athlete hit "Get My Full Report" on the Quick Scan page and left their email. 
              When Stripe is live, they'll be first to convert.
            </p>
          </div>
        `,
      }),
    })

    // 2. Send confirmation to athlete
    await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${RESEND_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        from: 'SPARQ <sammy@send.slateworks.io>',
        to: email,
        subject: 'You\'re on the SPARQ list 🏈',
        html: `
          <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto; background: #141414; color: #fff; padding: 32px; border-radius: 12px;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 24px;">
              <div style="width: 40px; height: 40px; background: #CDDC39; border-radius: 8px; display: flex; align-items: center; justify-content: center;">
                <span style="color: #141414; font-weight: 900; font-size: 18px;">S</span>
              </div>
              <span style="font-size: 20px; font-weight: 900;">SPARQ</span>
            </div>
            
            <h2 style="color: #CDDC39; margin: 0 0 12px; font-size: 22px;">You're on the list.</h2>
            
            <p style="color: #ccc; line-height: 1.6; margin: 0 0 16px;">
              We're putting the finishing touches on SPARQ ${tierLabel} and you'll be the first to know when it's ready.
            </p>
            
            <p style="color: #ccc; line-height: 1.6; margin: 0 0 24px;">
              What you'll get:
            </p>
            
            <ul style="color: #ccc; padding-left: 20px; margin: 0 0 24px; line-height: 2;">
              <li>Your top college matches — ranked by fit, not just name recognition</li>
              <li>Coaching staff research and contact info</li>
              <li>A personalized outreach plan with draft emails</li>
              <li>Depth chart analysis: where you'd actually fit</li>
            </ul>
            
            <p style="color: #666; font-size: 13px; margin: 0;">
              In the meantime, your Quick Scan is still live at 
              <a href="https://sparq-agent.vercel.app/quick-scan" style="color: #CDDC39;">sparq-agent.vercel.app/quick-scan</a>
            </p>
          </div>
        `,
      }),
    })

    return NextResponse.json({ success: true })
  } catch (err) {
    console.error('[WAITLIST] Error:', err)
    return NextResponse.json({ error: 'Failed to process request' }, { status: 500 })
  }
}
