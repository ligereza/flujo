/*
  Illustrator JSX — Logo Clean Master v1
  ======================================

  Fusion limpia de los intentos anteriores.

  Principios aprendidos:
  - El logo ya esta hecho: solo microcorrecciones.
  - No redibujar letras.
  - No alinear toda la palabra a baseline automaticamente.
  - No forzar diagonales.
  - No cerrar todos los handles de un nodo si ese nodo tambien toca una curva.
  - Para segmentos rectos, cerrar SOLO el handle del segmento.
  - Para redondas, corregir tangentes solo en extremos evidentes.
  - Eliminar puntos solo si son redundantes en tramos rectos sin handles reales.

  Modos:
    A = AUDIT: no modifica. Reporta candidatos, puntos, clasificacion y tolerancias.
    W = WORD: seleccionas palabra completa, escribes palabra, limpia segun letra.
    M = MICRO: no pide palabra, limpia micro H/V + puntos extra de forma conservadora.
    O = ORTHO: seleccion tratada como letras/formas rectas.
    R = ROUND: seleccion tratada como letras/formas redondas/curvas.

  No crea backup. Usa Ctrl+Z si no te gusta.

  Learning system:
    Al final puedes guardar un reporte .txt con parametros/resultados para ir aprendiendo
    que funciona en tus logos.
*/

#target illustrator

(function () {
  if (app.documents.length === 0) { alert("No hay documento abierto."); return; }
  var doc = app.activeDocument;
  if (!doc.selection || doc.selection.length === 0) { alert("Selecciona una palabra/logo primero."); return; }

  var mode = prompt(
    "Logo Clean Master v1\n\n" +
    "A = Audit, no modifica\n" +
    "W = Word, escribir palabra\n" +
    "M = Micro, sin palabra\n" +
    "O = Ortho, rectas\n" +
    "R = Round, curvas",
    "W"
  );
  if (mode === null) return;
  mode = String(mode).toUpperCase();
  if (mode !== "A" && mode !== "W" && mode !== "M" && mode !== "O" && mode !== "R") {
    alert("Modo invalido. Usa A, W, M, O o R.");
    return;
  }

  var word = "";
  if (mode === "W") {
    word = prompt("Escribe la palabra seleccionada. Espacios se ignoran.", "");
    if (word === null) return;
    word = String(word).replace(/\s+/g, "");
  }

  var selectedItems = [];
  for (var s = 0; s < doc.selection.length; s++) selectedItems.push(doc.selection[s]);

  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
  function copyPoint(p) { return [p[0], p[1]]; }
  function distance(a, b) { var dx=a[0]-b[0], dy=a[1]-b[1]; return Math.sqrt(dx*dx+dy*dy); }
  function angleDeg(dx, dy) { var a=Math.atan2(dy,dx)*180/Math.PI; while(a<0)a+=180; while(a>=180)a-=180; return a; }
  function angleDiff(a, b) { var d=Math.abs(a-b); if(d>90)d=180-d; return Math.abs(d); }

  function boundsOfItems(items) {
    var L=Infinity,T=-Infinity,R=-Infinity,B=Infinity;
    for(var i=0;i<items.length;i++){
      try { var b=items[i].visibleBounds; if(b[0]<L)L=b[0]; if(b[1]>T)T=b[1]; if(b[2]>R)R=b[2]; if(b[3]<B)B=b[3]; } catch(e) {}
    }
    if(!isFinite(L)) return {left:0,top:100,right:100,bottom:0,width:100,height:100,scale:100};
    var W=Math.max(0.001,R-L), H=Math.max(0.001,T-B);
    return {left:L,top:T,right:R,bottom:B,width:W,height:H,scale:Math.max(W,H)};
  }

  function boundsOfPaths(paths) {
    var L=Infinity,T=-Infinity,R=-Infinity,B=Infinity;
    for(var p=0;p<paths.length;p++){
      var pts=paths[p].pathPoints;
      for(var i=0;i<pts.length;i++){
        var a=pts[i].anchor;
        if(a[0]<L)L=a[0]; if(a[0]>R)R=a[0]; if(a[1]>T)T=a[1]; if(a[1]<B)B=a[1];
      }
    }
    if(!isFinite(L)) return {left:0,top:100,right:100,bottom:0,width:100,height:100,scale:100};
    var W=Math.max(0.001,R-L), H=Math.max(0.001,T-B);
    return {left:L,top:T,right:R,bottom:B,width:W,height:H,scale:Math.max(W,H)};
  }

  var gb = boundsOfItems(selectedItems);
  var baseH = Math.max(1, gb.height);
  var baseS = Math.max(1, gb.scale);

  var P = {
    alignTol: clamp(baseH * 0.0030, 0.05, 1.30),
    removeTol: clamp(baseH * 0.0008, 0.015, 0.34),
    angleTol: 2.0,
    handleAngleTol: 7.0,
    minSegment: clamp(baseS * 0.005, 0.35, 7.0),
    maxMove: 0
  };
  P.maxMove = P.alignTol * 1.25;

  function collectPaths(item, out) {
    if(!item) return;
    try { if(item.locked || item.hidden) return; } catch(e0) {}
    if(item.typename === "PathItem"){
      try { if(!item.guides && !item.clipping && item.pathPoints.length>=2) out.push(item); } catch(e1) {}
      return;
    }
    if(item.typename === "CompoundPathItem"){
      for(var c=0;c<item.pathItems.length;c++) collectPaths(item.pathItems[c], out);
      return;
    }
    if(item.typename === "GroupItem"){
      for(var g=0;g<item.pageItems.length;g++) collectPaths(item.pageItems[g], out);
      return;
    }
  }

  function candidateFromItem(item) {
    var paths=[]; collectPaths(item, paths);
    if(paths.length===0) return null;
    return { item:item, paths:paths, bounds:boundsOfPaths(paths), letter:"", kind:"" };
  }

  function collectCandidates(items) {
    var cands=[];
    for(var i=0;i<items.length;i++){
      var it=items[i];
      if(it.typename === "GroupItem"){
        var childCount=0;
        for(var g=0;g<it.pageItems.length;g++){
          var cand=candidateFromItem(it.pageItems[g]);
          if(cand){ cands.push(cand); childCount++; }
        }
        if(childCount===0){ var whole=candidateFromItem(it); if(whole)cands.push(whole); }
      } else {
        var c=candidateFromItem(it); if(c)cands.push(c);
      }
    }
    cands.sort(function(a,b){ return a.bounds.left - b.bounds.left; });
    return cands;
  }

  function letterKind(ch) {
    var c=String(ch).toUpperCase();
    if("EFHILT".indexOf(c)>=0) return "ORTHO";
    if("OCQ".indexOf(c)>=0) return "ROUND";
    if("AVWMNKXYZ".indexOf(c)>=0) return "ANGLED";
    if("BDPRSGUJ".indexOf(c)>=0) return "MIXED";
    if("147".indexOf(c)>=0) return "ORTHO";
    if("0".indexOf(c)>=0) return "ROUND";
    if("235689".indexOf(c)>=0) return "MIXED";
    return "MIXED";
  }

  function handleMagnitude(pp) {
    return Math.max(distance(pp.anchor, pp.leftDirection), distance(pp.anchor, pp.rightDirection));
  }
  function isStraightPoint(pp) { return handleMagnitude(pp) <= P.alignTol * 2.0; }
  function segmentLooksStraight(p1,p2) {
    return distance(p1.anchor,p1.rightDirection) <= P.alignTol*2.0 && distance(p2.anchor,p2.leftDirection) <= P.alignTol*2.0;
  }

  function geometryKind(cand) {
    var total=0, curved=0, hv=0, diag=0, segs=0;
    var hTol=clamp(cand.bounds.scale*0.004, 0.04, 1.5);
    for(var p=0;p<cand.paths.length;p++){
      var path=cand.paths[p], pts=path.pathPoints, n=pts.length;
      total += n;
      for(var i=0;i<n;i++) if(handleMagnitude(pts[i]) > hTol*2.0) curved++;
      var max=path.closed?n:n-1;
      for(var s=0;s<max;s++){
        var a1=pts[s].anchor, a2=pts[(s+1)%n].anchor;
        var dx=a2[0]-a1[0], dy=a2[1]-a1[1], len=Math.sqrt(dx*dx+dy*dy);
        if(len<P.minSegment) continue;
        segs++;
        var a=angleDeg(dx,dy);
        if(angleDiff(a,0)<=P.angleTol || angleDiff(a,90)<=P.angleTol) hv++;
        else if(angleDiff(a,45)<=P.angleTol || angleDiff(a,135)<=P.angleTol) diag++;
      }
    }
    var curveRatio=curved/Math.max(1,total);
    var hvRatio=hv/Math.max(1,segs);
    var diagRatio=diag/Math.max(1,segs);
    if(curveRatio>=0.35 && hvRatio<0.60) return "ROUND";
    if(hvRatio>=0.60 && curveRatio<0.25) return "ORTHO";
    if(hvRatio+diagRatio>=0.60 && curveRatio<0.25) return "ANGLED";
    return "MIXED";
  }

  function collapseSegmentHandles(p1,p2) {
    // Cierra solo los handles que pertenecen al segmento p1->p2.
    var changed=0;
    var a1=copyPoint(p1.anchor), a2=copyPoint(p2.anchor);
    if(distance(p1.rightDirection,a1)>0.00001){ p1.rightDirection=[a1[0],a1[1]]; changed++; }
    if(distance(p2.leftDirection,a2)>0.00001){ p2.leftDirection=[a2[0],a2[1]]; changed++; }
    return changed;
  }

  function moveAxis(pp,axis,target) {
    var a=copyPoint(pp.anchor), l=copyPoint(pp.leftDirection), r=copyPoint(pp.rightDirection);
    var d=target-a[axis];
    if(Math.abs(d)<0.00001) return false;
    if(Math.abs(d)>P.maxMove) return false;
    a[axis]=target; l[axis]+=d; r[axis]+=d;
    pp.anchor=a; pp.leftDirection=l; pp.rightDirection=r;
    return true;
  }

  function makeClusters(points, axis) {
    var arr=[];
    for(var i=0;i<points.length;i++) arr.push({pp:points[i], v:points[i].anchor[axis]});
    arr.sort(function(a,b){return a.v-b.v;});
    var clusters=[];
    for(var j=0;j<arr.length;j++){
      var placed=false;
      for(var c=0;c<clusters.length;c++){
        if(Math.abs(arr[j].v-clusters[c].center)<=P.alignTol){
          clusters[c].items.push(arr[j].pp); clusters[c].sum+=arr[j].v; clusters[c].center=clusters[c].sum/clusters[c].items.length; placed=true; break;
        }
      }
      if(!placed) clusters.push({center:arr[j].v,sum:arr[j].v,items:[arr[j].pp]});
    }
    return clusters;
  }

  function alignClusters(points, axis, minCount) {
    var clusters=makeClusters(points, axis);
    var changed=0;
    for(var c=0;c<clusters.length;c++){
      if(clusters[c].items.length<minCount) continue;
      var target=clusters[c].center;
      for(var i=0;i<clusters[c].items.length;i++) if(moveAxis(clusters[c].items[i],axis,target)) changed++;
    }
    return changed;
  }

  function straightenHVInPath(path, strict, collapse) {
    var moved=0, collapsed=0;
    var pts=path.pathPoints, n=pts.length, max=path.closed?n:n-1;
    for(var i=0;i<max;i++){
      var p1=pts[i], p2=pts[(i+1)%n];
      if(strict && !segmentLooksStraight(p1,p2)) continue;
      var a1=p1.anchor, a2=p2.anchor;
      var dx=a2[0]-a1[0], dy=a2[1]-a1[1], len=Math.sqrt(dx*dx+dy*dy);
      if(len<P.minSegment) continue;
      var ang=angleDeg(dx,dy);
      var isH=Math.abs(dy)<=P.alignTol || angleDiff(ang,0)<=P.angleTol;
      var isV=Math.abs(dx)<=P.alignTol || angleDiff(ang,90)<=P.angleTol;
      if(isH){
        var y=(a1[1]+a2[1])/2;
        if(moveAxis(p1,1,y)) moved++;
        if(moveAxis(p2,1,y)) moved++;
        if(collapse) collapsed += collapseSegmentHandles(p1,p2);
      } else if(isV){
        var x=(a1[0]+a2[0])/2;
        if(moveAxis(p1,0,x)) moved++;
        if(moveAxis(p2,0,x)) moved++;
        if(collapse) collapsed += collapseSegmentHandles(p1,p2);
      }
    }
    return {moved:moved, collapsed:collapsed};
  }

  function fixRoundTangents(path) {
    var changed=0;
    var b=boundsOfPaths([path]);
    var tol=clamp(b.scale*0.035, P.alignTol*2.0, P.alignTol*8.0);
    for(var i=0;i<path.pathPoints.length;i++){
      var pp=path.pathPoints[i], a=copyPoint(pp.anchor), l=copyPoint(pp.leftDirection), r=copyPoint(pp.rightDirection);
      var touched=false;
      if(Math.abs(a[0]-b.left)<=tol || Math.abs(a[0]-b.right)<=tol){
        if(Math.abs(l[0]-a[0])<=tol*1.4){ l[0]=a[0]; touched=true; }
        if(Math.abs(r[0]-a[0])<=tol*1.4){ r[0]=a[0]; touched=true; }
      }
      if(Math.abs(a[1]-b.top)<=tol || Math.abs(a[1]-b.bottom)<=tol){
        if(Math.abs(l[1]-a[1])<=tol*1.4){ l[1]=a[1]; touched=true; }
        if(Math.abs(r[1]-a[1])<=tol*1.4){ r[1]=a[1]; touched=true; }
      }
      if(touched){ pp.leftDirection=l; pp.rightDirection=r; try{pp.pointType=PointType.SMOOTH;}catch(e){} changed++; }
    }
    return changed;
  }

  function pathHasRoundHandles(path) {
    var pts=path.pathPoints, curved=0;
    for(var i=0;i<pts.length;i++) if(handleMagnitude(pts[i]) > P.alignTol*2.2) curved++;
    return path.closed && curved/Math.max(1,pts.length) >= 0.25;
  }

  function cleanCandidate(cand) {
    var moved=0, collapsed=0, round=0;
    for(var p=0;p<cand.paths.length;p++){
      var path=cand.paths[p];
      var allPts=[], straightPts=[];
      for(var i=0;i<path.pathPoints.length;i++){
        allPts.push(path.pathPoints[i]);
        if(isStraightPoint(path.pathPoints[i])) straightPts.push(path.pathPoints[i]);
      }
      if(cand.kind==="ORTHO"){
        moved += alignClusters(allPts,0,2);
        moved += alignClusters(allPts,1,2);
        var r1=straightenHVInPath(path,false,true);
        moved += r1.moved; collapsed += r1.collapsed;
      } else if(cand.kind==="ROUND"){
        round += fixRoundTangents(path);
        var r2=straightenHVInPath(path,true,false);
        moved += r2.moved;
      } else if(cand.kind==="ANGLED"){
        moved += alignClusters(straightPts,1,2);
        var r3=straightenHVInPath(path,true,true);
        moved += r3.moved; collapsed += r3.collapsed;
      } else {
        moved += alignClusters(straightPts,0,2);
        moved += alignClusters(straightPts,1,2);
        var r4=straightenHVInPath(path,true,true);
        moved += r4.moved; collapsed += r4.collapsed;
        if(pathHasRoundHandles(path)) round += fixRoundTangents(path);
      }
    }
    return {moved:moved, collapsed:collapsed, round:round};
  }

  function pointLineDistance(p,a,b) {
    var A=p[0]-a[0], B=p[1]-a[1], C=b[0]-a[0], D=b[1]-a[1];
    var len=C*C+D*D; if(len<0.00001) return distance(p,a);
    var t=(A*C+B*D)/len; if(t<0)return distance(p,a); if(t>1)return distance(p,b);
    return distance(p,[a[0]+t*C,a[1]+t*D]);
  }

  function removeExtraPoints(path) {
    var removed=0, minPts=path.closed?4:3;
    for(var i=path.pathPoints.length-1;i>=0;i--){
      var n=path.pathPoints.length; if(n<=minPts)break;
      if(!path.closed && (i===0 || i===n-1))continue;
      var prev=path.pathPoints[(i-1+n)%n], cur=path.pathPoints[i], next=path.pathPoints[(i+1)%n];
      if(!isStraightPoint(cur))continue;
      if(!segmentLooksStraight(prev,cur))continue;
      if(!segmentLooksStraight(cur,next))continue;
      if(distance(cur.anchor,prev.anchor)<=P.removeTol || distance(cur.anchor,next.anchor)<=P.removeTol){ try{cur.remove();removed++;}catch(e1){} continue; }
      var d=pointLineDistance(cur.anchor,prev.anchor,next.anchor);
      if(d<=P.removeTol){
        var a1=angleDeg(cur.anchor[0]-prev.anchor[0], cur.anchor[1]-prev.anchor[1]);
        var a2=angleDeg(next.anchor[0]-cur.anchor[0], next.anchor[1]-cur.anchor[1]);
        if(angleDiff(a1,a2)<=P.angleTol){ try{cur.remove();removed++;}catch(e2){} }
      }
    }
    return removed;
  }

  var cands=collectCandidates(selectedItems);
  if(cands.length===0){ alert("No encontre paths editables. Si es texto vivo: Type > Create Outlines."); return; }

  var allPaths=[];
  for(var ci=0;ci<cands.length;ci++) for(var cp=0;cp<cands[ci].paths.length;cp++) allPaths.push(cands[ci].paths[cp]);
  function countPoints(){ var n=0; for(var p=0;p<allPaths.length;p++) n+=allPaths[p].pathPoints.length; return n; }

  var wordMatches=(mode==="W" && word.length>0 && word.length===cands.length);
  for(var k=0;k<cands.length;k++){
    if(mode==="W" && wordMatches){ cands[k].letter=word.charAt(k); cands[k].kind=letterKind(cands[k].letter); }
    else if(mode==="O") cands[k].kind="ORTHO";
    else if(mode==="R") cands[k].kind="ROUND";
    else cands[k].kind=geometryKind(cands[k]);
  }

  var counts={ORTHO:0,ROUND:0,ANGLED:0,MIXED:0};
  for(var cc=0;cc<cands.length;cc++) counts[cands[cc].kind]++;

  if(mode==="A"){
    alert(
      "AUDIT Logo Clean Master\n\n"+
      "Candidatos: "+cands.length+"\n"+
      "Paths: "+allPaths.length+"\n"+
      "Puntos: "+countPoints()+"\n\n"+
      "ORTHO: "+counts.ORTHO+"\nROUND: "+counts.ROUND+"\nANGLED: "+counts.ANGLED+"\nMIXED: "+counts.MIXED+"\n\n"+
      "alignTol: "+P.alignTol.toFixed(4)+" pt\nremoveTol: "+P.removeTol.toFixed(4)+" pt\nangleTol: "+P.angleTol+" deg"
    );
    return;
  }

  var confirmMsg="Logo Clean Master\n\n"+
    "Modo: "+mode+"\n"+
    "Candidatos: "+cands.length+"\n"+
    "ORTHO: "+counts.ORTHO+", ROUND: "+counts.ROUND+", ANGLED: "+counts.ANGLED+", MIXED: "+counts.MIXED+"\n\n"+
    "No se creara backup. Usa Ctrl+Z si no te gusta.\n\nContinuar?";
  if(mode==="W" && word.length>0 && !wordMatches) confirmMsg += "\n\nAviso: letras ingresadas ("+word.length+") no calzan con candidatos ("+cands.length+"). Se uso clasificacion geometrica.";
  if(!confirm(confirmMsg)) return;

  var before=countPoints();
  var moved=0, collapsed=0, roundFixed=0, removed=0;
  for(var c=0;c<cands.length;c++){
    var res=cleanCandidate(cands[c]);
    moved+=res.moved; collapsed+=res.collapsed; roundFixed+=res.round;
  }
  for(var rp=0;rp<allPaths.length;rp++) removed+=removeExtraPoints(allPaths[rp]);
  var after=countPoints();

  app.redraw();

  var summary="Logo Clean Master v1 terminado\n\n"+
    "Puntos antes: "+before+"\n"+
    "Puntos despues: "+after+"\n"+
    "Puntos eliminados: "+removed+"\n\n"+
    "Alineaciones: "+moved+"\n"+
    "Handles de segmentos rectos cerrados: "+collapsed+"\n"+
    "Tangentes redondas corregidas: "+roundFixed+"\n\n"+
    "ORTHO: "+counts.ORTHO+", ROUND: "+counts.ROUND+", ANGLED: "+counts.ANGLED+", MIXED: "+counts.MIXED+"\n\n"+
    "alignTol: "+P.alignTol.toFixed(4)+" pt, removeTol: "+P.removeTol.toFixed(4)+" pt";

  alert(summary);

  if(confirm("Guardar reporte de aprendizaje para comparar resultados futuros?")){
    var note=prompt("Nota breve del resultado. Ej: bueno / deformo B / faltan redondas", "");
    if(note===null) note="";
    var f=File.saveDialog("Guardar reporte aprendizaje", "Text:*.txt");
    if(f){
      try{
        f.encoding="UTF-8";
        f.open("w");
        f.write(summary+"\n\nModo: "+mode+"\nPalabra: "+word+"\nNota: "+note+"\nFecha: "+(new Date()).toString()+"\n");
        f.close();
      }catch(e){ alert("No pude guardar reporte: "+e); }
    }
  }
})();
