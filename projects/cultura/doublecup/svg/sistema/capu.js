const {chromium} = require('playwright');
(async()=>{const b=await chromium.launch();
for (const t of [2,8,14,20,25]){
 const p=await b.newPage({viewport:{width:700,height:920}});
 await p.goto('file:///tmp/proto/sistema/union.svg');
 await p.waitForTimeout(t*1000+400);
 await p.screenshot({path:'/tmp/proto/un_'+t+'.png'});
 await p.close();}
await b.close();})();
