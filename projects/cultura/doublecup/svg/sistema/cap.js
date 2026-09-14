const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch();
const p=await b.newPage({viewport:{width:700,height:920},colorScheme:'dark',deviceScaleFactor:2});
await p.goto('file:///tmp/proto/prototipo_00.svg');
const pts=[0,3,6,7,8,11]; // segundos del ciclo de 16s
for(const t of pts){
  await p.evaluate(t=>{document.querySelectorAll('*').forEach(e=>{e.style.animationDelay=(-t)+'s';e.style.animationPlayState='paused';});},t);
  await p.waitForTimeout(80);
  await p.screenshot({path:`/tmp/proto/t${t}.png`,animations:'allow'});
}
await b.close();})();
