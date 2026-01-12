const API_BASE = window.API_BASE ?? 'http://127.0.0.1:8001';
const state = {
    teams: [],
    lastMatchup: null,
};

document.addEventListener('DOMContentLoaded', () => {
    // Ensure page is interactive
    document.body.style.pointerEvents = 'auto';
    
    initPipeline();
    initScrollReveal();
    initConsole();
    initFantasyHelper();
});

async function getCurrentNFLWeek() {
    // Try to get the current week from ESPN API
    try {
        const currentYear = new Date().getFullYear();
        const response = await fetch(`https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?seasontype=2&week=1&year=${currentYear}`);
        if (response.ok) {
            const data = await response.json();
            // ESPN API returns current week in the response
            if (data.week && data.week.number) {
                return data.week.number;
            }
        }
    } catch (error) {
        console.log('Could not fetch current week from API, using date-based calculation');
    }
    
    // Fallback: Calculate current NFL week based on date
    // NFL regular season typically starts the week after Labor Day (first Monday in September)
    const now = new Date();
    const currentYear = now.getFullYear();
    const currentMonth = now.getMonth() + 1; // 1-12
    const currentDate = now.getDate();
    
    // NFL season starts around early September, Week 1 is typically the first full week
    // Rough estimation based on month
    if (currentMonth < 9) {
        // Before September - likely preseason, default to week 1
        return 1;
    }
    
    // September: weeks 1-4
    // October: weeks 5-9  
    // November: weeks 10-14
    // December: weeks 15-18
    const weekMap = {
        9: 1,   // September - start of season
        10: 5,  // October
        11: 10, // November
        12: 15  // December
    };
    
    if (weekMap[currentMonth]) {
        const baseWeek = weekMap[currentMonth];
        // Add week number based on which week of the month it is (rough estimate)
        const weekOfMonth = Math.min(Math.ceil(currentDate / 7), 4);
        return Math.min(baseWeek + weekOfMonth - 1, 18);
    }
    
    // January or later - likely playoffs, default to week 18
    return 18;
}

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
    fetchDataStatus();
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
        const batchWeekInput = document.getElementById('batch-week');
        const batchSeasonSelect = document.getElementById('batch-season');
        
        // Set default week to current week
        if (batchWeekInput) {
            getCurrentNFLWeek().then(currentWeek => {
                if (currentWeek) {
                    batchWeekInput.value = currentWeek;
                }
            }).catch(() => {
                // Fallback to week 1 if API call fails
                batchWeekInput.value = 1;
            });
        }
        
        // Use native select - more reliable
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

// Custom dropdown component for fixed options (value/label pairs)
function createCustomDropdownForFixedOptions(selectElement, options, defaultValue) {
    if (!selectElement) return null;

    const wrapper = document.createElement('div');
    wrapper.className = 'custom-select-wrapper';
    
    const defaultOption = options.find(opt => opt.value === defaultValue) || options[0];
    const display = document.createElement('div');
    display.className = 'custom-select-display';
    display.textContent = defaultOption.label;
    display.style.backgroundColor = 'rgba(15, 22, 38, 0.9)';
    display.style.color = '#f8fbff';
    
    const dropdown = document.createElement('div');
    dropdown.className = 'custom-select-dropdown';
    dropdown.style.backgroundColor = '#0f1626';
    
    const hiddenInput = document.createElement('input');
    hiddenInput.type = 'hidden';
    hiddenInput.name = selectElement.name || '';
    hiddenInput.value = defaultValue || defaultOption.value;
    
    let isOpen = false;
    let selectedValue = defaultValue || defaultOption.value;
    let selectedText = defaultOption.label;
    
    // Create option elements
    options.forEach((option) => {
        const optionEl = document.createElement('div');
        optionEl.className = 'custom-select-option';
        if (option.value === selectedValue) {
            optionEl.classList.add('selected');
        }
        optionEl.textContent = option.label;
        optionEl.dataset.value = option.value;
        // Force inline styles to ensure visibility
        optionEl.style.backgroundColor = '#0f1626';
        optionEl.style.color = '#f8fbff';
        
        optionEl.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            selectedValue = option.value;
            selectedText = option.label;
            display.textContent = option.label;
            hiddenInput.value = option.value;
            selectElement.value = option.value;
            selectElement.dispatchEvent(new Event('change', { bubbles: true }));
            
            // Update selected state
            dropdown.querySelectorAll('.custom-select-option').forEach(opt => {
                opt.classList.remove('selected');
                opt.style.backgroundColor = '#0f1626';
            });
            optionEl.classList.add('selected');
            optionEl.style.backgroundColor = 'rgba(92, 124, 250, 0.3)';
            
            closeDropdown();
        }, { capture: true });
        
        // Also ensure hover styles are applied
        optionEl.addEventListener('mouseenter', () => {
            optionEl.style.backgroundColor = 'rgba(92, 124, 250, 0.4)';
        });
        optionEl.addEventListener('mouseleave', () => {
            if (!optionEl.classList.contains('selected')) {
                optionEl.style.backgroundColor = '#0f1626';
            }
        });
        
        dropdown.appendChild(optionEl);
    });
    
    function openDropdown() {
        if (isOpen) return;
        isOpen = true;
        wrapper.classList.add('open');
        document.addEventListener('click', handleOutsideClick);
    }
    
    function closeDropdown() {
        if (!isOpen) return;
        isOpen = false;
        wrapper.classList.remove('open');
        document.removeEventListener('click', handleOutsideClick);
    }
    
    function handleOutsideClick(event) {
        // Use setTimeout to avoid conflicts with other click handlers
        setTimeout(() => {
            if (!wrapper.contains(event.target) && isOpen) {
                closeDropdown();
            }
        }, 0);
    }
    
    display.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (isOpen) {
            closeDropdown();
        } else {
            openDropdown();
        }
    }, { capture: true });
    
    wrapper.appendChild(display);
    wrapper.appendChild(dropdown);
    wrapper.appendChild(hiddenInput);
    
    // Replace the select element
    selectElement.style.display = 'none';
    selectElement.parentNode.insertBefore(wrapper, selectElement);
    
    // Sync value when original select changes
    selectElement.addEventListener('change', () => {
        hiddenInput.value = selectElement.value;
        const selectedOpt = options.find(opt => opt.value === selectElement.value);
        if (selectedOpt) {
            selectedText = selectedOpt.label;
            display.textContent = selectedText;
        }
    });
    
    return {
        getValue: () => hiddenInput.value,
        setValue: (value) => {
            const optionEl = dropdown.querySelector(`[data-value="${value}"]`);
            if (optionEl) {
                optionEl.click();
            }
        }
    };
}

// Custom dropdown component
function createCustomDropdown(selectElement, options, placeholder) {
    if (!selectElement) return null;

    const wrapper = document.createElement('div');
    wrapper.className = 'custom-select-wrapper';
    
    const display = document.createElement('div');
    display.className = 'custom-select-display';
    display.textContent = placeholder;
    display.style.backgroundColor = 'rgba(15, 22, 38, 0.9)';
    display.style.color = '#f8fbff';
    
    const dropdown = document.createElement('div');
    dropdown.className = 'custom-select-dropdown';
    dropdown.style.backgroundColor = '#0f1626';
    
    const hiddenInput = document.createElement('input');
    hiddenInput.type = 'hidden';
    hiddenInput.name = selectElement.name || '';
    hiddenInput.value = '';
    
    let isOpen = false;
    let selectedValue = '';
    let selectedText = placeholder;
    
    // Create option elements
    options.forEach((option) => {
        const optionEl = document.createElement('div');
        optionEl.className = 'custom-select-option';
        optionEl.textContent = option;
        optionEl.dataset.value = option;
        
        optionEl.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            selectedValue = option;
            selectedText = option;
            display.textContent = option;
            hiddenInput.value = option;
            selectElement.value = option; // Sync with original select
            selectElement.dispatchEvent(new Event('change', { bubbles: true }));
            
            // Update selected state
            dropdown.querySelectorAll('.custom-select-option').forEach(opt => {
                opt.classList.remove('selected');
                opt.style.backgroundColor = '#0f1626';
            });
            optionEl.classList.add('selected');
            optionEl.style.backgroundColor = 'rgba(92, 124, 250, 0.3)';
            
            closeDropdown();
        }, { capture: true });
        
        // Also ensure hover styles are applied
        optionEl.addEventListener('mouseenter', () => {
            optionEl.style.backgroundColor = 'rgba(92, 124, 250, 0.4)';
        });
        optionEl.addEventListener('mouseleave', () => {
            if (!optionEl.classList.contains('selected')) {
                optionEl.style.backgroundColor = '#0f1626';
            }
        });
        
        dropdown.appendChild(optionEl);
    });
    
    function openDropdown() {
        if (isOpen) return;
        isOpen = true;
        wrapper.classList.add('open');
        document.addEventListener('click', handleOutsideClick);
    }
    
    function closeDropdown() {
        if (!isOpen) return;
        isOpen = false;
        wrapper.classList.remove('open');
        document.removeEventListener('click', handleOutsideClick);
    }
    
    function handleOutsideClick(event) {
        // Use setTimeout to avoid conflicts with other click handlers
        setTimeout(() => {
            if (!wrapper.contains(event.target) && isOpen) {
                closeDropdown();
            }
        }, 0);
    }
    
    display.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (isOpen) {
            closeDropdown();
        } else {
            openDropdown();
        }
    }, { capture: true });
    
    wrapper.appendChild(display);
    wrapper.appendChild(dropdown);
    wrapper.appendChild(hiddenInput);
    
    // Replace the select element
    selectElement.style.display = 'none';
    selectElement.parentNode.insertBefore(wrapper, selectElement);
    
    // Sync value when original select changes
    selectElement.addEventListener('change', () => {
        hiddenInput.value = selectElement.value;
        if (selectElement.value) {
            selectedText = options.find(opt => opt === selectElement.value) || placeholder;
            display.textContent = selectedText;
        }
    });
    
    return {
        getValue: () => hiddenInput.value,
        setValue: (value) => {
            const optionEl = dropdown.querySelector(`[data-value="${value}"]`);
            if (optionEl) {
                optionEl.click();
            }
        }
    };
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
    
    // Use native select - more reliable and responsive
    // Removed custom dropdown for better performance
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

    // Show all predictions, not just 3
    const allPredictions = predictions
        .map((game, index) => formatPredictionHighlight(game, index))
        .join('');

    const failureNote = failed.length
        ? `<p class="form-footnote">${failed.length} game${failed.length > 1 ? 's' : ''} need${failed.length > 1 ? '' : 's'} manual review.</p>`
        : '';

    const predictionsSection = predictions.length
        ? `<div class="injury-summary"><h4>All Predictions (${predictions.length})</h4><div class="predictions-list">${allPredictions}</div></div>`
        : '<p class="form-footnote">No games predicted. Check the data refresh status.</p>';

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
        ${predictionsSection}
        ${failureNote}
    `;

    updateResult(container, { status: 'success', html: content });
}

function formatPredictionHighlight(game, index) {
    const home = escapeHtml(game?.home_team ?? 'Home');
    const away = escapeHtml(game?.away_team ?? 'Away');
    const neutral = game?.is_neutral ? ' [NEUTRAL]' : '';
    const gameNum = `<strong>Game ${index + 1}:</strong>`;
    
    if (typeof game?.home_win_prob === 'number' && typeof game?.away_win_prob === 'number') {
        // ML mode - show probabilities
        const winner = escapeHtml(game?.winner ?? (game.home_win_prob >= game.away_win_prob ? home : away));
        const confidence = toNumber(game?.confidence) || Math.max(game.home_win_prob, game.away_win_prob) * 100;
        const homeProb = (game.home_win_prob * 100).toFixed(1);
        const awayProb = (game.away_win_prob * 100).toFixed(1);
        
        return `
            <div class="prediction-item">
                ${gameNum} ${away} @ ${home}${neutral}
                <div class="prediction-details">
                    <span class="prediction-winner">→ ${winner} wins (${confidence.toFixed(1)}% confidence)</span>
                    <span class="prediction-probs">${home} ${homeProb}% | ${away} ${awayProb}%</span>
                </div>
            </div>
        `;
    }

    if (typeof game?.home_points === 'number' && typeof game?.away_points === 'number') {
        // Heuristic mode - show score prediction
        const winner = game.home_points === game.away_points
            ? 'Toss-up'
            : game.home_points > game.away_points
                ? home
                : away;
        const diff = Math.abs(game.home_points - game.away_points);
        const confidence = Math.min((diff / 6) * 100, 95);
        const homeScore = game.home_points.toFixed(1);
        const awayScore = game.away_points.toFixed(1);
        
        return `
            <div class="prediction-item">
                ${gameNum} ${away} @ ${home}${neutral}
                <div class="prediction-details">
                    <span class="prediction-winner">→ ${winner} wins (${confidence.toFixed(1)}% confidence)</span>
                    <span class="prediction-score">Score: ${home} ${homeScore} - ${awayScore} ${away}</span>
                </div>
            </div>
        `;
    }

    return `<div class="prediction-item">${gameNum} ${away} @ ${home}${neutral}</div>`;
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
        // Refresh data status after updating
        fetchDataStatus();
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
        // Extract just the filename from the full path for better display
        const filePath = details.file ?? 'nflData.txt';
        const fileName = filePath.split(/[/\\]/).pop() || filePath;
        const fullPath = filePath.length > 50 ? `${filePath.substring(0, 47)}...` : filePath;
        
        return `
            <div class="result-metadata">
                <div class="result-row"><span>File</span><strong title="${escapeHtml(filePath)}">${escapeHtml(fileName)}</strong></div>
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

async function fetchDataStatus() {
    try {
        const data = await request('/api/data/status');
        const nflData = data?.nfl_data;
        const injuries = data?.injuries;
        
        // Update refresh card with latest week info
        const refreshCard = document.getElementById('refresh-card');
        if (refreshCard) {
            // Create or update status display
            let statusDisplay = refreshCard.querySelector('.data-status-display');
            if (!statusDisplay) {
                statusDisplay = document.createElement('div');
                statusDisplay.className = 'data-status-display';
                const intro = refreshCard.querySelector('.panel-intro');
                if (intro) {
                    intro.parentNode.insertBefore(statusDisplay, intro.nextSibling);
                }
            }
            
            let statusHTML = '<div class="data-status-info">';
            
            // NFL Data status
            if (nflData?.latest_week && nflData?.season_type) {
                const seasonLabel = nflData.season_type === 'regular' ? 'Regular' : 'Preseason';
                statusHTML += `<div class="status-item"><strong>Latest NFL data:</strong> ${seasonLabel} Week ${nflData.latest_week}</div>`;
            } else if (nflData?.file_exists) {
                statusHTML += '<div class="status-item"><strong>NFL data:</strong> File exists (week unknown)</div>';
            } else {
                statusHTML += '<div class="status-item"><strong>NFL data:</strong> No data file</div>';
            }
            
            // Injuries status
            if (injuries?.file_exists) {
                statusHTML += '<div class="status-item"><strong>Injuries:</strong> Available</div>';
            } else {
                statusHTML += '<div class="status-item"><strong>Injuries:</strong> Not available</div>';
            }
            
            statusHTML += '</div>';
            statusDisplay.innerHTML = statusHTML;
        }
    } catch (error) {
        // Silently fail - status is optional info
        console.log('Could not fetch data status:', error);
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
            title: 'Data collection',
            copy: 'Collect NFL stats, injury updates, and weather data from various sources.',
            bullets: [
                'Automated data collection with error handling.',
                'Data validation ensures consistency.',
                'System monitors data quality.',
            ],
            tag: 'Data collection',
            meta: 'System monitors all sources',
        },
        '02': {
            title: 'Feature processing',
            copy: 'Process team performance metrics, rest days, and travel factors.',
            bullets: [
                'Calculate team statistics and trends.',
                'Factor in rest days and travel.',
                'Identify unusual patterns in data.',
            ],
            tag: 'Processing • 37+ stats tracked',
            meta: 'Data processed and ready',
        },
        '03': {
            title: 'Prediction models',
            copy: 'Multiple models work together to make predictions. Each focuses on different factors.',
            bullets: [
                'Models are trained and updated regularly.',
                'Validation ensures accuracy.',
                'Models are calibrated for reliability.',
            ],
            tag: 'Models • 3 different approaches',
            meta: 'Models tested and validated',
        },
        '04': {
            title: 'Explanations',
            copy: 'Show why each prediction was made. Clear explanations accompany every result.',
            bullets: [
                'Highlight key factors in each prediction.',
                'Explain impact of injuries, weather, and other factors.',
                'Easy to understand summaries.',
            ],
            tag: 'Explanations',
            meta: 'Clear explanations provided',
        },
        '05': {
            title: 'Reports',
            copy: 'Generate predictions and summaries. Export results in various formats.',
            bullets: [
                'Generate detailed prediction reports.',
                'Include confidence levels and key factors.',
                'Export results as needed.',
            ],
            tag: 'Reports',
            meta: 'Reports generated and ready',
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

async function initFantasyHelper() {
    await loadQBRankings();
    await loadTeamOffenseRankings();
}

async function loadQBRankings() {
    const container = document.getElementById('qb-rankings');
    if (!container) return;
    
    try {
        const data = await request('/api/fantasy/qb-rankings');
        const qbs = Array.isArray(data?.qbs) ? data.qbs : [];
        
        if (qbs.length === 0) {
            updateResult(container, { status: 'info', html: 'No QB data available. Refresh game data first.' });
            return;
        }
        
        const topQBs = qbs.slice(0, 15); // Show top 15
        const qbList = topQBs.map((qb, index) => `
            <div class="fantasy-item">
                <div class="fantasy-rank">${index + 1}</div>
                <div class="fantasy-info">
                    <div class="fantasy-name">${escapeHtml(qb.name)} <span class="fantasy-team">(${escapeHtml(qb.team)})</span></div>
                    <div class="fantasy-stats">
                        <span>${qb.avg_yards} yds/g</span>
                        <span>${qb.avg_tds} TD/g</span>
                        <span>${qb.avg_ints} INT/g</span>
                        <span class="fantasy-score">Score: ${qb.fantasy_score}</span>
                    </div>
                </div>
            </div>
        `).join('');
        
        const html = `
            <div class="fantasy-list">${qbList}</div>
            <p class="form-footnote">Based on recent performance. Score = (Yards/25) + (TDs×4) - (INTs×2)</p>
        `;
        
        updateResult(container, { status: 'success', html });
    } catch (error) {
        const message = error instanceof Error ? error.message : 'Failed to load QB rankings';
        updateResult(container, { status: 'error', html: message });
    }
}

async function loadTeamOffenseRankings() {
    const container = document.getElementById('team-offense');
    if (!container) return;
    
    try {
        const data = await request('/api/fantasy/team-offense');
        const rbRankings = Array.isArray(data?.rb_rankings) ? data.rb_rankings : [];
        const wrRankings = Array.isArray(data?.wr_rankings) ? data.wr_rankings : [];
        
        if (rbRankings.length === 0 && wrRankings.length === 0) {
            updateResult(container, { status: 'info', html: 'No team data available. Refresh game data first.' });
            return;
        }
        
        const rbList = rbRankings.map((team, index) => `
            <div class="fantasy-item">
                <div class="fantasy-rank">${index + 1}</div>
                <div class="fantasy-info">
                    <div class="fantasy-name">${escapeHtml(team.team)}</div>
                    <div class="fantasy-stats">
                        <span>${team.avg_rushing_yds} rush yds/g</span>
                        <span>${team.avg_points} pts/g</span>
                    </div>
                </div>
            </div>
        `).join('');
        
        const wrList = wrRankings.map((team, index) => `
            <div class="fantasy-item">
                <div class="fantasy-rank">${index + 1}</div>
                <div class="fantasy-info">
                    <div class="fantasy-name">${escapeHtml(team.team)}</div>
                    <div class="fantasy-stats">
                        <span>${team.avg_passing_yds} pass yds/g</span>
                        <span>${team.avg_points} pts/g</span>
                    </div>
                </div>
            </div>
        `).join('');
        
        const html = `
            <div class="fantasy-section">
                <h4>Top teams for RBs</h4>
                <div class="fantasy-list">${rbList}</div>
            </div>
            <div class="fantasy-section" style="margin-top: 20px;">
                <h4>Top teams for WRs</h4>
                <div class="fantasy-list">${wrList}</div>
            </div>
        `;
        
        updateResult(container, { status: 'success', html });
    } catch (error) {
        const message = error instanceof Error ? error.message : 'Failed to load team rankings';
        updateResult(container, { status: 'error', html: message });
    }
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
