// Checks that the JavaScript on the page reproduces results.json at the default setting, on desktop and mobile,
// with no console errors and no horizontal overflow. Needs Playwright and a local server:
//   (cd ../.. && python -m http.server 8765) &
//   node tests/site_consistency.js
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const R = JSON.parse(fs.readFileSync(require('path').join(__dirname, '..', '..', 'data', 'results.json')));
  const b = await chromium.launch();
  for (const [name, vp, mobile] of [['desktop', { width: 1366, height: 900 }, false], ['mobile', { width: 375, height: 800 }, true]]) {
    const ctx = await b.newContext({ viewport: vp, isMobile: mobile, hasTouch: mobile });
    const p = await ctx.newPage();
    const errs = [];
    p.on('console', m => m.type() === 'error' && !/ERR_|net::|Failed to load resource/.test(m.text()) && errs.push(m.text()));
    p.on('pageerror', e => errs.push('pageerror ' + e.message));
    await p.goto('http://localhost:8765/bag-arbitrage/', { waitUntil: 'domcontentloaded' });
    await p.waitForSelector('#t-ca .v');
    await p.waitForTimeout(800);
    const info = await p.evaluate(() => {
      const all = B.flatMap(b => b.items), t = scenarioTest(all), f = fxStats(all);
      return { n: t.n, G: t.G, m: t.m, se: t.se, t: t.t, p: t.p, lo: t.lo, hi: t.hi, implied: f.implied,
        overflow: document.documentElement.scrollWidth - innerWidth,
        title: document.title, h1: document.querySelector('h1').textContent,
        imgsNoAlt: [...document.querySelectorAll('img')].filter(i => !i.hasAttribute('alt')).length,
        abstract: document.getElementById('abstract-text').textContent.slice(0, 200),
        scn: document.getElementById('scn-title').textContent };
    });
    const pr = R.primary;
    const close = (a, b, tol = 1e-6) => Math.abs(a - b) < tol;
    console.log(name, JSON.stringify({ n: info.n, G: info.G, overflow: info.overflow, scn: info.scn, imgsNoAlt: info.imgsNoAlt }));
    console.log(' match results.json:', close(info.m, pr.mean_log), close(info.se, pr.se), close(info.t, pr.stat, 1e-4), close(info.p, pr.p, 1e-9),
      close(info.lo * 100, pr.ci_low_pct, 1e-3), close(info.hi * 100, pr.ci_high_pct, 1e-3), close(info.implied, pr.implied_fx, 1e-6));
    console.log(' errors:', errs);
    
    await ctx.close();
  }
  // URL parameters must accept the full slider range (a shared link with 0% Canadian tax must reopen at 0%).
  const ctx2 = await b.newContext(); const q = await ctx2.newPage();
  await q.goto('http://localhost:8765/bag-arbitrage/?fx_cad=1.4271&tax_us=0&tax_ca=0', { waitUntil: 'domcontentloaded' });
  await q.waitForSelector('#t-ca .v');
  const tax = await q.evaluate(() => ({ state: state.taxca, slider: +document.getElementById('taxca').value, min: +document.getElementById('taxca').min, rmin: RANGES.taxca[0] }));
  console.log('tax_ca=0 link:', JSON.stringify(tax), tax.state === 0 && tax.slider === 0 && tax.min === tax.rmin ? 'OK' : 'FAIL');
  await ctx2.close();
  await b.close();
})();
