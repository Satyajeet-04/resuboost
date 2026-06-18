window.app = (() => {
  const state = {
    resumeText: null, resumeFile: null, jdText: null, role: null,
    gaps: null, matchScore: 0, rewriteResult: null, simulation: null,
    shortlistResult: null, currentStep: 'hero',
    templates: null, recommendations: null, selectedAtsPlatform: 'greenhouse'
  };

  // ===== EMBEDDED TEMPLATES (no backend dependency) =====
  const EMBEDDED_TEMPLATES = [
    {
      name: 'Modern Professional',
      id: 'modern-professional',
      ats_score: 96,
      description: 'Clean single-column layout with color-coded sections. Best for most corporate roles.',
      best_for: ['Software Engineer', 'Project Manager', 'Data Analyst', 'Marketing'],
      preview: 'SUMMARY | EXPERIENCE | EDUCATION | SKILLS — clean blue header, easy-to-scan bullets'
    },
    {
      name: 'Executive Impact',
      id: 'executive-impact',
      ats_score: 94,
      description: 'Emphasizes leadership, metrics, and career progression. Strategic focus.',
      best_for: ['Senior Manager', 'Director', 'VP', 'Team Lead', 'Engineering Manager'],
      preview: 'EXECUTIVE SUMMARY | LEADERSHIP | ACHIEVEMENTS | METRICS — bold headers, quantified results'
    },
    {
      name: 'Tech Minimal',
      id: 'tech-minimal',
      ats_score: 98,
      description: 'ATS-maximized layout for technical roles. Skills-first with keyword density optimization.',
      best_for: ['DevOps', 'Backend Engineer', 'Data Scientist', 'Cloud Architect'],
      preview: 'TECHNICAL SKILLS | EXPERIENCE | PROJECTS | EDUCATION — minimal design, maximum ATS parsing'
    },
    {
      name: 'Creative Portfolio',
      id: 'creative-portfolio',
      ats_score: 90,
      description: 'Balanced visual appeal with ATS compliance. Subtle design elements for creative roles.',
      best_for: ['UX Designer', 'Product Designer', 'Art Director', 'Content Creator'],
      preview: 'PROFILE | PORTFOLIO | SKILLS | EXPERIENCE | EDUCATION — subtle accent color, project focus'
    },
    {
      name: 'Entry-Level Launch',
      id: 'entry-level-launch',
      ats_score: 95,
      description: 'Designed for students and new grads. Emphasizes projects, internships, and coursework.',
      best_for: ['Internship', 'New Grad', 'Entry Level', 'Co-op', 'Fresher'],
      preview: 'EDUCATION | PROJECTS | INTERNSHIPS | SKILLS | COURSEWORK — GPA/projects prioritized'
    }
  ];

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

  // ===== TEMPLATES (fully client-side) =====
  function loadTemplates() {
    state.templates = EMBEDDED_TEMPLATES;
    renderTemplateGrid(state.templates);
    renderTemplateGridFull(state.templates);
    // Also try API in background for richer data
    api.client.getTemplates().then(res => {
      if (res && res.templates && res.templates.length) {
        state.templates = res.templates;
        renderTemplateGrid(state.templates);
        renderTemplateGridFull(state.templates);
      }
    }).catch(() => {});
  }

  function recommendTemplateClientSide(resume, jd) {
    const lower = (resume + ' ' + (jd || '')).toLowerCase();
    const keywords = lower.split(/[\s,;.()\n]+/).filter(k => k.length > 3);
    
    const typeScores = EMBEDDED_TEMPLATES.map(t => {
      let score = 0;
      t.best_for.forEach(bf => {
        const bfLower = bf.toLowerCase();
        if (lower.includes(bfLower)) score += 30;
        keywords.forEach(kw => {
          if (bfLower.includes(kw) || kw.includes(bfLower)) score += 5;
        });
      });
      return { ...t, score };
    });

    typeScores.sort((a, b) => b.score - a.score);
    const top = typeScores.filter(t => t.score > 0).slice(0, 3);
    const recommended = top.length ? top : [EMBEDDED_TEMPLATES[0], EMBEDDED_TEMPLATES[2], EMBEDDED_TEMPLATES[4]];
    
    let reasoning = '';
    if (top.length) {
      reasoning = `Your resume best matches ${top[0].name} (${top[0].best_for.join(', ')}) based on keyword analysis`;
    } else {
      reasoning = 'General ATS-optimized recommendations based on proven formats';
    }
    
    return { recommended, reasoning };
  }

  async function recommendTemplate() {
    if (!state.resumeText) { ui.showError('Please upload a resume first.'); return; }
    ui.hideError();
    ui.setLoading('rec-template-btn', true);
    try {
      // Try API first
      const result = await api.client.recommendTemplate(state.resumeText, state.jdText || '');
      ui.renderTemplateRecommendation(result);
    } catch {
      // Fallback: client-side
      const result = recommendTemplateClientSide(state.resumeText, state.jdText || '');
      ui.renderTemplateRecommendation(result);
    }
    document.getElementById('template-rec-result')?.classList.remove('hidden');
    ui.setLoading('rec-template-btn', false);
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
        ui.renderTemplateRecommendation(result);
        container.innerHTML = document.getElementById('template-rec-result').innerHTML;
      }
    } catch {
      const result = recommendTemplateClientSide(resume, jd || '');
      const container = document.getElementById('template-rec-result-page');
      if (container) {
        container.classList.remove('hidden');
        // Render into a temp container then copy
        ui.renderTemplateRecommendation(result);
        container.innerHTML = document.getElementById('template-rec-result').innerHTML;
      }
    }
    ui.setLoading('template-rec-btn-page', false);
  }

  // ===== SMART RECOMMENDATIONS (fully client-side) =====
  function generateRecommendationsClientSide(resume, jd, gaps, matchScore) {
    const resumeLower = resume.toLowerCase();
    const jdLower = jd.toLowerCase();
    const jdWords = jdLower.split(/[\s,;.()\n]+/).filter(w => w.length > 3);
    const missingSkills = gaps ? gaps.filter(g => g.importance === 'high').map(g => g.skill) : [];
    
    const recommendations = [];
    const quickWins = [];
    
    // Quick wins
    if (gaps && gaps.length > 0) {
      gaps.filter(g => g.importance === 'high').slice(0, 3).forEach(g => {
        quickWins.push(`Add "${g.skill}" to your Skills section — it's explicitly requested in the JD and completely missing from your resume.`);
      });
    }
    
    // Check for professional summary
    const summaryKeywords = ['professional summary', 'professional profile', 'summary', 'about me', 'career objective'];
    const hasSummary = summaryKeywords.some(k => resumeLower.includes(k));
    if (!hasSummary) {
      recommendations.push({
        category: 'rewrite',
        title: 'Add a Professional Summary',
        description: 'Your resume lacks a professional summary. Most recruiters scan this section first to understand your profile.',
        actionable_steps: [
          'Write a 3-4 sentence summary highlighting your years of experience, top skills, and career goals',
          'Mirror language from the job description\'s "About You" section',
          'Include your target role title and key domain expertise'
        ],
        estimated_time: '15 minutes',
        priority: 'high',
        roi: 'quick_win'
      });
    }
    
    // Experience section check
    if (!resumeLower.includes('experience') && !resumeLower.includes('work history')) {
      recommendations.push({
        category: 'rewrite',
        title: 'Add an Experience Section',
        description: 'Your resume appears to lack a dedicated Experience section, which is critical for most roles.',
        actionable_steps: [
          'List your work history in reverse chronological order',
          'Use STAR format (Situation, Task, Action, Result) for each bullet',
          'Include company names, dates, and 3-5 bullet points per role'
        ],
        estimated_time: '30 minutes',
        priority: 'critical',
        roi: 'quick_win'
      });
    }
    
    // Missing high-importance skills
    if (missingSkills.length > 0) {
      missingSkills.forEach(skill => {
        const isTech = ['python', 'java', 'javascript', 'react', 'aws', 'docker', 'sql', 'node', 'typescript', 'git', 'kubernetes', 'ml', 'ai', 'api'].some(t => skill.toLowerCase().includes(t));
        if (isTech) {
          recommendations.push({
            category: 'upskill',
            title: `Learn ${skill} for This Role`,
            description: `${skill} is explicitly required in the job description. Adding it will significantly improve your match score.`,
            actionable_steps: [
              `Complete a ${skill} crash course (see recommendations below)`,
              `Build a small project using ${skill}`,
              `Update your resume once you have a working project to showcase`
            ],
            estimated_time: '1-2 weeks',
            priority: 'high',
            roi: 'high_impact',
            courses: [
              { title: `${skill} Crash Course`, platform: 'Coursera/Udemy' },
              { title: `Build Projects with ${skill}`, platform: 'FrontendMasters/Pluralsight' }
            ],
            micropractices: [
              { task: `Practice ${skill} basics for 15 min`, time_minutes: 15 },
              { task: `Build a mini project using ${skill}`, time_minutes: 60 }
            ]
          });
        } else {
          recommendations.push({
            category: 'upskill',
            title: `Bridge Gap: ${skill}`,
            description: `Recruiters screening for this role are looking for ${skill}.`,
            actionable_steps: [
              `Research common interview questions about ${skill}`,
              `Find a short online course (LinkedIn Learning, Coursera)`,
              `Document your learning journey to demonstrate initiative`
            ],
            estimated_time: '1-3 weeks',
            priority: 'high',
            roi: 'high_impact',
            courses: [
              { title: `Introduction to ${skill}`, platform: 'LinkedIn Learning' },
              { title: `${skill} for Professionals`, platform: 'Coursera' }
            ]
          });
        }
      });
    }
    
    // Interview prep recommendation
    if (gaps && gaps.length >= 2) {
      recommendations.push({
        category: 'practice',
        title: 'Practice Answering Questions About Your Gaps',
        description: 'Be prepared to address missing qualifications honestly but positively in interviews.',
        actionable_steps: [
          'Prepare a 30-second narrative for each missing skill showing how you\'d learn it quickly',
          'Highlight transferable skills that compensate for specific gaps',
          'Practice the "I don\'t know X, but I know Y" framework'
        ],
        estimated_time: '30 minutes',
        priority: 'medium',
        roi: 'quick_win'
      });
    }
    
    // Quantified achievements check
    const numbers = resume.match(/\d+%/g) || resume.match(/\d+x/g);
    if (!numbers && resume.includes('experience')) {
      recommendations.push({
        category: 'rewrite',
        title: 'Add Quantified Achievements',
        description: 'Resumes with quantified results (%, $, time saved) get 40% more callbacks.',
        actionable_steps: [
          'Review each bullet point and add measurable impact',
          'Use patterns like: "Improved X by Y%", "Reduced Z by W hours/week"',
          'Even estimated metrics are better than none'
        ],
        estimated_time: '20 minutes',
        priority: 'high',
        roi: 'quick_win',
        micropractices: [
          { task: 'Rewrite one bullet with a metric', time_minutes: 10 },
          { task: 'Add impact numbers to top 3 bullets', time_minutes: 20 }
        ]
      });
    }
    
    // Networking recommendation
    recommendations.push({
      category: 'network',
      title: 'Connect with Professionals in Target Roles',
      description: 'Referrals increase interview chances by 10x. Build genuine connections.',
      actionable_steps: [
        'Find 5 people with your target title on LinkedIn',
        'Send personalized connection notes (not template messages)',
        'Ask for 15-min informational interviews'
      ],
      estimated_time: '1 hour',
      priority: 'medium',
      roi: 'high_impact'
    });
    
    // Deduplicate by title
    const seen = new Set();
    const uniqueRecs = recommendations.filter(r => {
      const key = r.title.toLowerCase();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
    
    return {
      focus_area: missingSkills.length > 0
        ? `Address ${missingSkills.length} critical skill gap${missingSkills.length > 1 ? 's' : ''} to reach interview threshold`
        : `Optimize resume presentation and impact — your skills align but need better framing`,
      quick_wins: quickWins.slice(0, 5),
      recommendations: uniqueRecs.slice(0, 8)
    };
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
    } catch {
      // Client-side fallback
      const result = generateRecommendationsClientSide(
        state.resumeText, state.jdText, state.gaps, state.matchScore
      );
      state.recommendations = result;
      ui.renderSmartRecommendations(result);
      nav('step-recommendations');
    }
    ui.setLoading('recommend-btn', false);
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
    document.querySelectorAll('.nav-links a[data-section]').forEach(a => {
      a.addEventListener('click', e => { e.preventDefault(); nav(a.dataset.section); });
    });
    document.getElementById('hero-cta')?.addEventListener('click', () => nav('step-upload'));
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
    document.getElementById('rec-template-btn')?.addEventListener('click', recommendTemplate);
    document.getElementById('template-rec-btn-page')?.addEventListener('click', recommendTemplateFromPage);
    document.getElementById('recommend-btn')?.addEventListener('click', smartRecommend);
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
    const fi = document.getElementById('file-input'); if (fi) fi.value = '';
    const info = document.getElementById('file-info'); if (info) info.textContent = 'No file selected';
    const ext = document.getElementById('extracted-text'); if (ext) ext.value = '';
    const extC = document.getElementById('extracted-text-container'); if (extC) extC.classList.add('hidden');
    const jd = document.getElementById('jd-input'); if (jd) jd.value = '';
    const role = document.getElementById('role-input'); if (role) role.value = '';
    const gaps = document.getElementById('gap-list'); if (gaps) gaps.innerHTML = '';
    const sim = document.getElementById('simulation-table')?.querySelector('tbody'); if (sim) sim.innerHTML = '';
    const cl = document.getElementById('cover-letter-result'); if (cl) cl.classList.add('hidden');
    const kw = document.getElementById('keywords-result'); if (kw) kw.classList.add('hidden');
    const sc = document.getElementById('score-result'); if (sc) sc.classList.add('hidden');
    const qs = document.getElementById('questions-result'); if (qs) qs.classList.add('hidden');
    const ats = document.getElementById('ats-result'); if (ats) ats.classList.add('hidden');
    const sr = document.getElementById('shortlist-resume-container'); if (sr) sr.classList.add('hidden');
    const ac = document.getElementById('shortlist-agree-check'); if (ac) ac.checked = false;
    const dl = document.getElementById('shortlist-download-btn'); if (dl) dl.disabled = true;
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
