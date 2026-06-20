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

export interface MatchPrediction {
  home_team_name: string;
  away_team_name: string;
  home_win_prob: number;
  home_loss_prob: number;
  home_team_crest: string;
  away_team_crest: string;
  match_date: string;
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
