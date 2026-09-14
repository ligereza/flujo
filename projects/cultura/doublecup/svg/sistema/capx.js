const {chromium} = require('playwright');
(async()=>{const b=await chromium.launch();
for (const t of [3,13,22]){
 const p=await b.newPage({viewport:{width:700,height:920}});
 await p.goto('file:///tmp/proto/sistema/sintesis.svg');
 await p.waitForTimeout(t*1000+400);
 await p.screenshot({path:'/tmp/proto/sn_'+t+'.png'});
 await p.close();}
await b.close();})();
