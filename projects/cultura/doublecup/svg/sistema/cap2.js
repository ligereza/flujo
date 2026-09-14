const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch();
const p=await b.newPage({viewport:{width:700,height:920},colorScheme:'dark',deviceScaleFactor:2});
await p.goto('file:///tmp/proto/prototipo_00.svg');
for(const t of [1,6.8,9]){
  await p.evaluate(t=>{document.querySelectorAll('*').forEach(e=>{e.style.animationDelay=(-t)+'s';e.style.animationPlayState='paused';});},t);
  await p.waitForTimeout(80);
  await p.screenshot({path:`/tmp/proto/v2_${t}.png`,animations:'allow'});
}
await b.close();})();
