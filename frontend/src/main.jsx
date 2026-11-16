import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

const money = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });
const formatFee = (cents) => money.format(cents / 100);

async function requestRun(mode, portVersion, daysOverdue) {
  const response = await fetch('/api/' + mode, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(mode === 'compare' ? { portVersion, daysOverdue } : { portVersion }),
  });
  if (!response.ok) {
    const problem = await response.json().catch(() => null);
    throw new Error(problem?.message ?? 'The comparison service is unavailable. Try again.');
  }
  return response.json();
}

function Evidence({ result }) {
  const [artifact, setArtifact] = useState('criterion');
  const [copyStatus, setCopyStatus] = useState('');
  const days = result.daysOverdue;
  const criterion = 'Given a return ' + days + ' days overdue, when the fee is calculated, the migrated calculator shall charge ' + formatFee(result.legacyCents) + ' to preserve the observed library policy.';
  const regression = [
    'from backend.fees import calculate_fee',
    '',
    'def test_fee_at_' + days + '_days():',
    '    assert calculate_fee(' + days + ', "corrected") == ' + result.legacyCents,
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
      const data = await requestRun(mode, selectedVersion, Number(input));
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
    } else if (lastMode === 'compare' && days !== '' && Number.isInteger(Number(days)) && Number(days) >= 0 && Number(days) <= 365) {
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
          <div><h2 id="workbench-title">Library fee calculator</h2><p>Compare one return or sweep all 366 supported inputs.</p></div>
          <div className="switch" aria-label="Python port version">
            <button type="button" aria-pressed={version === 'flawed'} disabled={Boolean(pending)} onClick={() => changeVersion('flawed')}>Initial port</button>
            <button type="button" aria-pressed={version === 'corrected'} disabled={Boolean(pending)} onClick={() => changeVersion('corrected')}>Corrected port</button>
          </div>
        </header>
        <form className="controls" onSubmit={(event) => { event.preventDefault(); void run('compare'); }}>
          <label>Days overdue<input type="number" required min="0" max="365" step="1" value={days}
            disabled={Boolean(pending)} onChange={(event) => { setDays(event.target.value); setError(''); }} /></label>
          <button className="primary" disabled={Boolean(pending)} type="submit">{pending === 'compare' ? 'Comparing…' : 'Compare'} <span aria-hidden="true">→</span></button>
          <button className="outline sweep-button" disabled={Boolean(pending)} type="button" onClick={() => void run('sweep')}>{pending === 'sweep' ? 'Sweeping…' : 'Run boundary sweep'}</button>
        </form>
        {error && <div className="callout mismatch" role="alert"><strong>Run failed.</strong> {error}</div>}
        <div className="panes">
          <article className="legacy">
            <header><span className="terminal-icon" aria-hidden="true">›_</span><h3>Legacy terminal</h3><span className="runtime-label">GW-BASIC</span></header>
            <div className="pane-body">
              <div className="terminal-prompt">&gt; {comparison ? 'INPUT ' + displayedDays : 'RUN OVERDUE.BAS'}</div>
              <div className="fee">{comparison ? formatFee(comparison.legacyCents) : '—'}</div>
              <div className="terminal-detail">{comparison ? comparison.legacyOutput + ' cents' : 'Awaiting input'}</div>
            </div>
          </article>
          <article className="modern">
            <header><span className="modern-icon" aria-hidden="true">⌘</span><h3>Modern calculator</h3><span className="runtime-label">PYTHON</span></header>
            <div className="pane-body">
              <div className="modern-label">Calculated fee</div>
              <div className="fee">{comparison ? formatFee(comparison.modernCents) : '—'}</div>
              <div className="modern-label">{comparison ? displayedDays + ' days overdue' : 'Awaiting comparison'}</div>
            </div>
          </article>
        </div>
        <div aria-live="polite">
          {mismatch && <div className="callout mismatch">
            <strong>{sweep ? 'First mismatch at day ' + displayedDays : 'Mismatch at day ' + displayedDays}</strong>
            <span>{sweep ? sweep.mismatchCount + ' differences across ' + sweep.checkedCount + ' inputs.' : 'The grace period changes when fees begin, while the original bills from the due date.'}</span>
          </div>}
          {parity && <div className="callout match">
            <strong>{sweep ? 'Parity verified across all ' + sweep.checkedCount + ' inputs' : 'Both programs agree at day ' + displayedDays}</strong>
            {sweep && reference !== null && <button type="button" className="link-button" onClick={() => { setDays(String(reference)); void run('compare', version, String(reference)); }}>Replay day {reference} →</button>}
          </div>}
        </div>
        {comparison && <details className="policy" open={Boolean(mismatch)}><summary>Legacy policy lines</summary>
          <pre>{comparison.policyLines.join('\n')}</pre>
        </details>}
        {mismatch && <Evidence key={comparison.daysOverdue} result={comparison} />}
      </section>
      <section className="how" id="how-it-works">
        <h2>How it works</h2>
        <p>The terminal runs an original demonstration fixture in PC-BASIC. The sweep evaluates every whole day from 0 to 365 in order. The first difference gives you a concrete case to review before updating the Kiro spec and the port.</p>
      </section>
    </main>
    <footer className="shell footer">Behavior Time Machine <span>Independent Kiroween prototype</span></footer>
  </>;
}

createRoot(document.getElementById('root')).render(<App />);
