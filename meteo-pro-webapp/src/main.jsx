import React from 'react';
import { createRoot } from 'react-dom/client';
import { dataSources, featureGroups, mapLayers } from './dataSources.js';
import './styles.css';

function App() {
  return (
    <main>
      <section className="hero">
        <div>
          <p className="eyebrow">Brazil and global meteorological dashboard</p>
          <h1>Meteo Pro Dashboard</h1>
          <p>Professional weather webapp blueprint with forecast, radar, satellite, wind, hydrology, aviation, marine and air quality modules.</p>
        </div>
      </section>

      <section className="stats">
        <div><strong>{dataSources.length}</strong><span>data sources</span></div>
        <div><strong>{mapLayers.length}</strong><span>map layers</span></div>
        <div><strong>{featureGroups.length}</strong><span>feature groups</span></div>
      </section>

      <section className="panel">
        <h2>Map layers</h2>
        <div className="chip-list">{mapLayers.map((layer) => <span key={layer}>{layer}</span>)}</div>
      </section>

      <section className="panel">
        <h2>Pro feature matrix</h2>
        <div className="feature-grid">
          {featureGroups.map((group) => (
            <article className="feature-card" key={group.title}>
              <h3>{group.title}</h3>
              <div className="chip-list">{group.items.map((item) => <span key={item}>{item}</span>)}</div>
            </article>
          ))}
        </div>
      </section>

      <section className="panel">
        <h2>Data source registry</h2>
        <div className="source-table">
          {dataSources.map((source) => (
            <article className="source-row" key={source.name}>
              <h3>{source.name}</h3>
              <p>{source.country} · {source.region}</p>
              <p>{source.category} · {source.access}</p>
              <div className="chip-list compact">{source.features.map((feature) => <span key={feature}>{feature}</span>)}</div>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}

createRoot(document.getElementById('root')).render(<App />);
