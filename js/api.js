const api = (() => {
  class BackendClient {
    constructor() {
      this.baseUrl = CONFIG.BACKEND_URL;
    }

    async request(endpoint, body) {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), CONFIG.TIMEOUT_MS);

      try {
        const res = await fetch(`${this.baseUrl}${endpoint}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
          signal: controller.signal
        });
        clearTimeout(timeoutId);
        if (!res.ok) {
          const errText = await res.text();
          throw new Error(errText || `HTTP ${res.status}`);
        }
        return res.json();
      } catch (err) {
        clearTimeout(timeoutId);
        throw err;
      }
    }

    async analyze(resumeText, jdText) {
      return this.request('/analyze', {
        resume: resumeText,
        job_description: jdText
      });
    }

    async rewrite(resumeText, skill, context = '') {
      return this.request('/rewrite', {
        resume: resumeText,
        skill: skill,
        context: context
      });
    }

    async simulate(resumeText, role) {
      return this.request('/simulate', {
        resume: resumeText,
        role: role
      });
    }

    async fullRewrite(resumeText, gaps, jdText) {
      return this.request('/full_rewrite', {
        resume: resumeText,
        gaps: gaps,
        job_description: jdText
      });
    }
  }

  return { client: new BackendClient() };
})();
