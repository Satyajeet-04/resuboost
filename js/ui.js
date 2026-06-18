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

  function renderCoverLetter(data) {
    const el = $('#cover-letter-result');
    if (!el) return;
    el.classList.remove('hidden');

    const textEl = $('#cover-letter-text');
    if (textEl) textEl.textContent = data.cover_letter;

    const subjectEl = $('#cover-letter-subject');
    if (subjectEl && data.subject_line) subjectEl.textContent = `Subject: ${data.subject_line}`;

    const pointsEl = $('#cover-letter-points');
    if (pointsEl && data.key_points && data.key_points.length) {
      pointsEl.innerHTML = data.key_points.map(p => `<li>${escapeHtml(p)}</li>`).join('');
    }
  }

  function renderKeywords(data) {
    const el = $('#keywords-result');
    if (!el) return;
    el.classList.remove('hidden');

    const statsEl = $('#keyword-stats');
    if (statsEl && data.stats) {
      const s = data.stats;
      const pct = s.coverage_pct || 0;
      statsEl.innerHTML = `
        <div class="keyword-stat-row">
          <span>Coverage</span>
          <span style="font-weight:700;font-size:1.2rem;color:${pct >= 70 ? '#22c55e' : pct >= 40 ? '#eab308' : '#ef4444'}">${pct}%</span>
        </div>
        <div class="keyword-stat-row">
          <span>Matched</span><span>${s.matched || 0} / ${s.total_keywords || 0}</span>
        </div>
        <div class="keyword-stat-row">
          <span>Missing</span><span style="color:#ef4444">${s.missing || 0}</span>
        </div>
      `;
    }

    const listEl = $('#keyword-list');
    if (listEl && data.keywords) {
      listEl.innerHTML = data.keywords.map(k => `
        <div class="keyword-item ${k.in_resume ? 'kw-present' : 'kw-missing'}">
          <div class="keyword-name">
            <span class="badge ${k.importance === 'high' ? 'badge-red' : k.importance === 'medium' ? 'badge-yellow' : 'badge-green'}">${k.importance}</span>
            ${escapeHtml(k.keyword)}
            <span class="kw-status">${k.in_resume ? '✅' : '❌'}</span>
          </div>
          ${k.suggestion ? `<div class="keyword-suggestion">${escapeHtml(k.suggestion)}</div>` : ''}
        </div>
      `).join('');
    }

    if (data.recommendation) {
      const recEl = $('#keyword-recommendation');
      if (recEl) recEl.textContent = data.recommendation;
    }
  }

  function renderScore(data) {
    const el = $('#score-result');
    if (!el) return;
    el.classList.remove('hidden');

    const overallEl = $('#score-overall');
    if (overallEl) {
      const s = data.overall_score || 0;
      overallEl.textContent = `${s}/100`;
      overallEl.style.color = s >= 70 ? '#22c55e' : s >= 40 ? '#eab308' : '#ef4444';
    }

    const scoresList = $('#scores-list');
    if (scoresList && data.scores) {
      scoresList.innerHTML = data.scores.map(sc => `
        <div class="score-category-row">
          <div class="score-category-header">
            <span style="font-weight:600">${escapeHtml(sc.category)}</span>
            <span style="font-weight:700;color:${sc.score >= 70 ? '#22c55e' : sc.score >= 40 ? '#eab308' : '#ef4444'}">${sc.score}/${sc.max_score || 100}</span>
          </div>
          <div class="progress-bar" style="height:8px;margin:4px 0">
            <div class="progress-fill" style="width:${sc.score}%;height:8px;background:${sc.score >= 70 ? '#22c55e' : sc.score >= 40 ? '#eab308' : '#ef4444'}"></div>
          </div>
          <p style="font-size:0.85rem;color:#666;margin:2px 0">${escapeHtml(sc.reason)}</p>
          ${sc.tip ? `<p style="font-size:0.85rem;color:#0891b2;margin:2px 0">💡 ${escapeHtml(sc.tip)}</p>` : ''}
        </div>
      `).join('');
    }

    const strengthsEl = $('#score-strengths');
    if (strengthsEl && data.strengths) {
      strengthsEl.innerHTML = data.strengths.map(s => `<li>${escapeHtml(s)}</li>`).join('');
    }

    const weaknessesEl = $('#score-weaknesses');
    if (weaknessesEl && data.weaknesses) {
      weaknessesEl.innerHTML = data.weaknesses.map(s => `<li>${escapeHtml(s)}</li>`).join('');
    }

    const fixesEl = $('#score-fixes');
    if (fixesEl && data.priority_fixes) {
      fixesEl.innerHTML = data.priority_fixes.map(s => `<li>${escapeHtml(s)}</li>`).join('');
    }
  }

  function renderInterviewQuestions(data) {
    const el = $('#questions-result');
    if (!el) return;
    el.classList.remove('hidden');

    const listEl = $('#questions-list');
    if (listEl && data.questions) {
      listEl.innerHTML = data.questions.map((q, i) => {
        const diffColor = q.difficulty === 'hard' ? '#ef4444' : q.difficulty === 'medium' ? '#eab308' : '#22c55e';
        return `
          <div class="question-card">
            <div class="question-header">
              <span class="question-number">Q${i + 1}</span>
              <span class="badge badge-${q.category === 'technical' ? 'red' : q.category === 'behavioral' ? 'yellow' : 'green'}">${escapeHtml(q.category || 'general')}</span>
              <span style="color:${diffColor};font-size:0.8rem;font-weight:600">${escapeHtml(q.difficulty || 'medium')}</span>
            </div>
            <p class="question-text">${escapeHtml(q.question)}</p>
            <p class="question-why"><strong>Why this is asked:</strong> ${escapeHtml(q.why_asked || '')}</p>
            ${q.preparation_tip ? `<p class="question-tip"><strong>💡 Tip:</strong> ${escapeHtml(q.preparation_tip)}</p>` : ''}
          </div>
        `;
      }).join('');
    }
  }

  function renderAtsBreakdown(data) {
    const el = $('#ats-result');
    if (!el) return;
    el.classList.remove('hidden');

    const result = data.result || data;

    const scoreEl = $('#ats-platform-score');
    if (scoreEl) {
      const s = result.overall_score || 0;
      scoreEl.textContent = `${s}/100`;
      scoreEl.style.color = s >= 70 ? '#22c55e' : s >= 40 ? '#eab308' : '#ef4444';
    }

    // Parseability
    const parseEl = $('#ats-parseability');
    if (parseEl && result.parseability) {
      const p = result.parseability;
      parseEl.innerHTML = `
        <div class="ats-metric">
          <span style="font-weight:600">Parseability</span>
          <span style="color:${p.score >= 70 ? '#22c55e' : '#eab308'}">${p.score}/100</span>
        </div>
        ${p.issues && p.issues.length ? `<ul class="ats-issues">${p.issues.map(i => `<li>${escapeHtml(i)}</li>`).join('')}</ul>` : '<p style="font-size:0.85rem;color:#22c55e">No parseability issues</p>'}
      `;
    }

    // Keyword match
    const kwEl = $('#ats-keywords');
    if (kwEl && result.keyword_match) {
      const km = result.keyword_match;
      kwEl.innerHTML = `
        <div class="ats-metric">
          <span style="font-weight:600">Keyword Match</span>
          <span style="color:${km.score >= 70 ? '#22c55e' : '#eab308'}">${km.score}/100</span>
        </div>
        ${km.matched && km.matched.length ? `<p style="font-size:0.85rem;margin:4px 0"><strong>Found:</strong> ${km.matched.join(', ')}</p>` : ''}
        ${km.missing && km.missing.length ? `<p style="font-size:0.85rem;margin:4px 0;color:#ef4444"><strong>Missing:</strong> ${km.missing.join(', ')}</p>` : ''}
      `;
    }

    // Section compatibility
    const secEl = $('#ats-sections');
    if (secEl && result.section_compatibility) {
      const sc = result.section_compatibility;
      secEl.innerHTML = `
        <div class="ats-metric">
          <span style="font-weight:600">Sections</span>
          <span style="color:${sc.clean ? '#22c55e' : '#ef4444'}">${sc.clean ? '✅ Compatible' : '⚠️ Issues'}</span>
        </div>
        ${sc.warning ? `<p style="font-size:0.85rem;color:#eab308">${escapeHtml(sc.warning)}</p>` : ''}
        ${sc.issues && sc.issues.length ? `<ul class="ats-issues">${sc.issues.map(i => `<li>${escapeHtml(i)}</li>`).join('')}</ul>` : ''}
      `;
    }

    // Specific feedback
    const feedbackEl = $('#ats-feedback');
    if (feedbackEl && result.specific_feedback) {
      feedbackEl.textContent = result.specific_feedback;
    }

    // Action items
    const actionEl = $('#ats-actions');
    if (actionEl && result.action_items) {
      actionEl.innerHTML = result.action_items.map(a => `<li>${escapeHtml(a)}</li>`).join('');
    }

    // Platform name
    const nameEl = $('#ats-platform-name');
    if (nameEl && result.platform) {
      nameEl.textContent = `ATS: ${result.platform.charAt(0).toUpperCase() + result.platform.slice(1)}`;
    }
  }

  function renderShortlistLoading() {
    const badgeEl = $('#shortlist-badge');
    if (badgeEl) {
      badgeEl.style.background = '#fefce8';
      badgeEl.style.border = '2px solid #eab308';
    }
    const iconEl = $('#shortlist-badge-icon');
    if (iconEl) iconEl.textContent = '⏳';
    const textEl = $('#shortlist-badge-text');
    if (textEl) textEl.textContent = 'Generating Shortlist Resume...';
    const scoreEl = $('#shortlist-score');
    if (scoreEl) scoreEl.textContent = '--/100';
    const barEl = $('#shortlist-progress-bar');
    if (barEl) barEl.style.width = '0%';
    const container = $('#shortlist-resume-container');
    if (container) container.classList.add('hidden');
    const iterEl = $('#shortlist-iterations');
    if (iterEl) iterEl.innerHTML = '<p style="color:#666">Running verification loop...</p>';
  }

  function renderShortlistResult(data) {
    const isVerified = data.shortlist_verified;
    const finalScore = data.final_score || 0;

    // Badge
    const badgeEl = $('#shortlist-badge');
    if (badgeEl) {
      if (isVerified) {
        badgeEl.style.background = '#f0fdf4';
        badgeEl.style.border = '2px solid #22c55e';
      } else {
        badgeEl.style.background = '#fefce8';
        badgeEl.style.border = '2px solid #eab308';
      }
    }

    const iconEl = $('#shortlist-badge-icon');
    if (iconEl) iconEl.textContent = isVerified ? '✅' : '⚠️';

    const textEl = $('#shortlist-badge-text');
    if (textEl) {
      textEl.textContent = isVerified
        ? 'SHORTLIST VERIFIED — Ready for Round 1'
        : `Score: ${finalScore}/100 — Consider manual review`;
      textEl.style.color = isVerified ? '#16a34a' : '#ca8a04';
    }

    const scoreEl = $('#shortlist-score');
    if (scoreEl) {
      scoreEl.textContent = `${finalScore}/100`;
      scoreEl.style.color = isVerified ? '#22c55e' : '#eab308';
    }

    const barEl = $('#shortlist-progress-bar');
    if (barEl) {
      barEl.style.width = `${finalScore}%`;
      barEl.style.backgroundColor = isVerified ? '#22c55e' : '#eab308';
    }

    // Iterations
    const iterEl = $('#shortlist-iterations');
    if (iterEl && data.iterations) {
      iterEl.innerHTML = data.iterations.map(iter => {
        const passed = iter.score >= 85;
        return `
          <div style="display:flex;align-items:center;gap:12px;padding:8px 12px;margin-bottom:8px;background:${passed ? '#f0fdf4' : '#fefce8'};border-radius:8px;border-left:4px solid ${passed ? '#22c55e' : '#eab308'}">
            <span style="font-weight:700;font-size:0.9rem;min-width:80px">Iter ${iter.iteration}</span>
            <div style="flex:1">
              <div style="display:flex;justify-content:space-between;align-items:center">
                <span style="font-size:0.85rem">Score: <strong style="color:${iter.score >= 85 ? '#16a34a' : '#ca8a04'}">${iter.score}/100</strong></span>
                <span style="font-size:0.8rem;color:#666">${iter.remaining_weaknesses || 0} weaknesses</span>
              </div>
              <div class="progress-bar" style="height:6px;margin:4px 0">
                <div class="progress-fill" style="width:${iter.score}%;height:6px;background:${iter.score >= 85 ? '#22c55e' : '#eab308'}"></div>
              </div>
            </div>
            <span style="font-size:1.2rem">${passed ? '✅' : '🔄'}</span>
          </div>
        `;
      }).join('');
    }

    // Resume text
    const resumeEl = $('#shortlist-resume-text');
    if (resumeEl && data.resume) {
      resumeEl.textContent = data.resume;
    }

    // Changes
    const changesEl = $('#shortlist-changes');
    if (changesEl && data.changes_summary) {
      changesEl.textContent = data.changes_summary;
    }

    // Show container
    const container = $('#shortlist-resume-container');
    if (container) container.classList.remove('hidden');

    // Reset disclaimer checkbox
    const agreeCheck = $('#shortlist-agree-check');
    if (agreeCheck) agreeCheck.checked = false;
    const dlBtn = $('#shortlist-download-btn');
    if (dlBtn) {
      dlBtn.disabled = true;
      dlBtn.textContent = '✅ Agree to Terms to Download';
    }
  }

  return { show, setLoading, renderGaps, renderRewrite, renderFullRewrite, renderSimulation, renderCoverLetter, renderKeywords, renderScore, renderInterviewQuestions, renderAtsBreakdown, renderShortlistLoading, renderShortlistResult, showError, hideError, escapeHtml };
})();
