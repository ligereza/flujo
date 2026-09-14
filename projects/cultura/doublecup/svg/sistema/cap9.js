const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({viewport:{width:700,height:920}, colorScheme:'dark'});
  await p.goto('file:///tmp/proto/sistema/vaso.svg');
  let prev=0;
  for (const t of [1,7,12,17,22]) {
    await p.waitForTimeout((t-prev)*1000); prev=t;
    await p.screenshot({path:`/tmp/proto/x_t${t}.png`});
  }
  await b.close();
})();
