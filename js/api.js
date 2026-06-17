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
          let detail = `HTTP ${res.status}`;
          try {
            const errJson = await res.json();
            if (errJson.detail) detail = errJson.detail;
          } catch {
            const errText = await res.text().catch(() => '');
            if (errText) detail = errText;
          }
          // Detect rate limit / quota errors
          const lower = detail.toLowerCase();
          if (res.status === 429 || lower.includes('rate limit') || lower.includes('quota') || lower.includes('resource exhausted')) {
            throw new RateLimitError(detail);
          }
          throw new Error(detail);
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

    async coverLetter(resumeText, jdText) {
      return this.request('/cover_letter', {
        resume: resumeText,
        job_description: jdText
      });
    }

    async keywords(resumeText, jdText) {
      return this.request('/keywords', {
        resume: resumeText,
        job_description: jdText
      });
    }

    async score(resumeText, jdText) {
      return this.request('/score', {
        resume: resumeText,
        job_description: jdText
      });
    }

    async interviewQuestions(resumeText, jdText, gaps = []) {
      return this.request('/interview_questions', {
        resume: resumeText,
        job_description: jdText,
        gaps: gaps
      });
    }

    async atsBreakdown(resumeText, jdText, platform = 'greenhouse') {
      return this.request('/ats_breakdown', {
        resume: resumeText,
        job_description: jdText,
        platform: platform
      });
    }
  }

  return { client: new BackendClient(), RateLimitError };
})();
