const {chromium} = require('playwright');
(async()=>{const b=await chromium.launch();
for (const t of [0,2,4]){
 const p=await b.newPage({viewport:{width:700,height:920}});
 await p.goto('file:///tmp/proto/sistema/cableado.svg');
 await p.waitForTimeout(t*1000+400);
 await p.screenshot({path:'/tmp/proto/cb_'+t+'.png'});
 await p.close();}
await b.close();})();
