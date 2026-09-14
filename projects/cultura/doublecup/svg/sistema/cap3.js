const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({viewport:{width:700,height:920}, colorScheme:'dark'});
  await p.goto('file:///tmp/proto/prototipo_01.svg');
  for (const t of [0,2,4.5,9,13.5,17]) {
    await p.evaluate((t) => {
      document.querySelectorAll('*').forEach(e=>{
        e.style.animationDelay = (-t)+'s';
        e.style.animationPlayState = 'paused';
      });
    }, t);
    await p.screenshot({path:`/tmp/proto/p1_t${t}.png`});
  }
  await b.close();
})();
