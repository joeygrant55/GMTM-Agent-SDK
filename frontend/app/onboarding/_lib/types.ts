export const ONBOARDING_MAXPREPS_KEY = 'sparq.onboarding.maxprepsData'
export const ONBOARDING_PROFILE_ID_KEY = 'sparq.onboarding.profileId'

export interface MaxPrepsSeasonStats {
  season?: string
  tackles?: number
  interceptions?: number
  passBreakups?: number
  sacks?: number
  touchdowns?: number
  [key: string]: string | number | undefined
}

export interface MaxPrepsAthlete {
  maxprepsAthleteId?: string
  name: string
  position?: string
  school?: string
  classYear?: number
  city?: string
  state?: string
  maxprepsUrl?: string
  teamRecord?: string
  seasonStats?: MaxPrepsSeasonStats[]
}

export interface CompleteOnboardingPayload {
  maxprepsData: MaxPrepsAthlete | null
  combineMetrics: {
    fortyYardDash?: number
    shuttle?: number
    vertical?: number
    heightFeet?: number
    heightInches?: number
    weight?: number
  }
  gpa?: number
  majorArea: 'Undecided' | 'Business' | 'STEM' | 'Communications' | 'Other'
  recruitingGoals: {
    targetLevel: 'D1 Power' | 'D1 Mid-Major' | 'D2' | 'D3' | 'Open'
    geography: 'Anywhere' | 'In-state' | 'Southeast' | 'Midwest' | 'West' | 'Northeast'
    schoolSize: 'Large' | 'Medium' | 'Small' | 'No preference'
  }
  hudlUrl?: string
}
