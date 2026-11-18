import React, { useState, useEffect } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

const money = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });
const formatFee = (value, unit = 'cents') => unit === 'cents' ? money.format(value / 100) : String(value);

async function requestRun(mode, portVersion, daysOverdue, caseId) {
  const response = await fetch('/api/' + mode, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(mode === 'compare' ? { portVersion, input: daysOverdue, caseId } : { portVersion, caseId }),
  });
  if (!response.ok) {
    const problem = await response.json().catch(() => null);
    throw new Error(problem?.message ?? 'The comparison service is unavailable. Try again.');
  }
  return response.json();
}

function Evidence({ result, migration }) {
  const [artifact, setArtifact] = useState('criterion');
  const [copyStatus, setCopyStatus] = useState('');
  const days = result.daysOverdue;
  const criterion = 'Given ' + migration.inputLabel.toLowerCase() + ' ' + days + ', the migrated calculator shall return ' + formatFee(result.legacyCents, migration.outputUnit) + ' to preserve the observed legacy behavior.';
  const regression = [
    'from backend.' + migration.portFile.replace('.py', '') + ' import ' + migration.portFunction,
    '',
    'def test_' + migration.id.replaceAll('-', '_') + '_at_' + String(days).replace('-', 'minus_') + '():',
    '    assert ' + migration.portFunction + '(' + days + ', "corrected") == ' + result.legacyCents,
  ].join('\n');
  const content = artifact === 'criterion' ? criterion : regression;

  async function copy() {
    try {
      await navigator.clipboard.writeText(content);
      setCopyStatus('Copied');
    } catch {
      setCopyStatus('Select and copy the text below.');
    }
  }

  return <section className="evidence" aria-labelledby="evidence-title">
    <div className="evidence-header">
      <div>
        <h2 id="evidence-title">Turn the difference into a test</h2>
        <p>Confirm the legacy policy before adopting this expectation.</p>
      </div>
      <button type="button" className="outline" onClick={copy}>Copy {artifact === 'criterion' ? 'criterion' : 'test'}</button>
    </div>
    <div className="switch evidence-switch" aria-label="Evidence format">
      {['criterion', 'test'].map((value) => <button key={value} type="button" aria-pressed={artifact === value}
        onClick={() => { setArtifact(value); setCopyStatus(''); }}>
        {value === 'criterion' ? 'Acceptance criterion' : 'Pytest regression'}
      </button>)}
    </div>
    <pre>{content}</pre>
    <span className="copy-status" role="status">{copyStatus}</span>
  </section>;
}

function App() {
  const [cases, setCases] = useState([]);
  const [caseId, setCaseId] = useState('library');
  const [caseError, setCaseError] = useState('');
  useEffect(() => {
    fetch('/api/cases').then(async response => {
      if (!response.ok) throw new Error('Could not load migration cases.');
      setCases(await response.json());
    }).catch(failure => setCaseError(failure.message));
  }, []);
  const migration = cases.find(item => item.id === caseId);
  const [days, setDays] = useState('4');
  const [version, setVersion] = useState('flawed');
  const [result, setResult] = useState(null);
  const [pending, setPending] = useState('');
  const [error, setError] = useState('');
  const [lastMode, setLastMode] = useState(null);
  const [reference, setReference] = useState(null);

  async function run(mode, selectedVersion = version, input = days) {
    setPending(mode);
    setError('');
    setResult(null);
    try {
      const data = await requestRun(mode, selectedVersion, Number(input), caseId);
      setResult({ mode, data });
      setLastMode(mode);
      const pair = mode === 'compare' ? data : data.firstMismatch;
      if (pair && !pair.matches) setReference(pair.daysOverdue);
    } catch (failure) {
      setError(failure instanceof TypeError ? 'Could not reach the comparison service. Try again.' : failure.message);
    } finally {
      setPending('');
    }
  }

  function changeVersion(nextVersion) {
    if (nextVersion === version) return;
    setVersion(nextVersion);
    if (lastMode === 'sweep') {
      void run('sweep', nextVersion);
    } else if (lastMode === 'compare' && days !== '' && Number.isInteger(Number(days)) && Number(days) >= migration.minimum && Number(days) <= migration.maximum) {
      void run('compare', nextVersion);
    } else {
      setResult(null);
      setError('');
    }
  }

  const sweep = result?.mode === 'sweep' ? result.data : null;
  const comparison = result?.mode === 'compare' ? result.data : sweep?.firstMismatch;
  const mismatch = comparison && !comparison.matches;
  const parity = result && !mismatch;
  const displayedDays = comparison?.daysOverdue ?? days;

  function changeCase(nextId) {
    setCaseId(nextId);
    setDays(String(cases.find(item => item.id === nextId).minimum));
    setResult(null);
    setReference(null);
    setLastMode(null);
    setError('');
  }

  function downloadReport() {
    const report = result.mode === 'compare' ? result.data.report : result.data;
    const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' }));
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = caseId + '-' + version + '-report.json';
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return <>
    <header className="topbar">
      <div className="shell top-inner">
        <a className="brand" href="./"><span className="brand-icon" aria-hidden="true">↶</span> Behavior Time Machine</a>
        <a className="nav-link" href="#how-it-works">How it works <span aria-hidden="true">↗</span></a>
      </div>
    </header>
    <main className="shell">
      <section className="hero">
        <div className="hero-main">
          <h1>What did the old<br className="desktop-break" /> code <em>really</em> do?</h1>
          <p>Replay a working GW-BASIC program against its Python port and turn a hidden behavior difference into a regression test.</p>
        </div>
        <div className="hero-art" aria-hidden="true">
          <svg viewBox="0 0 300 210" fill="none">
            <defs><pattern id="grid" width="18" height="18" patternUnits="userSpaceOnUse"><path d="M18 0H0V18" stroke="#b3a3d8" opacity=".42"/></pattern></defs>
            <rect x="1" y="1" width="298" height="208" rx="14" fill="url(#grid)"/>
            <path d="M150 33a72 72 0 1 1-63 36" stroke="#6943bd" strokeWidth="2" strokeDasharray="3 7"/>
            <path d="M87 69l-1-19m1 19 19-3" stroke="#6943bd" strokeWidth="2"/>
            <path d="M121 64h58m-58 81h58m-51-81v5c0 15 9 19 22 35-13 16-22 20-22 35v6m44-81v5c0 15-9 19-22 35 13 16 22 20 22 35v6" stroke="#382367" strokeWidth="3" strokeLinecap="round"/>
            <path d="M136 135l14-18 14 18z" fill="#a581ef"/>
            <path d="M60 114v16m-8-8h16m173-63v22m-11-11h22m-14 80v10m-5-5h10" stroke="#6943bd" strokeWidth="2"/>
            <circle cx="150" cy="33" r="4" fill="#6943bd"/>
          </svg>
        </div>
      </section>

      <section className="workbench" aria-labelledby="workbench-title" aria-busy={Boolean(pending)}>
        <header className="bench-heading">
          <div><h2 id="workbench-title">{migration?.title ?? "Loading migration cases…"}</h2><p>{migration && "Compare one input or sweep all " + (migration.maximum - migration.minimum + 1) + " supported inputs."}</p></div>
          <div className="switch" aria-label="Python port version">
            <button type="button" aria-pressed={version === 'flawed'} disabled={Boolean(pending) || !migration} onClick={() => changeVersion('flawed')}>Initial port</button>
            <button type="button" aria-pressed={version === 'corrected'} disabled={Boolean(pending) || !migration} onClick={() => changeVersion('corrected')}>Corrected port</button>
          </div>
        </header>
        {caseError && <p role="alert">{caseError}</p>}
        <label className="case-select">Migration case
          <select value={caseId} disabled={Boolean(pending) || !migration} onChange={event => changeCase(event.target.value)}>
            {cases.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}
          </select>
        </label>
        <form className="controls" onSubmit={(event) => { event.preventDefault(); void run('compare'); }}>
          <label>{migration?.inputLabel ?? "Input"}<input type="number" required min={migration?.minimum} max={migration?.maximum} step="1" value={days}
            disabled={Boolean(pending) || !migration} onChange={(event) => { setDays(event.target.value); setError(''); }} /></label>
          <button className="primary" disabled={Boolean(pending) || !migration} type="submit">{pending === 'compare' ? 'Comparing…' : 'Compare'} <span aria-hidden="true">→</span></button>
          <button className="outline sweep-button" disabled={Boolean(pending) || !migration} type="button" onClick={() => void run('sweep')}>{pending === 'sweep' ? 'Sweeping…' : 'Run boundary sweep'}</button>
        </form>
        {error && <div className="callout mismatch" role="alert"><strong>Run failed.</strong> {error}</div>}
        <div className="panes">
          <article className="legacy">
            <header><span className="terminal-icon" aria-hidden="true">›_</span><h3>Legacy terminal</h3><span className="runtime-label">GW-BASIC</span></header>
            <div className="pane-body">
              <div className="terminal-prompt">&gt; {comparison ? 'INPUT ' + displayedDays : 'RUN OVERDUE.BAS'}</div>
              <div className="fee">{comparison ? formatFee(comparison.legacyCents, migration.outputUnit) : '—'}</div>
              <div className="terminal-detail">{comparison ? comparison.legacyOutput + ' ' + migration.outputUnit : 'Awaiting input'}</div>
            </div>
          </article>
          <article className="modern">
            <header><span className="modern-icon" aria-hidden="true">⌘</span><h3>Modern calculator</h3><span className="runtime-label">PYTHON</span></header>
            <div className="pane-body">
              <div className="modern-label">Calculated fee</div>
              <div className="fee">{comparison ? formatFee(comparison.modernCents, migration.outputUnit) : '—'}</div>
              <div className="modern-label">{comparison ? migration?.inputLabel + ' ' + displayedDays : 'Awaiting comparison'}</div>
            </div>
          </article>
        </div>
        <div aria-live="polite">
          {mismatch && <div className="callout mismatch">
            <strong>{sweep ? 'First mismatch at ' + migration.inputUnit + ' ' + displayedDays : 'Mismatch at ' + migration.inputUnit + ' ' + displayedDays}</strong>
            <span>{sweep ? sweep.mismatchCount + (sweep.mismatchCount === 1 ? ' difference across ' : ' differences across ') + sweep.checkedCount + ' inputs.' : 'The port and the running legacy program returned different values.'}</span>
          </div>}
          {parity && <div className="callout match">
            <strong>{sweep ? 'Parity verified across all ' + sweep.checkedCount + ' inputs' : 'Both programs agree at ' + migration.inputUnit + ' ' + displayedDays}</strong>
            {sweep && reference !== null && <button type="button" className="link-button" onClick={() => { setDays(String(reference)); void run('compare', version, String(reference)); }}>Replay {migration?.inputUnit} {reference} →</button>}
          </div>}
        </div>
        {comparison && <details className="policy" open={Boolean(mismatch)}><summary>Legacy policy lines</summary>
          <pre>{comparison.policyLines.join('\n')}</pre>
        </details>}
        {mismatch && <Evidence key={caseId + comparison.daysOverdue} result={comparison} migration={migration} />}
        {result && <div className="report-download"><button type="button" className="outline" onClick={downloadReport}>Download run report ↓</button><p>Includes the manifest, source hashes, checked range, actual outputs, and every mismatch.</p></div>}
      </section>
      <section className="how" id="how-it-works">
        <h2>How it works</h2>
        <p>Both fictional demonstration programs run in PC-BASIC through the same generated batch driver. Each sweep evaluates every integer in the selected manifest’s declared domain in one interpreter process. The first difference gives you a concrete case to review before updating the Kiro spec and the port.</p>
      </section>
    </main>
    <footer className="shell footer">Behavior Time Machine <span>Independent Kiroween prototype</span></footer>
  </>;
}

createRoot(document.getElementById('root')).render(<App />);
