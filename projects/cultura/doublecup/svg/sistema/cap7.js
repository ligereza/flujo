const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({viewport:{width:700,height:920}, colorScheme:'dark'});
  await p.goto('file:///tmp/proto/prototipo_03.svg');
  let prev=0;
  for (const t of [0.5,1.5,2.5,3.5,4.5]) {
    await p.waitForTimeout((t-prev)*1000); prev=t;
    await p.screenshot({path:`/tmp/proto/u_t${t}.png`});
  }
  await b.close();
})();
