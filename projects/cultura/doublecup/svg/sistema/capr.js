const {chromium} = require('playwright');
(async()=>{const b=await chromium.launch();
for (const [n,t] of [["depth",0],["normal",0],["relieve",0],["relieve",4],["relieve",8]]){
 const p=await b.newPage({viewport:{width:700,height:920}});
 await p.goto('file:///tmp/proto/sistema/'+n+'.svg');
 await p.waitForTimeout(t*1000+300);
 await p.screenshot({path:'/tmp/proto/r_'+n+'_'+t+'.png'});
 await p.close();}
await b.close();})();
