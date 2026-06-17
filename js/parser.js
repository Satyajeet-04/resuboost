const parser = (() => {
  let pdfjsLib = null;

  async function init() {
    if (pdfjsLib) return;
    pdfjsLib = await import('https://mozilla.github.io/pdf.js/build/pdf.mjs');
    pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://mozilla.github.io/pdf.js/build/pdf.worker.mjs';
  }

  async function extractTextFromPDF(file) {
    await init();
    const arrayBuffer = await file.arrayBuffer();
    const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;

    if (pdf.numPages > 10) {
      console.warn(`Resume has ${pdf.numPages} pages — unusually large`);
    }

    let text = '';
    for (let i = 1; i <= pdf.numPages; i++) {
      const page = await pdf.getPage(i);
      const content = await page.getTextContent();
      text += content.items.map(item => item.str).join(' ') + '\n';
    }
    return text.trim();
  }

  return { extractTextFromPDF };
})();
