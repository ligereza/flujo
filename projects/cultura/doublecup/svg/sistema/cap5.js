const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({viewport:{width:700,height:920}, colorScheme:'dark'});
  await p.goto('file:///tmp/proto/prototipo_01.svg');
  let prev = 0;
  for (const t of [0,2,4,6,8,9,12,16]) {
    await p.waitForTimeout((t-prev)*1000); prev = t;
    await p.screenshot({path:`/tmp/proto/r_t${t}.png`});
  }
  await b.close();
})();
