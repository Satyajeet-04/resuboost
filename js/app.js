window.app = (() => {
  const state = {
    resumeText: null,
    resumeFile: null,
    jdText: null,
    role: null,
    gaps: null,
    matchScore: 0,
    rewriteResult: null,
    simulation: null,
    currentStep: 'upload'
  };

  function init() {
    setupFileUpload();
    setupEventListeners();
    checkForJDInClipboard();
  }

  function setupFileUpload() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const browseBtn = document.getElementById('browse-btn');

    if (!dropZone || !fileInput) return;

    browseBtn?.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (file) await handleFile(file);
    });

    dropZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropZone.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', () => {
      dropZone.classList.remove('drag-over');
    });

    dropZone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropZone.classList.remove('drag-over');
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    });
  }

  async function handleFile(file) {
    ui.hideError();

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      ui.showError('Only PDF files are supported.');
      return;
    }

    if (file.size > CONFIG.MAX_FILE_SIZE) {
      ui.showError('File is too large. Maximum 5MB.');
      return;
    }

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
      if (err.message?.includes('password')) {
        ui.showError('This PDF is password-protected. Please remove the password first.');
      } else {
        ui.showError('Could not parse this PDF. Please paste your resume text manually.');
      }
      document.getElementById('extracted-text-container').classList.remove('hidden');
      document.getElementById('extracted-text').value = '';
    }
  }

  function setupEventListeners() {
    document.getElementById('to-jd-btn')?.addEventListener('click', () => {
      const textarea = document.getElementById('extracted-text');
      if (textarea && textarea.value.trim()) {
        state.resumeText = textarea.value.trim();
      }
      if (!state.resumeText) {
        ui.showError('Please upload a resume or paste text first.');
        return;
      }
      ui.show('step-jd');
    });

    document.getElementById('analyze-btn')?.addEventListener('click', analyze);

    document.getElementById('simulate-btn')?.addEventListener('click', simulate);

    document.getElementById('cover-letter-btn')?.addEventListener('click', generateCoverLetter);
    document.getElementById('keywords-btn')?.addEventListener('click', analyzeKeywords);
    document.getElementById('score-btn')?.addEventListener('click', scoreResume);
    document.getElementById('questions-btn')?.addEventListener('click', generateQuestions);
    document.getElementById('ats-breakdown-btn')?.addEventListener('click', atsBreakdown);

    document.querySelectorAll('.back-to-analyze-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        ui.show('step-analyze');
      });
    });

    document.getElementById('full-rewrite-btn')?.addEventListener('click', fullRewrite);

    document.getElementById('new-analysis-btn')?.addEventListener('click', reset);

    document.getElementById('copy-rewrite')?.addEventListener('click', () => {
      const bullets = document.querySelectorAll('#rewritten-bullets li');
      const text = Array.from(bullets).map(li => li.textContent).join('\n');
      navigator.clipboard.writeText(text).then(() => {
        const btn = document.getElementById('copy-rewrite');
        btn.textContent = 'Copied!';
        setTimeout(() => { btn.textContent = 'Copy to Clipboard'; }, 2000);
      });
    });

    // Download rewritten resume as text file
    document.getElementById('download-txt')?.addEventListener('click', () => {
      const text = document.getElementById('full-rewrite-text')?.textContent;
      if (!text) return;
      const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'resuboost-rewritten-resume.txt';
      a.click();
      URL.revokeObjectURL(url);
    });

    // Save rewritten resume as PDF via browser print
    document.getElementById('download-pdf')?.addEventListener('click', () => {
      const text = document.getElementById('full-rewrite-text')?.textContent;
      if (!text) return;
      const safeText = ui.escapeHtml(text);
      const scriptBlock = '<' + 'script>';
      const scriptEnd = '<' + '/script>';
      const printWin = window.open('', '_blank', 'width=800,height=600');
      if (!printWin) {
        ui.showError('Popup blocked. Please allow popups or use Copy to Clipboard.');
        return;
      }
      printWin.document.write('<!DOCTYPE html><html><head><title>ResuBoost - Rewritten Resume</title>' +
        '<style>body{font-family:Calibri,Arial,sans-serif;font-size:12pt;line-height:1.5;max-width:800px;margin:0.5in auto;padding:0 20px}' +
        'pre{white-space:pre-wrap;font-family:Calibri,Arial,sans-serif;font-size:12pt;line-height:1.5;border:none;background:white;color:black;padding:0;margin:0;overflow:visible;max-height:none}' +
        '.footer{font-size:9pt;color:#999;text-align:center;margin-top:30px;border-top:1px solid #ddd;padding-top:10px}' +
        '@media print{body{margin:0.5in}}' +
        '</style></head><body>' +
        '<pre>' + safeText + '</pre>' +
        '<div class="footer">Generated by ResuBoost</div>' +
        scriptBlock + 'window.onload=function(){window.print();window.close()};' + scriptEnd +
        '</body></html>');
      printWin.document.close();
    });

    // Cover letter download
    document.getElementById('download-cover-letter')?.addEventListener('click', () => {
      const text = document.getElementById('cover-letter-text')?.textContent;
      if (!text) return;
      const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'cover-letter.txt';
      a.click();
      URL.revokeObjectURL(url);
    });

    // ATS platform selector
    document.getElementById('ats-platform-select')?.addEventListener('change', (e) => {
      state.selectedAtsPlatform = e.target.value;
    });
  }

  async function generateCoverLetter() {
    ui.hideError();
    ui.setLoading('cover-letter-btn', true);
    try {
      const result = await api.client.coverLetter(state.resumeText, state.jdText);
      ui.renderCoverLetter(result);
      ui.show('step-cover-letter');
    } catch (err) {
      ui.showError(err instanceof api.RateLimitError ? '⚠️ Rate limit. Wait 30-60s.' : `Cover letter failed: ${err.message}`);
    } finally {
      ui.setLoading('cover-letter-btn', false);
    }
  }

  async function analyzeKeywords() {
    ui.hideError();
    ui.setLoading('keywords-btn', true);
    try {
      const result = await api.client.keywords(state.resumeText, state.jdText);
      ui.renderKeywords(result);
      ui.show('step-keywords');
    } catch (err) {
      ui.showError(err instanceof api.RateLimitError ? '⚠️ Rate limit. Wait 30-60s.' : `Keyword analysis failed: ${err.message}`);
    } finally {
      ui.setLoading('keywords-btn', false);
    }
  }

  async function scoreResume() {
    ui.hideError();
    ui.setLoading('score-btn', true);
    try {
      const result = await api.client.score(state.resumeText, state.jdText);
      ui.renderScore(result);
      ui.show('step-score');
    } catch (err) {
      ui.showError(err instanceof api.RateLimitError ? '⚠️ Rate limit. Wait 30-60s.' : `Scoring failed: ${err.message}`);
    } finally {
      ui.setLoading('score-btn', false);
    }
  }

  async function generateQuestions() {
    ui.hideError();
    ui.setLoading('questions-btn', true);
    try {
      const gaps = state.gaps ? state.gaps.map(g => g.skill) : [];
      const result = await api.client.interviewQuestions(state.resumeText, state.jdText, gaps);
      ui.renderInterviewQuestions(result);
      ui.show('step-questions');
    } catch (err) {
      ui.showError(err instanceof api.RateLimitError ? '⚠️ Rate limit. Wait 30-60s.' : `Questions failed: ${err.message}`);
    } finally {
      ui.setLoading('questions-btn', false);
    }
  }

  async function atsBreakdown() {
    ui.hideError();
    const platform = state.selectedAtsPlatform || 'greenhouse';
    ui.setLoading('ats-breakdown-btn', true);
    try {
      const result = await api.client.atsBreakdown(state.resumeText, state.jdText, platform);
      ui.renderAtsBreakdown(result);
      ui.show('step-ats');
    } catch (err) {
      ui.showError(err instanceof api.RateLimitError ? '⚠️ Rate limit. Wait 30-60s.' : `ATS breakdown failed: ${err.message}`);
    } finally {
      ui.setLoading('ats-breakdown-btn', false);
    }
  }

  async function analyze() {
    ui.hideError();

    const jdTextarea = document.getElementById('jd-input');
    const jdText = jdTextarea?.value.trim();
    state.jdText = jdText;

    const roleInput = document.getElementById('role-input');
    state.role = roleInput?.value.trim() || '';

    if (!jdText) {
      ui.showError('Please paste a job description.');
      return;
    }

    ui.setLoading('analyze-btn', true);
    ui.show('step-analyze');

    try {
      const result = await api.client.analyze(state.resumeText, jdText);
      state.gaps = result.gaps;
      state.matchScore = result.match_score;
      ui.renderGaps(result.gaps, result.match_score);
    } catch (err) {
      if (err instanceof api.RateLimitError) {
        ui.showError('⚠️ Rate limit reached. The free AI tier is busy right now. Please wait 30-60 seconds and try again.');
      } else {
        ui.showError(`Analysis failed: ${err.message}`);
      }
      ui.show('step-jd');
    } finally {
      ui.setLoading('analyze-btn', false);
    }
  }

  async function rewrite(skill) {
    ui.hideError();
    ui.setLoading('analyze-btn', true);

    try {
      const result = await api.client.rewrite(state.resumeText, skill, state.jdText);
      state.rewriteResult = result;
      ui.renderRewrite(result.original, result.rewritten, result.explanation);
      ui.show('step-rewrite');
    } catch (err) {
      if (err instanceof api.RateLimitError) {
        ui.showError('⚠️ Rate limit reached. Please wait 30-60 seconds, then try again.');
      } else {
        ui.showError(`Rewrite failed: ${err.message}`);
      }
    } finally {
      ui.setLoading('analyze-btn', false);
    }
  }

  async function simulate() {
    ui.hideError();

    const role = state.role || document.getElementById('role-input')?.value.trim();
    if (!role) {
      ui.showError('Please enter a target role.');
      return;
    }

    ui.setLoading('simulate-btn', true);

    try {
      const result = await api.client.simulate(state.resumeText, role);
      state.simulation = result;
      ui.renderSimulation(result.queries, result.match_rate);
      ui.show('step-simulate');
    } catch (err) {
      if (err instanceof api.RateLimitError) {
        ui.showError('⚠️ Rate limit reached. Please wait 30-60 seconds, then try again.');
      } else {
        ui.showError(`Simulation failed: ${err.message}`);
      }
    } finally {
      ui.setLoading('simulate-btn', false);
    }
  }

  async function fullRewrite() {
    ui.hideError();

    if (!state.gaps || state.gaps.length === 0) {
      ui.showError('No gaps to address. Run analysis first.');
      return;
    }

    const gapSkills = state.gaps.map(g => g.skill);
    ui.setLoading('full-rewrite-btn', true);

    try {
      const result = await api.client.fullRewrite(state.resumeText, gapSkills, state.jdText);
      ui.renderFullRewrite(result.full_resume, result.changes_summary);
      ui.show('step-full-rewrite');
    } catch (err) {
      if (err instanceof api.RateLimitError) {
        ui.showError('⚠️ Rate limit reached. Please wait 30-60 seconds, then try again.');
      } else {
        ui.showError(`Full rewrite failed: ${err.message}`);
      }
    } finally {
      ui.setLoading('full-rewrite-btn', false);
    }
  }

  function reset() {
    state.resumeText = null;
    state.resumeFile = null;
    state.jdText = null;
    state.gaps = null;
    state.rewriteResult = null;
    state.simulation = null;
    state.selectedAtsPlatform = 'greenhouse';

    document.getElementById('file-input').value = '';
    document.getElementById('file-info').textContent = 'No file selected';
    document.getElementById('extracted-text').value = '';
    document.getElementById('extracted-text-container').classList.add('hidden');
    document.getElementById('jd-input').value = '';
    document.getElementById('role-input').value = '';
    document.getElementById('gap-list').innerHTML = '';
    document.getElementById('rewrite-result').classList.add('hidden');
    document.getElementById('simulation-table').querySelector('tbody').innerHTML = '';
    document.getElementById('cover-letter-result')?.classList.add('hidden');
    document.getElementById('keywords-result')?.classList.add('hidden');
    document.getElementById('score-result')?.classList.add('hidden');
    document.getElementById('questions-result')?.classList.add('hidden');
    document.getElementById('ats-result')?.classList.add('hidden');

    ui.show('step-upload');
  }

  function checkForJDInClipboard() {
    if (!navigator.clipboard?.readText) return;
    navigator.clipboard.readText().then(text => {
      if (text && text.length > 100 && text.includes('\n')) {
        const jdInput = document.getElementById('jd-input');
        if (jdInput && !jdInput.value) {
          jdInput.value = text;
          jdInput.placeholder = 'Detected from clipboard!';
        }
      }
    }).catch(() => {});
  }

  document.addEventListener('DOMContentLoaded', init);
  return { init, analyze, rewrite, fullRewrite, simulate, generateCoverLetter, analyzeKeywords, scoreResume, generateQuestions, atsBreakdown, reset };
})();
