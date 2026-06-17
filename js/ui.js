const ui = (() => {
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  function show(elementId) {
    document.querySelectorAll('.step').forEach(el => el.classList.add('hidden'));
    const el = $(`#${elementId}`);
    if (el) el.classList.remove('hidden');
  }

  function setLoading(buttonId, loading) {
    const btn = $(`#${buttonId}`);
    if (!btn) return;
    if (loading) {
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner"></span> Processing...';
    } else {
      btn.disabled = false;
      btn.innerHTML = btn.dataset.originalText || btn.textContent;
    }
  }

  function renderGaps(gaps, matchScore) {
    const container = $('#gap-list');
    if (!container) return;
    container.innerHTML = '';

    const scoreEl = $('#match-score');
    if (scoreEl) {
      const color = matchScore >= 80 ? '#22c55e' : matchScore >= 50 ? '#eab308' : '#ef4444';
      scoreEl.textContent = `${matchScore}%`;
      scoreEl.style.color = color;
    }

    if (!gaps || gaps.length === 0) {
      container.innerHTML = '<div class="gap-card gap-high"><p>No significant gaps found. Your resume aligns well with this role!</p></div>';
      return;
    }

    gaps.forEach((gap, idx) => {
      const badge = { high: 'Critical', medium: 'Important', low: 'Nice-to-have' };
      const badgeColor = { high: 'badge-red', medium: 'badge-yellow', low: 'badge-green' };

      const card = document.createElement('div');
      card.className = `gap-card gap-${gap.importance}`;
      card.innerHTML = `
        <div class="gap-header">
          <span class="skill-name">${escapeHtml(gap.skill)}</span>
          <span class="badge ${badgeColor[gap.importance]}">${badge[gap.importance]}</span>
        </div>
        <p class="gap-reason">${escapeHtml(gap.reason)}</p>
        <button class="btn btn-primary btn-sm rewrite-btn" data-skill="${escapeHtml(gap.skill)}">
          Rewrite for this gap
        </button>
      `;
      container.appendChild(card);
    });

    container.querySelectorAll('.rewrite-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const skill = btn.dataset.skill;
        app.rewrite(skill);
      });
    });
  }

  function renderRewrite(original, rewritten, explanation) {
    const container = $('#rewrite-result');
    if (!container) return;
    container.classList.remove('hidden');

    const originalList = $('#original-bullets');
    const rewrittenList = $('#rewritten-bullets');
    const explanationEl = $('#rewrite-explanation');

    if (originalList) {
      originalList.innerHTML = original.map(b => `<li>${escapeHtml(b)}</li>`).join('');
    }
    if (rewrittenList) {
      rewrittenList.innerHTML = rewritten.map(b => `<li>${escapeHtml(b)}</li>`).join('');
    }
    if (explanationEl) {
      explanationEl.textContent = explanation;
    }
  }

  function renderSimulation(queries, matchRate) {
    const container = $('#simulation-table tbody');
    if (!container) return;
    container.innerHTML = '';

    const rateEl = $('#match-rate');
    if (rateEl) {
      rateEl.textContent = `${matchRate}%`;
      const color = matchRate >= 70 ? '#22c55e' : matchRate >= 40 ? '#eab308' : '#ef4444';
      rateEl.style.color = color;
    }

    const bar = $('#match-bar');
    if (bar) {
      bar.style.width = `${matchRate}%`;
      bar.style.backgroundColor = matchRate >= 70 ? '#22c55e' : matchRate >= 40 ? '#eab308' : '#ef4444';
    }

    queries.forEach(q => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td><code>${escapeHtml(q.query)}</code></td>
        <td class="${q.match ? 'match-yes' : 'match-no'}">${q.match ? 'YES' : 'NO'}</td>
        <td>${escapeHtml(q.why)}</td>
      `;
      container.appendChild(row);
    });
  }

  function renderFullRewrite(fullResume, changesSummary) {
    const container = $('#full-rewrite-result');
    if (!container) return;
    container.classList.remove('hidden');

    const resumeEl = $('#full-rewrite-text');
    if (resumeEl) {
      resumeEl.textContent = fullResume;
    }

    const changesEl = $('#full-rewrite-changes');
    if (changesEl) {
      changesEl.innerHTML = changesSummary
        ? changesSummary.split('\n').filter(l => l.trim()).map(l => `<li>${escapeHtml(l.replace(/^[-*]\s*/, ''))}</li>`).join('')
        : '<li>Full resume rewritten to better match the target role</li>';
    }
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function showError(message) {
    const el = $('#error-message');
    if (!el) return;
    el.textContent = message;
    el.classList.remove('hidden');
    setTimeout(() => el.classList.add('hidden'), 8000);
  }

  function hideError() {
    const el = $('#error-message');
    if (el) el.classList.add('hidden');
  }

  return { show, setLoading, renderGaps, renderRewrite, renderFullRewrite, renderSimulation, showError, hideError, escapeHtml };
})();
