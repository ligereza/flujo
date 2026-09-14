const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  for (const t of [0,2,4,6,8,9,12,16]) {
    const p = await b.newPage({viewport:{width:700,height:920}, colorScheme:'dark'});
    await p.goto('file:///tmp/proto/prototipo_01.svg');
    await p.evaluate((t) => {
      document.querySelectorAll('*').forEach(e=>{
        e.style.animationDelay = (-t)+'s';
        e.style.animationPlayState = 'paused';
      });
    }, t);
    await p.waitForTimeout(120);
    await p.screenshot({path:`/tmp/proto/q_t${t}.png`});
    await p.close();
  }
  await b.close();
})();
