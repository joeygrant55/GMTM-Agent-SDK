import { ImageResponse } from 'next/og'
import { NextRequest } from 'next/server'

export const runtime = 'edge'

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url)

  const name = searchParams.get('name') || 'Athlete Name'
  const sport = searchParams.get('sport') || 'Football'
  const position = searchParams.get('position') || 'ATH'
  const rating = searchParams.get('rating') || '—'
  const stat1 = searchParams.get('stat1') || ''
  const stat2 = searchParams.get('stat2') || ''
  const stat3 = searchParams.get('stat3') || ''
  const stat4 = searchParams.get('stat4') || ''
  const match = searchParams.get('match') || ''
  const size = searchParams.get('size') || 'og'

  const width = size === 'square' ? 1080 : 1200
  const height = size === 'square' ? 1080 : 630

  const isSquare = size === 'square'
  const stats = [stat1, stat2, stat3, stat4].filter(Boolean)
  const initials = name.split(' ').map((w: string) => w[0]).join('').slice(0, 2).toUpperCase()

  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: '#000000',
          fontFamily: 'Inter, sans-serif',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {/* Background gradient effects */}
        <div
          style={{
            position: 'absolute',
            top: '-100px',
            right: '-100px',
            width: '500px',
            height: '500px',
            borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(200,255,0,0.08) 0%, transparent 70%)',
            display: 'flex',
          }}
        />
        <div
          style={{
            position: 'absolute',
            bottom: '-150px',
            left: '-100px',
            width: '400px',
            height: '400px',
            borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(200,255,0,0.05) 0%, transparent 70%)',
            display: 'flex',
          }}
        />

        {/* Main content */}
        <div
          style={{
            display: 'flex',
            flexDirection: isSquare ? 'column' : 'row',
            alignItems: isSquare ? 'center' : 'flex-start',
            padding: isSquare ? '60px 50px' : '50px 60px',
            flex: 1,
            gap: isSquare ? '30px' : '50px',
          }}
        >
          {/* Left / Top section */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              flex: 1,
              justifyContent: 'center',
              alignItems: isSquare ? 'center' : 'flex-start',
            }}
          >
            {/* Sport + Position badge */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                marginBottom: '16px',
              }}
            >
              <div
                style={{
                  padding: '6px 16px',
                  backgroundColor: 'rgba(200,255,0,0.12)',
                  borderRadius: '100px',
                  border: '1px solid rgba(200,255,0,0.25)',
                  color: '#c8ff00',
                  fontSize: '16px',
                  fontWeight: 700,
                  letterSpacing: '0.05em',
                  textTransform: 'uppercase' as const,
                  display: 'flex',
                }}
              >
                {sport} · {position}
              </div>
            </div>

            {/* Athlete name */}
            <div
              style={{
                fontSize: isSquare ? '56px' : '52px',
                fontWeight: 900,
                color: '#ffffff',
                lineHeight: 1.05,
                letterSpacing: '-0.02em',
                textAlign: isSquare ? 'center' : 'left',
                display: 'flex',
              }}
            >
              {name}
            </div>

            {/* Stats row */}
            {stats.length > 0 && (
              <div
                style={{
                  display: 'flex',
                  gap: '12px',
                  marginTop: '24px',
                  flexWrap: 'wrap',
                  justifyContent: isSquare ? 'center' : 'flex-start',
                }}
              >
                {stats.map((stat, i) => (
                  <div
                    key={i}
                    style={{
                      padding: '10px 18px',
                      backgroundColor: 'rgba(255,255,255,0.06)',
                      borderRadius: '12px',
                      border: '1px solid rgba(255,255,255,0.08)',
                      color: '#e5e5e5',
                      fontSize: '18px',
                      fontWeight: 600,
                      display: 'flex',
                    }}
                  >
                    {stat}
                  </div>
                ))}
              </div>
            )}

            {/* College match */}
            {match && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  marginTop: '20px',
                  color: '#a3a3a3',
                  fontSize: '18px',
                }}
              >
                <span style={{ display: 'flex' }}>Top Match:</span>
                <span
                  style={{
                    color: '#c8ff00',
                    fontWeight: 700,
                    display: 'flex',
                  }}
                >
                  {match}
                </span>
              </div>
            )}
          </div>

          {/* Right / Bottom section — SPARQ Rating */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              width: isSquare ? '280px' : '240px',
              flexShrink: 0,
            }}
          >
            {/* Rating circle */}
            <div
              style={{
                width: isSquare ? '240px' : '200px',
                height: isSquare ? '240px' : '200px',
                borderRadius: '50%',
                background: 'linear-gradient(135deg, rgba(200,255,0,0.15) 0%, rgba(200,255,0,0.03) 100%)',
                border: '3px solid rgba(200,255,0,0.4)',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                position: 'relative',
              }}
            >
              {/* Glow */}
              <div
                style={{
                  position: 'absolute',
                  inset: '-20px',
                  borderRadius: '50%',
                  background: 'radial-gradient(circle, rgba(200,255,0,0.12) 0%, transparent 60%)',
                  display: 'flex',
                }}
              />
              <div
                style={{
                  fontSize: '14px',
                  fontWeight: 700,
                  color: '#a3a3a3',
                  textTransform: 'uppercase' as const,
                  letterSpacing: '0.1em',
                  marginBottom: '4px',
                  display: 'flex',
                }}
              >
                SPARQ
              </div>
              <div
                style={{
                  fontSize: isSquare ? '80px' : '72px',
                  fontWeight: 900,
                  color: '#c8ff00',
                  lineHeight: 1,
                  display: 'flex',
                }}
              >
                {rating}
              </div>
              <div
                style={{
                  fontSize: '13px',
                  fontWeight: 600,
                  color: '#737373',
                  marginTop: '4px',
                  display: 'flex',
                }}
              >
                RATING
              </div>
            </div>

            {/* Initials badge below circle */}
            <div
              style={{
                marginTop: '16px',
                width: '48px',
                height: '48px',
                borderRadius: '12px',
                backgroundColor: 'rgba(200,255,0,0.15)',
                border: '1px solid rgba(200,255,0,0.3)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#c8ff00',
                fontSize: '18px',
                fontWeight: 900,
              }}
            >
              {initials}
            </div>
          </div>
        </div>

        {/* Bottom bar — branding */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '16px 60px',
            borderTop: '1px solid rgba(255,255,255,0.06)',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
            }}
          >
            <div
              style={{
                width: '28px',
                height: '28px',
                borderRadius: '6px',
                backgroundColor: '#c8ff00',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#000',
                fontSize: '14px',
                fontWeight: 900,
              }}
            >
              S
            </div>
            <span
              style={{
                color: '#737373',
                fontSize: '14px',
                fontWeight: 500,
                display: 'flex',
              }}
            >
              Powered by SPARQ
            </span>
          </div>
          <span
            style={{
              color: '#525252',
              fontSize: '13px',
              display: 'flex',
            }}
          >
            sparq-agent.vercel.app
          </span>
        </div>
      </div>
    ),
    { width, height }
  )
}
