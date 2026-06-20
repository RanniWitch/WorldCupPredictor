import { useState, useEffect } from 'react';
import { fetchGroups, fetchPredictions } from '../api';
import { TeamCard } from './TeamCard';
import { MatchPredictionCard } from './MatchPredictionCard';
import type { Group, MatchPrediction } from '../types';
import './GroupStageView.css';

interface GroupStageViewProps {
  active?: boolean;
}

export function GroupStageView({ active = true }: GroupStageViewProps) {
  const [groups, setGroups] = useState<Group[]>([]);
  const [predictions, setPredictions] = useState<MatchPrediction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [groupsData, predictionsData] = await Promise.all([
        fetchGroups(),
        fetchPredictions(),
      ]);
      setGroups(groupsData.groups);
      setPredictions(predictionsData.predictions);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
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
    return <div className="group-stage-loading" role="status">Loading group stage data…</div>;
  }

  if (error) {
    return (
      <div className="group-stage-error" role="alert">
        <p>{error}</p>
        <button onClick={loadData}>Retry</button>
      </div>
    );
  }

  return (
    <div className="group-stage-grid">
      {groups.map((group) => {
        const teamNames = group.teams.map((t) => t.team_name);
        const groupPredictions = predictions.filter(
          (p) =>
            teamNames.includes(p.home_team_name) &&
            teamNames.includes(p.away_team_name)
        );

        return (
          <div className="group-card" key={group.group_name}>
            <h2 className="group-card__header">Group {group.group_name}</h2>
            <div className="group-card__teams">
              {group.teams.map((team) => (
                <TeamCard
                  key={team.team_id}
                  teamName={team.team_name}
                  crestUrl={team.crest}
                />
              ))}
            </div>
            {groupPredictions.length > 0 && (
              <div className="group-card__predictions">
                {groupPredictions.map((prediction) => (
                  <MatchPredictionCard
                    key={`${prediction.home_team_name}-${prediction.away_team_name}`}
                    homeTeam={prediction.home_team_name}
                    awayTeam={prediction.away_team_name}
                    homeWinProb={prediction.home_win_prob}
                    homeLossProb={prediction.home_loss_prob}
                    homeTeamCrest={prediction.home_team_crest}
                    awayTeamCrest={prediction.away_team_crest}
                    matchDate={prediction.match_date}
                  />
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default GroupStageView;
