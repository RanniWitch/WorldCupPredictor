import { useState } from 'react';
import { GroupStageView } from './components/GroupStageView';
import { KnockoutBracketView } from './components/KnockoutBracketView';
import './App.css';

type Tab = 'groups' | 'knockout';

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('groups');
  const [refreshKey, setRefreshKey] = useState(0);

  const handleRefresh = () => {
    setRefreshKey((prev) => prev + 1);
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="app-title">World Cup 2026 Predictor</h1>
        <button className="app-refresh-btn" onClick={handleRefresh} aria-label="Refresh data">
          ↻ Refresh
        </button>
      </header>

      <nav className="app-tabs" role="tablist" aria-label="Dashboard views">
        <button
          className={`app-tab${activeTab === 'groups' ? ' app-tab--active' : ''}`}
          role="tab"
          aria-selected={activeTab === 'groups'}
          aria-controls="panel-groups"
          id="tab-groups"
          onClick={() => setActiveTab('groups')}
        >
          Group Stage
        </button>
        <button
          className={`app-tab${activeTab === 'knockout' ? ' app-tab--active' : ''}`}
          role="tab"
          aria-selected={activeTab === 'knockout'}
          aria-controls="panel-knockout"
          id="tab-knockout"
          onClick={() => setActiveTab('knockout')}
        >
          Knockout Bracket
        </button>
      </nav>

      <main className="app-content">
        <div
          id="panel-groups"
          role="tabpanel"
          aria-labelledby="tab-groups"
          hidden={activeTab !== 'groups'}
        >
          {activeTab === 'groups' && (
            <GroupStageView key={`groups-${refreshKey}`} active={true} />
          )}
        </div>
        <div
          id="panel-knockout"
          role="tabpanel"
          aria-labelledby="tab-knockout"
          hidden={activeTab !== 'knockout'}
        >
          {activeTab === 'knockout' && (
            <KnockoutBracketView key={`knockout-${refreshKey}`} active={true} />
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
