export interface Team {
  team_id: number;
  team_name: string;
  crest: string;
}

export interface Group {
  group_name: string;
  teams: Team[];
}

export interface GroupsResponse {
  groups: Group[];
}

export interface ScorelinePrediction {
  home_goals: number;
  away_goals: number;
  probability: number;
}

export interface MatchPrediction {
  home_team_name: string;
  away_team_name: string;
  home_win_prob: number;
  draw_prob: number;
  away_win_prob: number;
  home_loss_prob: number;
  home_team_crest: string;
  away_team_crest: string;
  match_date: string;

  // Goals predictions
  expected_home_goals: number;
  expected_away_goals: number;
  expected_total_goals: number;
  over_1_5_prob: number;
  over_2_5_prob: number;
  over_3_5_prob: number;
  over_4_5_prob: number;
  predicted_home_goals: number;
  predicted_away_goals: number;
  predicted_score_prob: number;
  top_scorelines: ScorelinePrediction[];
}

export interface PredictionsResponse {
  predictions: MatchPrediction[];
}

export interface KnockoutTeam {
  team_name: string;
  crest: string;
}

export interface KnockoutMatch {
  home_team: KnockoutTeam;
  away_team: KnockoutTeam;
  status: string;
  home_score: number | null;
  away_score: number | null;
}

export interface KnockoutRound {
  round_name: string;
  matches: KnockoutMatch[];
}

export interface KnockoutResponse {
  rounds: KnockoutRound[];
}

// Arbitrage Scanner Types
export interface BestOdds {
  price: number;
  bookmaker: string;
}

export interface ArbitrageStakes {
  budget: number;
  home: number;
  draw?: number;
  away: number;
  guaranteed_profit: number;
}

export interface BookmakerOdds {
  bookmaker: string;
  home?: number;
  draw?: number;
  away?: number;
}

export interface ArbitrageEvent {
  event_id: string;
  home_team: string;
  away_team: string;
  commence_time: string;
  is_arbitrage: boolean;
  implied_probability: number;
  profit_pct: number;
  market?: string;
  market_label?: string;
  best_odds: {
    home: BestOdds;
    away: BestOdds;
    draw: BestOdds | null;
  };
  stakes: ArbitrageStakes | null;
  bookmaker_count: number;
  all_bookmaker_odds: BookmakerOdds[];
}

export interface ArbitrageResponse {
  events: ArbitrageEvent[];
  arbitrage_found: number;
  total_events: number;
  quota_remaining: string;
  sport: string;
}

export interface SportItem {
  key: string;
  title: string;
  group: string;
  description: string;
  has_outrights: boolean;
}

export interface SportsResponse {
  active: SportItem[];
  inactive: SportItem[];
}
