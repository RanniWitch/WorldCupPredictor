import { useState, useEffect } from 'react';
import { fetchKnockout } from '../api';
import type { KnockoutResponse, KnockoutRound, KnockoutMatch, KnockoutTeam } from '../types';
import './KnockoutBracketView.css';

interface KnockoutBracketViewProps {
  active?: boolean;
}

function formatRoundName(roundName: string): string {
  return roundName.replace(/_/g, ' ');
}

function TeamSlot({ team, score }: { team: KnockoutTeam; score: number | null }) {
  const isTBD = team.team_name === 'TBD';

  return (
    <div className="knockout-match__team">
      {!isTBD && team.crest ? (
        <img
          className="knockout-match__crest"
          src={team.crest}
          alt={team.team_name}
          width={24}
          height={24}
        />
      ) : (
        <svg
          className="knockout-match__crest"
          width="24"
          height="24"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <rect width="24" height="24" rx="4" fill="#e0e0e0" />
          <text
            x="50%"
            y="50%"
            dominantBaseline="central"
            textAnchor="middle"
            fontSize="10"
            fill="#666"
          >
            ?
          </text>
        </svg>
      )}
      <span className={`knockout-match__team-name${isTBD ? ' knockout-match__team-name--tbd' : ''}`}>
        {team.team_name}
      </span>
      {score !== null && (
        <span className="knockout-match__score">{score}</span>
      )}
    </div>
  );
}

function MatchCard({ match }: { match: KnockoutMatch }) {
  const isFinished = match.status === 'FINISHED';

  return (
    <div className="knockout-match">
      <TeamSlot
        team={match.home_team}
        score={isFinished ? match.home_score : null}
      />
      {isFinished && (
        <div className="knockout-match__score-divider">vs</div>
      )}
      <TeamSlot
        team={match.away_team}
        score={isFinished ? match.away_score : null}
      />
      {!isFinished && (
        <div className="knockout-match__status">{match.status}</div>
      )}
    </div>
  );
}

function RoundColumn({ round }: { round: KnockoutRound }) {
  return (
    <div className="knockout-bracket__round">
      <div className="knockout-bracket__round-header">
        {formatRoundName(round.round_name)}
      </div>
      <div className="knockout-bracket__matches">
        {round.matches.map((match, index) => (
          <MatchCard key={index} match={match} />
        ))}
      </div>
    </div>
  );
}

export function KnockoutBracketView({ active = true }: KnockoutBracketViewProps) {
  const [data, setData] = useState<KnockoutResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchKnockout();
      setData(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (active) {
      loadData();
    }
  }, [active]);

  if (loading) {
    return (
      <div className="knockout-bracket__loading" role="status">
        Loading knockout bracket…
      </div>
    );
  }

  if (error) {
    return (
      <div className="knockout-bracket__error" role="alert">
        <p>{error}</p>
        <button onClick={loadData}>Retry</button>
      </div>
    );
  }

  if (!data || data.rounds.length === 0) {
    return (
      <div className="knockout-bracket__loading">
        No knockout data available.
      </div>
    );
  }

  return (
    <div className="knockout-bracket">
      <div className="knockout-bracket__rounds">
        {data.rounds.map((round) => (
          <RoundColumn key={round.round_name} round={round} />
        ))}
      </div>
    </div>
  );
}
