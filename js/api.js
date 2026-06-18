class RateLimitError extends Error {
  constructor(message) {
    super(message);
    this.name = 'RateLimitError';
  }
}

const api = (() => {
  class BackendClient {
    constructor() {
      this.baseUrl = CONFIG.BACKEND_URL;
    }

    async request(endpoint, body, method = 'POST') {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), CONFIG.TIMEOUT_MS);
      try {
        const opts = { method, headers: { 'Content-Type': 'application/json' }, signal: controller.signal };
        if (body) opts.body = JSON.stringify(body);
        const res = await fetch(`${this.baseUrl}${endpoint}`, opts);
        clearTimeout(timeoutId);
        if (!res.ok) {
          let detail = `HTTP ${res.status}`;
          try { const j = await res.json(); if (j.detail) detail = j.detail; }
          catch { const t = await res.text().catch(() => ''); if (t) detail = t; }
          const ds = typeof detail === 'string' ? detail : JSON.stringify(detail);
          const lower = ds.toLowerCase();
          if (res.status === 429 || lower.includes('rate limit') || lower.includes('quota') || lower.includes('resource exhausted'))
            throw new RateLimitError(detail);
          throw new Error(detail);
        }
        return res.json();
      } catch (err) { clearTimeout(timeoutId); throw err; }
    }

    async analyze(r, jd) { return this.request('/analyze', { resume: r, job_description: jd }); }
    async rewrite(r, skill, ctx = '') { return this.request('/rewrite', { resume: r, skill, context: ctx }); }
    async simulate(r, role) { return this.request('/simulate', { resume: r, role }); }
    async fullRewrite(r, gaps, jd) { return this.request('/full_rewrite', { resume: r, gaps, job_description: jd }); }
    async coverLetter(r, jd) { return this.request('/cover_letter', { resume: r, job_description: jd }); }
    async keywords(r, jd) { return this.request('/keywords', { resume: r, job_description: jd }); }
    async score(r, jd) { return this.request('/score', { resume: r, job_description: jd }); }
    async interviewQuestions(r, jd, gaps = []) { return this.request('/interview_questions', { resume: r, job_description: jd, gaps }); }
    async atsBreakdown(r, jd, p = 'greenhouse') { return this.request('/ats_breakdown', { resume: r, job_description: jd, platform: p }); }
    async shortlist(r, jd, aggressive = false) { return this.request('/shortlist', { resume: r, job_description: jd, aggressive }); }

    // Templates + Recommendations — try API, fallback gracefully (app.js has client-side fallbacks)
    async getTemplates() { 
      try { return await this.request('/templates', null, 'GET'); }
      catch { return { templates: [] }; }
    }
    async recommendTemplate(r, jd = '') { 
      try { return await this.request('/templates/recommend', { resume: r, job_description: jd }); }
      catch { throw new Error('Backend unavailable'); }
    }
    async recommend(r, jd) { 
      try { return await this.request('/recommend', { resume: r, job_description: jd }); }
      catch { throw new Error('Backend unavailable'); }
    }
  }

  return { client: new BackendClient(), RateLimitError };
})();
