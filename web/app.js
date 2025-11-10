const API_BASE = window.API_BASE ?? 'http://127.0.0.1:8001';
const state = {
    teams: [],
    lastMatchup: null,
};

document.addEventListener('DOMContentLoaded', () => {
    initPipeline();
    initScrollReveal();
    initConsole();
});

function initConsole() {
    const matchupForm = document.getElementById('matchup-form');
    const batchForm = document.getElementById('batch-form');
    const refreshDataBtn = document.getElementById('refresh-data');
    const refreshInjuriesBtn = document.getElementById('refresh-injuries');

    if (!matchupForm) {
        return;
    }

    const homeSelect = document.getElementById('home-team');
    const awaySelect = document.getElementById('away-team');
    const neutralCheckbox = document.getElementById('neutral-site');
    const matchupResult = document.getElementById('matchup-result');

    fetchHealthStatus();
    loadTeams(homeSelect, awaySelect);

    matchupForm.addEventListener('submit', (event) => {
        onMatchupSubmit(event, {
            homeSelect,
            awaySelect,
            neutralCheckbox,
            resultEl: matchupResult,
        });
    });

    if (batchForm) {
        const batchResult = document.getElementById('batch-result');
        batchForm.addEventListener('submit', (event) => onBatchSubmit(event, batchResult));
    }

    if (refreshDataBtn) {
        const refreshResult = document.getElementById('refresh-result');
        refreshDataBtn.addEventListener('click', () => handleRefresh('data', refreshDataBtn, refreshResult));
    }

    if (refreshInjuriesBtn) {
        const refreshResult = document.getElementById('refresh-result');
        refreshInjuriesBtn.addEventListener('click', () => handleRefresh('injuries', refreshInjuriesBtn, refreshResult));
    }
}

async function loadTeams(homeSelect, awaySelect) {
    if (!homeSelect || !awaySelect) return;

    setSelectPlaceholder(homeSelect, 'Loading teams…');
    setSelectPlaceholder(awaySelect, 'Loading teams…');

    try {
        const data = await request('/api/teams');
        const teams = Array.isArray(data?.teams) ? data.teams : [];
        if (!teams.length) {
            throw new Error('NFL dataset unavailable');
        }

        state.teams = teams;
        populateTeamSelect(homeSelect, teams, 'Select home team');
        populateTeamSelect(awaySelect, teams, 'Select away team');
        updateStatus('teams', `${teams.length} teams cached`);
    } catch (error) {
        const message = error instanceof Error ? error.message : 'Unable to load teams';
        setSelectPlaceholder(homeSelect, message, true);
        setSelectPlaceholder(awaySelect, message, true);
        updateStatus('teams', `Unavailable · ${message}`);
    }
}

function setSelectPlaceholder(select, text, disabled = true) {
    if (!select) return;
    select.innerHTML = '';
    const option = document.createElement('option');
    option.value = '';
    option.disabled = true;
    option.selected = true;
    option.textContent = text;
    select.appendChild(option);
    select.disabled = disabled;
}

function populateTeamSelect(select, teams, placeholder) {
    if (!select) return;
    select.innerHTML = '';

    const placeholderOption = document.createElement('option');
    placeholderOption.value = '';
    placeholderOption.disabled = true;
    placeholderOption.selected = true;
    placeholderOption.textContent = placeholder;
    select.appendChild(placeholderOption);

    teams.forEach((team) => {
        const option = document.createElement('option');
        option.value = team;
        option.textContent = team;
        select.appendChild(option);
    });

    select.disabled = false;
}

async function onMatchupSubmit(event, controls) {
    event.preventDefault();
    if (!controls) return;

    const {
        homeSelect,
        awaySelect,
        neutralCheckbox,
        resultEl,
    } = controls;

    const homeTeam = homeSelect?.value ?? '';
    const awayTeam = awaySelect?.value ?? '';

    if (!homeTeam || !awayTeam) {
        updateResult(resultEl, { status: 'error', html: 'Pick both teams before running a prediction.' });
        return;
    }

    if (homeTeam === awayTeam) {
        updateResult(resultEl, { status: 'error', html: 'Select two different teams to simulate a matchup.' });
        return;
    }

    const submitBtn = document.getElementById('matchup-submit');
    setLoading(submitBtn, true, 'Running...');
    updateResult(resultEl, { status: 'info', html: 'Crunching numbers...' });

    try {
        const payload = {
            home_team: homeTeam,
            away_team: awayTeam,
            neutral_site: Boolean(neutralCheckbox?.checked),
            use_ml: true,
        };

        const response = await request('/api/matchup', {
            method: 'POST',
            body: payload,
        });

        renderMatchupResult(resultEl, response, payload);
        state.lastMatchup = {
            ...payload,
            timestamp: response?.timestamp ?? new Date().toISOString(),
        };
        updateStatus('matchup', formatTimestamp(state.lastMatchup.timestamp));
    } catch (error) {
        const message = error instanceof Error ? error.message : 'Prediction failed';
        updateResult(resultEl, { status: 'error', html: message });
    } finally {
        setLoading(submitBtn, false);
    }
}

function renderMatchupResult(container, response, requestPayload) {
    if (!container) return;

    const prediction = response?.prediction ?? {};
    const injuries = response?.injuries ?? {};
    const timestamp = response?.timestamp;

    const homeTeam = requestPayload?.home_team ?? prediction?.home_team ?? 'Home';
    const awayTeam = requestPayload?.away_team ?? prediction?.away_team ?? 'Away';

    const homePoints = toNumber(prediction?.home_points);
    const awayPoints = toNumber(prediction?.away_points);
    const hasPoints = Number.isFinite(homePoints) && Number.isFinite(awayPoints);

    const winner = hasPoints
        ? homePoints > awayPoints
            ? homeTeam
            : awayPoints > homePoints
                ? awayTeam
                : 'Too close to call'
        : prediction?.winner ?? 'Prediction ready';

    const confidence = hasPoints
        ? Math.min((Math.abs(homePoints - awayPoints) / 6) * 100, 95)
        : toNumber(prediction?.confidence, 0);

    const content = `
        <div class="result-header">
            <div class="result-team">
                <span class="team-name">${escapeHtml(homeTeam)}</span>
                <span class="team-score">${hasPoints ? formatPoints(homePoints) : '—'}</span>
                <span class="team-meta">Home</span>
            </div>
            <div class="result-team">
                <span class="team-name">${escapeHtml(awayTeam)}</span>
                <span class="team-score">${hasPoints ? formatPoints(awayPoints) : '—'}</span>
                <span class="team-meta">Away</span>
            </div>
        </div>
        <div class="result-metadata">
            <div class="result-row">
                <span>Winner</span>
                <strong>${escapeHtml(winner)}</strong>
            </div>
            <div class="result-row">
                <span>Confidence</span>
                <strong>${confidence ? `${confidence.toFixed(1)}%` : '—'}</strong>
            </div>
            <div class="result-row">
                <span>Neutral site</span>
                <strong>${requestPayload?.neutral_site ? 'Yes' : 'No'}</strong>
            </div>
            <div class="result-row">
                <span>Generated</span>
                <strong>${formatTimestamp(timestamp)}</strong>
            </div>
        </div>
        ${renderInjurySummary(homeTeam, injuries?.home_team, awayTeam, injuries?.away_team)}
    `;

    updateResult(container, { status: 'success', html: content });
}

function renderInjurySummary(homeTeam, homeData, awayTeam, awayData) {
    if (!homeData && !awayData) {
        return '';
    }

    const segments = [];
    if (homeData) {
        segments.push(renderTeamInjury(homeTeam, homeData));
    }
    if (awayData) {
        segments.push(renderTeamInjury(awayTeam, awayData));
    }

    if (!segments.length) {
        return '';
    }

    return `
        <div class="injury-summary">
            <h4>Injury impact</h4>
            ${segments.join('')}
        </div>
    `;
}

function renderTeamInjury(teamName, data) {
    const impact = toNumber(data?.impact_score);
    const total = toNumber(data?.total_injuries, 0);
    const keyList = Array.isArray(data?.injury_list) ? data.injury_list : [];
    const keyCount = toNumber(data?.key_injuries, keyList.length);
    const qbStatus = typeof data?.qb_injured === 'boolean'
        ? data.qb_injured
            ? 'Key QB impacted'
            : 'Starter available'
        : null;

    const keyBlock = keyList.length
        ? `<ul>${keyList.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>`
        : '<p class="form-footnote">No flagged key injuries.</p>';

    const qbRow = qbStatus
        ? `<div class="result-row"><span>QB status</span><strong>${qbStatus}</strong></div>`
        : '';

    return `
        <div class="injury-card">
            <div class="injury-card__header">
                <span class="injury-card__team">${escapeHtml(teamName)}</span>
                <span class="injury-card__impact">${impact ? `Impact ${impact.toFixed(1)}` : 'Impact —'}</span>
            </div>
            <div class="result-row"><span>Total injuries</span><strong>${total}</strong></div>
            <div class="result-row"><span>Key injuries</span><strong>${keyCount}</strong></div>
            ${qbRow}
            ${keyBlock}
        </div>
    `;
}

async function onBatchSubmit(event, container) {
    event.preventDefault();
    if (!container) return;

    const submitBtn = document.getElementById('batch-submit');
    const weekInput = document.getElementById('batch-week');
    const seasonInput = document.getElementById('batch-season');

    const week = toNumber(weekInput?.value);
    if (!Number.isFinite(week) || week < 1 || week > 18) {
        updateResult(container, { status: 'error', html: 'Enter a week between 1 and 18.' });
        return;
    }

    setLoading(submitBtn, true, 'Batching...');
    updateResult(container, { status: 'info', html: 'Running weekly batch...' });

    try {
        const payload = {
            week,
            season_type: seasonInput?.value ?? 'regular',
            use_ml: true,
        };
        const response = await request('/api/batch', {
            method: 'POST',
            body: payload,
        });
        renderBatchResult(container, response);
    } catch (error) {
        const message = error instanceof Error ? error.message : 'Batch prediction failed';
        updateResult(container, { status: 'error', html: message });
    } finally {
        setLoading(submitBtn, false);
    }
}

function renderBatchResult(container, data) {
    if (!container) return;

    const summary = data?.summary ?? {};
    const predictions = Array.isArray(data?.predictions) ? data.predictions : [];
    const failed = Array.isArray(data?.failed_games) ? data.failed_games : [];

    const highlightItems = predictions
        .slice(0, 3)
        .map((game, index) => `<li>${formatPredictionHighlight(game, index)}</li>`)
        .join('');

    const failureNote = failed.length
        ? `<p class="form-footnote">${failed.length} games need manual review.</p>`
        : '';

    const content = `
        <div class="result-metadata">
            <div class="result-row">
                <span>Week</span>
                <strong>${escapeHtml(summary.week ?? '—')} (${escapeHtml((summary.season_type ?? '').toUpperCase())})</strong>
            </div>
            <div class="result-row">
                <span>Predicted</span>
                <strong>${summary.predicted_games ?? predictions.length}/${summary.total_games ?? predictions.length}</strong>
            </div>
            <div class="result-row">
                <span>Generated</span>
                <strong>${formatTimestamp(summary.timestamp)}</strong>
            </div>
        </div>
        ${predictions.length ? `<div class="injury-summary"><h4>Highlights</h4><ul>${highlightItems}</ul></div>` : '<p class="form-footnote">No games predicted. Check the data refresh status.</p>'}
        ${failureNote}
    `;

    updateResult(container, { status: 'success', html: content });
}

function formatPredictionHighlight(game, index) {
    const home = escapeHtml(game?.home_team ?? 'Home');
    const away = escapeHtml(game?.away_team ?? 'Away');

    if (typeof game?.home_win_prob === 'number' && typeof game?.away_win_prob === 'number') {
        const winner = escapeHtml(game?.winner ?? (game.home_win_prob >= game.away_win_prob ? home : away));
        const confidence = toNumber(game?.confidence) || Math.max(game.home_win_prob, game.away_win_prob) * 100;
        return `${index + 1}. ${away} @ ${home} — ${winner} (${confidence.toFixed(1)}%)`;
    }

    if (typeof game?.home_points === 'number' && typeof game?.away_points === 'number') {
        const winner = game.home_points === game.away_points
            ? 'Toss-up'
            : game.home_points > game.away_points
                ? home
                : away;
        const diff = Math.abs(game.home_points - game.away_points);
        const confidence = Math.min((diff / 6) * 100, 95);
        return `${index + 1}. ${away} @ ${home} — ${winner} (${confidence.toFixed(1)}%)`;
    }

    return `${index + 1}. ${away} @ ${home}`;
}

async function handleRefresh(type, button, container) {
    if (!container) return;

    const label = type === 'data' ? 'Refreshing data...' : 'Refreshing injuries...';
    setLoading(button, true, label);
    updateResult(container, { status: 'info', html: label });

    try {
        const response = await request(`/api/refresh/${type}`, { method: 'POST' });
        const html = renderRefreshDetails(type, response);
        updateResult(container, { status: 'success', html });
        updateStatus('refresh', formatTimestamp(response?.updated_at));
    } catch (error) {
        const message = error instanceof Error ? error.message : 'Refresh failed';
        updateResult(container, { status: 'error', html: message });
    } finally {
        setLoading(button, false);
    }
}

function renderRefreshDetails(type, payload) {
    if (!payload) return 'No response received.';

    const updated = formatTimestamp(payload.updated_at);
    const details = payload.details ?? {};

    if (type === 'data') {
        return `
            <div class="result-metadata">
                <div class="result-row"><span>File</span><strong>${escapeHtml(details.file ?? 'nflData.txt')}</strong></div>
                <div class="result-row"><span>Size</span><strong>${details.size_kb ? `${details.size_kb} KB` : '—'}</strong></div>
                <div class="result-row"><span>Modified</span><strong>${formatTimestamp(details.modified_at)}</strong></div>
                <div class="result-row"><span>Updated</span><strong>${updated}</strong></div>
            </div>
        `;
    }

    const topImpacted = Array.isArray(details.top_impacted) ? details.top_impacted : [];
    const impactedList = topImpacted.length
        ? `<ul>${topImpacted
            .map((team) => `<li>${escapeHtml(team.team)} · ${team.injury_count} injuries (impact ${Number(team.impact_score ?? 0).toFixed(2)})</li>`)
            .join('')}</ul>`
        : '<p class="form-footnote">No high-impact injuries flagged.</p>';

    return `
        <div class="result-metadata">
            <div class="result-row"><span>Teams with data</span><strong>${details.teams_with_data ?? '—'}</strong></div>
            <div class="result-row"><span>Total injuries</span><strong>${details.total_injuries ?? '—'}</strong></div>
            <div class="result-row"><span>Updated</span><strong>${updated}</strong></div>
        </div>
        <div class="injury-summary">
            <h4>Most impacted</h4>
            ${impactedList}
        </div>
    `;
}

async function fetchHealthStatus() {
    try {
        const data = await request('/api/health');
        updateStatus('api', `OK · ${formatTimestamp(data?.timestamp)}`);
    } catch (error) {
        const message = error instanceof Error ? error.message : 'Unavailable';
        updateStatus('api', `Offline · ${message}`);
    }
}

function updateResult(element, { status, html }) {
    if (!element) return;

    element.classList.remove('is-empty', 'has-success', 'has-error', 'has-info');

    if (status === 'info') {
        element.classList.add('has-info');
        element.textContent = html;
        return;
    }

    if (status === 'error') {
        element.classList.add('has-error');
        element.innerHTML = `<strong>Error:</strong> ${escapeHtml(html)}`;
        return;
    }

    if (status === 'success') {
        element.classList.add('has-success');
        element.innerHTML = html;
        return;
    }

    element.classList.add('is-empty');
    element.textContent = html;
}

function updateStatus(key, value) {
    const el = document.getElementById(`status-${key}`);
    if (el) {
        el.textContent = value;
    }
}

function setLoading(button, isLoading, loadingLabel = 'Working...') {
    if (!button) return;
    if (isLoading) {
        button.dataset.originalLabel = button.dataset.originalLabel ?? button.textContent;
        button.textContent = loadingLabel;
        button.disabled = true;
        button.classList.add('is-loading');
    } else {
        if (button.dataset.originalLabel) {
            button.textContent = button.dataset.originalLabel;
        }
        button.disabled = false;
        button.classList.remove('is-loading');
    }
}

async function request(path, options = {}) {
    const {
        method = 'GET',
        body,
        headers = {},
    } = options;

    const fetchOptions = {
        method,
        headers: {
            ...headers,
        },
    };

    if (body !== undefined) {
        fetchOptions.headers['Content-Type'] = 'application/json';
        fetchOptions.body = typeof body === 'string' ? body : JSON.stringify(body);
    }

    const response = await fetch(`${API_BASE}${path}`, fetchOptions);
    const text = await response.text();
    let payload = null;

    if (text) {
        try {
            payload = JSON.parse(text);
        } catch (error) {
            throw new Error(`Invalid JSON response from ${path}`);
        }
    }

    if (!response.ok) {
        const detail = payload && typeof payload === 'object' && 'detail' in payload
            ? payload.detail
            : response.statusText;
        throw new Error(detail || 'Request failed');
    }

    return payload;
}

function toNumber(value, fallback = NaN) {
    const num = typeof value === 'number' ? value : Number(value);
    return Number.isFinite(num) ? num : fallback;
}

function formatPoints(points) {
    return Number(points).toFixed(1);
}

function formatTimestamp(value) {
    if (!value) return '—';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return value;
    }
    return `${date.toLocaleDateString()} ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
}

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

/* Existing sections for pipeline and scroll animations */
function initPipeline() {
    const steps = document.querySelectorAll('.pipeline-step');
    if (!steps.length) return;

    const detailTitle = document.querySelector('[data-step-title]');
    const detailCopy = document.querySelector('[data-step-copy]');
    const detailList = document.querySelector('[data-step-list]');
    const detailTag = document.querySelector('[data-step-tag]');
    const detailMeta = document.querySelector('[data-step-meta]');

    const stepData = {
        '01': {
            title: 'Async ingestion',
            copy: 'Multiple async workers grab NFL stats, injury updates, betting lines, and NOAA weather snapshots. Each feed is normalized, deduped, and versioned so model runs can rewind any matchup state.',
            bullets: [
                'Rate-limited requests fanned out with retry queues.',
                'Schema validator enforces field parity across seasons.',
                'Slack alerts trigger if any feed drifts or stalls.',
            ],
            tag: 'Ingestion tier • 450 req/min',
            meta: 'Last run 02:14 AM · 34 sources healthy',
        },
        '02': {
            title: 'Feature vault',
            copy: 'A feature store curates drive-level tensors, red-zone efficiency, pass-rush win rates, and cadence shifts. Signals are versioned so historical backtests stay reproducible.',
            bullets: [
                'Windowed aggregates cached in DuckDB + Parquet.',
                'Rest/travel adjustments computed with custom heuristics.',
                'Anomaly detector flags outlier data points before train time.',
            ],
            tag: 'Feature tier • 37 signals tracked',
            meta: 'Last refresh 02:21 AM · 0 anomalies pending review',
        },
        '03': {
            title: 'Model ensemble',
            copy: 'Gradient boosting, calibrated logistic stacks, and Bayesian ridge models collaborate. Each focuses on a different signal family for calibration and scenario testing.',
            bullets: [
                'Weekly hyperparameter sweeps via optuna scheduler.',
                'Validation spans rolling eight-week windows to avoid drift.',
                'Calibration curves logged to compare expected vs. actual.',
            ],
            tag: 'Model tier • 3 ensemble members',
            meta: 'Backtest Week 9 MAE: 2.7 · Brier score: 0.18',
        },
        '04': {
            title: 'Explainability',
            copy: 'SHAP value summaries and rule-based narratives automatically explain why a matchup leans a certain way. Plain-language breakdowns land alongside the numbers.',
            bullets: [
                'Top contributing features rendered as callout bullets.',
                'Contextualizes injuries, weather, and tape-notes overrides.',
                'Supports quick edits before exporting final report.',
            ],
            tag: 'Explainability • Narrative engine v2.3',
            meta: 'Template updated 3 days ago · Localization ready',
        },
        '05': {
            title: 'Report engine',
            copy: 'CLI and PDF output share the same rendering core. Batch runs push to Notion dashboards while analysts can export CSVs for parlay spreadsheets.',
            bullets: [
                'Markdown-to-PDF pipeline with custom React mailer.',
                'Generates bet slip checklist with confidence intervals.',
                'Audit log captures overrides and note history.',
            ],
            tag: 'Delivery • Multi-channel',
            meta: 'Nightly batch complete · 12 reports queued',
        },
    };

    steps.forEach((step) => {
        step.addEventListener('click', () => {
            const key = step.dataset.step;
            if (!key || !stepData[key]) return;

            steps.forEach((btn) => btn.classList.toggle('is-active', btn === step));

            const { title, copy, bullets, tag, meta } = stepData[key];
            if (detailTitle) detailTitle.textContent = title;
            if (detailCopy) detailCopy.textContent = copy;
            if (detailTag) detailTag.textContent = tag;
            if (detailMeta) detailMeta.textContent = meta;

            if (detailList) {
                detailList.innerHTML = '';
                bullets.forEach((bullet) => {
                    const li = document.createElement('li');
                    li.textContent = bullet;
                    detailList.appendChild(li);
                });
            }
        });
    });
}

function initScrollReveal() {
    const observer = new IntersectionObserver(onIntersect, {
        threshold: 0.25,
        rootMargin: '0px 0px -10% 0px',
    });

    document
        .querySelectorAll('.section, .model-card, .stat-card, .report-card, .panel-card')
        .forEach((element) => {
            element.classList.add('is-waiting');
            observer.observe(element);
        });
}

function onIntersect(entries, observer) {
    entries.forEach((entry) => {
        if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            entry.target.classList.remove('is-waiting');
            observer.unobserve(entry.target);
        }
    });
}
