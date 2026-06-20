import './MatchPredictionCard.css';

export interface MatchPredictionCardProps {
  homeTeam: string;
  awayTeam: string;
  homeWinProb: number;
  homeLossProb: number;
  homeTeamCrest: string;
  awayTeamCrest: string;
  matchDate: string;
}

/**
 * Formats a probability value (0.0–1.0) as a percentage string
 * rounded to 1 decimal place, e.g. "65.3%".
 */
export function formatProbability(prob: number): string {
  return (prob * 100).toFixed(1) + '%';
}

export function MatchPredictionCard({
  homeTeam,
  awayTeam,
  homeWinProb,
  homeLossProb,
  homeTeamCrest,
  awayTeamCrest,
  matchDate,
}: MatchPredictionCardProps) {
  const homeFavored = homeWinProb > homeLossProb;
  const formattedDate = new Date(matchDate).toLocaleDateString();

  return (
    <div className="match-prediction-card">
      <div className="match-date">{formattedDate}</div>
      <div className="match-teams">
        <div className={`team home-team${homeFavored ? ' favored' : ''}`}>
          {homeTeamCrest && (
            <img
              className="team-crest"
              src={homeTeamCrest}
              alt={homeTeam}
            />
          )}
          <span className="team-name">{homeTeam}</span>
          <span className="team-prob">{formatProbability(homeWinProb)}</span>
        </div>
        <div className={`team away-team${!homeFavored ? ' favored' : ''}`}>
          {awayTeamCrest && (
            <img
              className="team-crest"
              src={awayTeamCrest}
              alt={awayTeam}
            />
          )}
          <span className="team-name">{awayTeam}</span>
          <span className="team-prob">{formatProbability(homeLossProb)}</span>
        </div>
      </div>
    </div>
  );
}

export default MatchPredictionCard;
