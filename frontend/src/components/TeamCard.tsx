import { useState } from 'react';

interface TeamCardProps {
  teamName: string;
  crestUrl: string;
}

function PlaceholderIcon({ teamName }: { teamName: string }) {
  return (
    <svg
      className="team-card__placeholder"
      width="32"
      height="32"
      viewBox="0 0 32 32"
      aria-hidden="true"
    >
      <rect width="32" height="32" rx="4" fill="#e0e0e0" />
      <text
        x="50%"
        y="50%"
        dominantBaseline="central"
        textAnchor="middle"
        fontSize="14"
        fill="#666"
      >
        {teamName.charAt(0).toUpperCase()}
      </text>
    </svg>
  );
}

export function TeamCard({ teamName, crestUrl }: TeamCardProps) {
  const [imgError, setImgError] = useState(false);

  const showPlaceholder = !crestUrl || imgError;

  return (
    <div className="team-card">
      {showPlaceholder ? (
        <PlaceholderIcon teamName={teamName} />
      ) : (
        <img
          className="team-card__crest"
          src={crestUrl}
          alt={teamName}
          width={32}
          height={32}
          onError={() => setImgError(true)}
        />
      )}
      <span className="team-card__name">{teamName}</span>
    </div>
  );
}
