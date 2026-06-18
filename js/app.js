window.app = (() => {
  const state = {
    resumeText: null, resumeFile: null, jdText: null, role: null,
    gaps: null, matchScore: 0, rewriteResult: null, simulation: null,
    shortlistResult: null, currentStep: 'hero',
    templates: null, recommendations: null
  };

  function init() {
    setupFileUpload();
    setupEventListeners();
    checkForJDInClipboard();
    loadTemplates();
  }

  function nav(section) {
    document.querySelectorAll('.page-section').forEach(el => el.classList.add('hidden'));
    const target = document.getElementById(section);
    if (target) target.classList.remove('hidden');
    document.querySelectorAll('.nav-links a').forEach(a => a.classList.remove('active'));
    const link = document.querySelector(`.nav-links a[data-section="${section}"]`);
    if (link) link.classList.add('active');
    state.currentStep = section;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  async function loadTemplates() {
    try {
      const res = await api.client.getTemplates();
      state.templates = res.templates || [];
      if (state.templates.length) {
        renderTemplateGrid(state.templates);
        renderTemplateGridFull(state.templates);
      }
    } catch { /* non-critical */ }
  }

  function setupFileUpload() {
    const dz = document.getElementById('drop-zone');
    const fi = document.getElementById('file-input');
    const bb = document.getElementById('browse-btn');
    if (!dz || !fi) return;
    bb?.addEventListener('click', () => fi.click());
    fi.addEventListener('change', async e => { const f = e.target.files[0]; if (f) await handleFile(f); });
    dz.addEventListener('dragover', e => { e.preventDefault(); dz.classList.add('drag-over'); });
    dz.addEventListener('dragleave', () => dz.classList.remove('drag-over'));
    dz.addEventListener('drop', e => { e.preventDefault(); dz.classList.remove('drag-over'); const f = e.dataTransfer.files[0]; if (f) handleFile(f); });
  }

  async function handleFile(file) {
    ui.hideError();
    if (!file.name.toLowerCase().endsWith('.pdf')) { ui.showError('Only PDF files are supported.'); return; }
    if (file.size > CONFIG.MAX_FILE_SIZE) { ui.showError('File is too large. Maximum 5MB.'); return; }
    state.resumeFile = file;
    document.getElementById('file-info').textContent = `${file.name} (${(file.size / 1024).toFixed(0)} KB)`;
    try {
      const text = await parser.extractTextFromPDF(file);
      if (!text || text.length < 50) {
        document.getElementById('extracted-text-container').classList.remove('hidden');
        document.getElementById('extracted-text').value = '';
        ui.showError('This PDF appears to be scanned or image-based. Please paste your resume text manually.');
        return;
      }
      state.resumeText = text;
      document.getElementById('extracted-text-container').classList.remove('hidden');
      document.getElementById('extracted-text').value = text;
    } catch (err) {
      if (err.message?.includes('password')) ui.showError('This PDF is password-protected. Please remove the password first.');
      else ui.showError('Could not parse this PDF. Please paste your resume text manually.');
      document.getElementById('extracted-text-container').classList.remove('hidden');
      document.getElementById('extracted-text').value = '';
    }
  }

  function setupEventListeners() {
    // Nav
    document.querySelectorAll('.nav-links a[data-section]').forEach(a => {
      a.addEventListener('click', e => { e.preventDefault(); nav(a.dataset.section); });
    });

    // Hero CTA
    document.getElementById('hero-cta')?.addEventListener('click', () => nav('step-upload'));

    // Upload → JD
    document.getElementById('to-jd-btn')?.addEventListener('click', () => {
      const ta = document.getElementById('extracted-text');
      if (ta && ta.value.trim()) state.resumeText = ta.value.trim();
      if (!state.resumeText) { ui.showError('Please upload a resume or paste text first.'); return; }
      nav('step-jd');
    });

    document.getElementById('analyze-btn')?.addEventListener('click', analyze);
    document.getElementById('simulate-btn')?.addEventListener('click', simulate);
    document.getElementById('cover-letter-btn')?.addEventListener('click', generateCoverLetter);
    document.getElementById('keywords-btn')?.addEventListener('click', analyzeKeywords);
    document.getElementById('score-btn')?.addEventListener('click', scoreResume);
    document.getElementById('questions-btn')?.addEventListener('click', generateQuestions);
    document.getElementById('ats-breakdown-btn')?.addEventListener('click', atsBreakdown);
    document.getElementById('shortlist-btn')?.addEventListener('click', shortlist);
    document.getElementById('full-rewrite-btn')?.addEventListener('click', fullRewrite);

    // Recommend templates
    document.getElementById('rec-template-btn')?.addEventListener('click', recommendTemplate);
    document.getElementById('template-rec-btn-page')?.addEventListener('click', recommendTemplateFromPage);

    // Smart recommendations
    document.getElementById('recommend-btn')?.addEventListener('click', smartRecommend);

    // Shortlist downloads
    document.getElementById('shortlist-agree-check')?.addEventListener('change', e => {
      const btn = document.getElementById('shortlist-download-btn');
      if (btn) btn.disabled = !e.target.checked;
    });
    document.getElementById('shortlist-download-btn')?.addEventListener('click', () => {
      const text = document.getElementById('shortlist-resume-text')?.textContent;
      if (!text) return;
      const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url; a.download = 'resuboost-shortlist-resume.txt'; a.click();
      URL.revokeObjectURL(url);
    });

    document.querySelectorAll('.back-to-analyze-btn').forEach(btn => btn.addEventListener('click', () => nav('step-analyze')));
    document.getElementById('copy-rewrite')?.addEventListener('click', () => {
      const bullets = document.querySelectorAll('#rewritten-bullets li');
      const text = Array.from(bullets).map(li => li.textContent).join('\n');
      navigator.clipboard.writeText(text).then(() => { const b = document.getElementById('copy-rewrite'); b.textContent = 'Copied!'; setTimeout(() => { b.textContent = 'Copy to Clipboard'; }, 2000); });
    });

    // Download rewritten
    document.getElementById('download-txt')?.addEventListener('click', () => {
      const text = document.getElementById('full-rewrite-text')?.textContent;
      if (!text) return;
      const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url; a.download = 'resuboost-rewritten-resume.txt'; a.click();
      URL.revokeObjectURL(url);
    });

    document.getElementById('download-pdf')?.addEventListener('click', () => {
      const text = document.getElementById('full-rewrite-text')?.textContent;
      if (!text) return;
      const safeText = ui.escapeHtml(text);
      const printWin = window.open('', '_blank', 'width=800,height=600');
      if (!printWin) { ui.showError('Popup blocked. Please allow popups or use Copy to Clipboard.'); return; }
      printWin.document.write('<!DOCTYPE html><html><head><title>ResuBoost - Rewritten Resume</title>' +
        '<style>body{font-family:Calibri,Arial,sans-serif;font-size:12pt;line-height:1.5;max-width:800px;margin:0.5in auto;padding:0 20px}' +
        'pre{white-space:pre-wrap;font-family:Calibri,Arial,sans-serif;font-size:12pt;line-height:1.5;border:none;background:white;color:black;padding:0;margin:0;overflow:visible;max-height:none}' +
        '.footer{font-size:9pt;color:#999;text-align:center;margin-top:30px;border-top:1px solid #ddd;padding-top:10px}' +
        '@media print{body{margin:0.5in}}' +
        '</style></head><body><pre>' + safeText + '</pre>' +
        '<div class="footer">Generated by ResuBoost</div>' +
        '<script>window.onload=function(){window.print();window.close()};<' + '/script></body></html>');
      printWin.document.close();
    });

    document.getElementById('download-cover-letter')?.addEventListener('click', () => {
      const text = document.getElementById('cover-letter-text')?.textContent;
      if (!text) return;
      const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url; a.download = 'cover-letter.txt'; a.click();
      URL.revokeObjectURL(url);
    });

    document.getElementById('ats-platform-select')?.addEventListener('change', e => { state.selectedAtsPlatform = e.target.value; });
  }

  async function recommendTemplate() {
    if (!state.resumeText) { ui.showError('Please upload a resume first.'); return; }
    ui.hideError();
    ui.setLoading('rec-template-btn', true);
    try {
      const result = await api.client.recommendTemplate(state.resumeText, state.jdText || '');
      ui.renderTemplateRecommendation(result);
      document.getElementById('template-rec-result')?.classList.remove('hidden');
    } catch (err) {
      ui.showError(err instanceof api.RateLimitError ? '⚠️ Rate limit. Wait 30-60s.' : `Recommendation failed: ${err.message}`);
    } finally { ui.setLoading('rec-template-btn', false); }
  }

  async function recommendTemplateFromPage() {
    const resume = document.getElementById('template-resume-input')?.value.trim();
    const jd = document.getElementById('template-jd-input')?.value.trim();
    if (!resume) { ui.showError('Please paste your resume text.'); return; }
    ui.hideError();
    ui.setLoading('template-rec-btn-page', true);
    try {
      const result = await api.client.recommendTemplate(resume, jd || '');
      const container = document.getElementById('template-rec-result-page');
      if (container) {
        container.classList.remove('hidden');
        // Use a temp state to render
        ui.renderTemplateRecommendation(result);
        container.innerHTML = document.getElementById('template-rec-result').innerHTML;
      }
    } catch (err) {
      ui.showError(err instanceof api.RateLimitError ? '⚠️ Rate limit. Wait 30-60s.' : `Recommendation failed: ${err.message}`);
    } finally { ui.setLoading('template-rec-btn-page', false); }
  }

  async function smartRecommend() {
    if (!state.resumeText || !state.jdText) { ui.showError('Please upload a resume and JD first.'); return; }
    ui.hideError();
    ui.setLoading('recommend-btn', true);
    try {
      const result = await api.client.recommend(state.resumeText, state.jdText);
      state.recommendations = result;
      ui.renderSmartRecommendations(result);
      nav('step-recommendations');
    } catch (err) {
      ui.showError(err instanceof api.RateLimitError ? '⚠️ Rate limit. Wait 30-60s.' : `Recommendations failed: ${err.message}`);
    } finally { ui.setLoading('recommend-btn', false); }
  }

  async function analyze() {
    ui.hideError();
    const jdTextarea = document.getElementById('jd-input');
    const jdText = jdTextarea?.value.trim();
    state.jdText = jdText;
    const roleInput = document.getElementById('role-input');
    state.role = roleInput?.value.trim() || '';
    if (!jdText) { ui.showError('Please paste a job description.'); return; }
    ui.setLoading('analyze-btn', true);
    nav('step-analyze');
    try {
      const result = await api.client.analyze(state.resumeText, jdText);
      state.gaps = result.gaps;
      state.matchScore = result.match_score;
      ui.renderGaps(result.gaps, result.match_score);
    } catch (err) {
      if (err instanceof api.RateLimitError) ui.showError('⚠️ Rate limit reached. Please wait 30-60 seconds and try again.');
      else ui.showError(`Analysis failed: ${err.message}`);
      nav('step-jd');
    } finally { ui.setLoading('analyze-btn', false); }
  }

  async function rewrite(skill) {
    ui.hideError();
    ui.setLoading('analyze-btn', true);
    try {
      const result = await api.client.rewrite(state.resumeText, skill, state.jdText);
      state.rewriteResult = result;
      ui.renderRewrite(result.original, result.rewritten, result.explanation);
      nav('step-rewrite');
    } catch (err) {
      if (err instanceof api.RateLimitError) ui.showError('⚠️ Rate limit reached. Please wait 30-60 seconds, then try again.');
      else ui.showError(`Rewrite failed: ${err.message}`);
    } finally { ui.setLoading('analyze-btn', false); }
  }

  async function simulate() {
    ui.hideError();
    const role = state.role || document.getElementById('role-input')?.value.trim();
    if (!role) { ui.showError('Please enter a target role.'); return; }
    ui.setLoading('simulate-btn', true);
    try {
      const result = await api.client.simulate(state.resumeText, role);
      state.simulation = result;
      ui.renderSimulation(result.queries, result.match_rate);
      nav('step-simulate');
    } catch (err) {
      if (err instanceof api.RateLimitError) ui.showError('⚠️ Rate limit reached. Please wait 30-60 seconds, then try again.');
      else ui.showError(`Simulation failed: ${err.message}`);
    } finally { ui.setLoading('simulate-btn', false); }
  }

  async function shortlist() {
    ui.hideError();
    const aggressiveMode = document.getElementById('shortlist-mode-toggle')?.checked || false;
    if (!state.jdText) { ui.showError('Please paste a job description first.'); return; }
    ui.setLoading('shortlist-btn', true);
    nav('step-shortlist');
    ui.renderShortlistLoading();
    try {
      const result = await api.client.shortlist(state.resumeText, state.jdText, aggressiveMode);
      state.shortlistResult = result;
      ui.renderShortlistResult(result);
    } catch (err) {
      if (err instanceof api.RateLimitError) ui.showError('⚠️ Rate limit reached. Please wait 30-60 seconds, then try again.');
      else ui.showError(`Shortlist failed: ${err.message}`);
      nav('step-analyze');
    } finally { ui.setLoading('shortlist-btn', false); }
  }

  async function generateCoverLetter() {
    ui.hideError();
    ui.setLoading('cover-letter-btn', true);
    try {
      const result = await api.client.coverLetter(state.resumeText, state.jdText);
      ui.renderCoverLetter(result);
      nav('step-cover-letter');
    } catch (err) {
      ui.showError(err instanceof api.RateLimitError ? '⚠️ Rate limit. Wait 30-60s.' : `Cover letter failed: ${err.message}`);
    } finally { ui.setLoading('cover-letter-btn', false); }
  }

  async function analyzeKeywords() {
    ui.hideError();
    ui.setLoading('keywords-btn', true);
    try {
      const result = await api.client.keywords(state.resumeText, state.jdText);
      ui.renderKeywords(result);
      nav('step-keywords');
    } catch (err) {
      ui.showError(err instanceof api.RateLimitError ? '⚠️ Rate limit. Wait 30-60s.' : `Keyword analysis failed: ${err.message}`);
    } finally { ui.setLoading('keywords-btn', false); }
  }

  async function scoreResume() {
    ui.hideError();
    ui.setLoading('score-btn', true);
    try {
      const result = await api.client.score(state.resumeText, state.jdText);
      ui.renderScore(result);
      nav('step-score');
    } catch (err) {
      ui.showError(err instanceof api.RateLimitError ? '⚠️ Rate limit. Wait 30-60s.' : `Scoring failed: ${err.message}`);
    } finally { ui.setLoading('score-btn', false); }
  }

  async function generateQuestions() {
    ui.hideError();
    ui.setLoading('questions-btn', true);
    try {
      const gaps = state.gaps ? state.gaps.map(g => g.skill) : [];
      const result = await api.client.interviewQuestions(state.resumeText, state.jdText, gaps);
      ui.renderInterviewQuestions(result);
      nav('step-questions');
    } catch (err) {
      ui.showError(err instanceof api.RateLimitError ? '⚠️ Rate limit. Wait 30-60s.' : `Questions failed: ${err.message}`);
    } finally { ui.setLoading('questions-btn', false); }
  }

  async function atsBreakdown() {
    ui.hideError();
    const platform = state.selectedAtsPlatform || 'greenhouse';
    ui.setLoading('ats-breakdown-btn', true);
    try {
      const result = await api.client.atsBreakdown(state.resumeText, state.jdText, platform);
      ui.renderAtsBreakdown(result);
      nav('step-ats');
    } catch (err) {
      ui.showError(err instanceof api.RateLimitError ? '⚠️ Rate limit. Wait 30-60s.' : `ATS breakdown failed: ${err.message}`);
    } finally { ui.setLoading('ats-breakdown-btn', false); }
  }

  async function fullRewrite() {
    ui.hideError();
    if (!state.gaps || state.gaps.length === 0) { ui.showError('No gaps to address. Run analysis first.'); return; }
    const gapSkills = state.gaps.map(g => g.skill);
    ui.setLoading('full-rewrite-btn', true);
    try {
      const result = await api.client.fullRewrite(state.resumeText, gapSkills, state.jdText);
      ui.renderFullRewrite(result.full_resume, result.changes_summary);
      nav('step-full-rewrite');
    } catch (err) {
      if (err instanceof api.RateLimitError) ui.showError('⚠️ Rate limit reached. Please wait 30-60 seconds, then try again.');
      else ui.showError(`Full rewrite failed: ${err.message}`);
    } finally { ui.setLoading('full-rewrite-btn', false); }
  }

  function reset() {
    state.resumeText = null; state.resumeFile = null; state.jdText = null;
    state.gaps = null; state.rewriteResult = null; state.simulation = null;
    state.shortlistResult = null; state.recommendations = null;
    state.selectedAtsPlatform = 'greenhouse';
    document.getElementById('file-input').value = '';
    document.getElementById('file-info').textContent = 'No file selected';
    document.getElementById('extracted-text').value = '';
    document.getElementById('extracted-text-container').classList.add('hidden');
    document.getElementById('jd-input').value = '';
    document.getElementById('role-input').value = '';
    document.getElementById('gap-list').innerHTML = '';
    document.getElementById('rewrite-result') && (document.getElementById('rewrite-result').classList.add('hidden'));
    const simTb = document.getElementById('simulation-table')?.querySelector('tbody');
    if (simTb) simTb.innerHTML = '';
    document.getElementById('cover-letter-result')?.classList.add('hidden');
    document.getElementById('keywords-result')?.classList.add('hidden');
    document.getElementById('score-result')?.classList.add('hidden');
    document.getElementById('questions-result')?.classList.add('hidden');
    document.getElementById('ats-result')?.classList.add('hidden');
    document.getElementById('shortlist-resume-container')?.classList.add('hidden');
    document.getElementById('shortlist-agree-check') && (document.getElementById('shortlist-agree-check').checked = false);
    const dlBtn = document.getElementById('shortlist-download-btn');
    if (dlBtn) dlBtn.disabled = true;
    nav('step-upload');
  }

  function renderTemplateGrid(templates) {
    const grid = document.getElementById('template-grid');
    if (!grid) return;
    grid.innerHTML = templates.map((t, i) => `
      <div class="template-card ${i === 0 ? 'featured' : ''}">
        <h4>${ui.escapeHtml(t.name)} ${i === 0 ? '<span class="template-badge">Best Match</span>' : ''}</h4>
        <div class="ats-score">ATS Score: ${t.ats_score}/100</div>
        <p>${ui.escapeHtml(t.description)}</p>
        <div class="best-for"><strong>Best for:</strong> ${t.best_for.map(b => `<span>${ui.escapeHtml(b)}</span>`).join(' ')}</div>
      </div>
    `).join('');
  }

  function renderTemplateGridFull(templates) {
    const grid = document.getElementById('templates-full-grid');
    if (!grid) return;
    grid.innerHTML = templates.map(t => `
      <div class="template-card">
        <h4>${ui.escapeHtml(t.name)}</h4>
        <div class="ats-score">ATS Score: ${t.ats_score}/100</div>
        <p>${ui.escapeHtml(t.description)}</p>
        <div class="best-for"><strong>Best for:</strong> ${t.best_for.map(b => `<span>${ui.escapeHtml(b)}</span>`).join(' ')}</div>
        <p style="font-size:0.8rem;color:var(--text-muted);margin-top:8px">${ui.escapeHtml(t.preview)}</p>
      </div>
    `).join('');
  }

  function checkForJDInClipboard() {
    if (!navigator.clipboard?.readText) return;
    navigator.clipboard.readText().then(text => {
      if (text && text.length > 100 && text.includes('\n')) {
        const jdInput = document.getElementById('jd-input');
        if (jdInput && !jdInput.value) { jdInput.value = text; jdInput.placeholder = 'Detected from clipboard!'; }
      }
    }).catch(() => {});
  }

  document.addEventListener('DOMContentLoaded', init);
  return { init, analyze, rewrite, fullRewrite, simulate, generateCoverLetter, analyzeKeywords, scoreResume, generateQuestions, atsBreakdown, shortlist, recommendTemplate, smartRecommend, reset, nav, loadTemplates, renderTemplateGrid };
})();
