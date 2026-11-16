(() => {
  'use strict';
  const $ = (s, root = document) => root.querySelector(s);
  const $$ = (s, root = document) => [...root.querySelectorAll(s)];
  const data = JSON.parse($('#deck-data').textContent);
  const slides = $$('.slide'), stage = $('#stage'), viewport = $('#viewport');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const exporting = new URLSearchParams(location.search).get('export') === '1';
  let current = -1, paused = false, forceMotion = false, printMode = false, caseIndex = 0;
  let themeBeforePrint = null;
  let generation = 0, pointerStart = null, ignoreClickUntil = 0;
  const timers = new Set(), frames = new Set(), effects = new Set();
  const motionAllowed = () => !paused && (!reduced.matches || forceMotion) && !exporting && !printMode && !document.hidden;
  const later = (fn, ms) => { const id = setTimeout(() => { timers.delete(id); fn(); }, ms); timers.add(id); return id; };
  const every = (fn, ms) => { const id = setInterval(fn, ms); timers.add(id); return id; };
  const frame = fn => { const id = requestAnimationFrame(t => { frames.delete(id); fn(t); }); frames.add(id); return id; };
  const stopEffects = () => {
    generation++;
    timers.forEach(id => { clearTimeout(id); clearInterval(id); }); timers.clear();
    frames.forEach(cancelAnimationFrame); frames.clear();
    effects.forEach(a => a.cancel()); effects.clear();
    $('#hopper').getAnimations({subtree:true}).forEach(a => a.cancel());
    $('#hopper').dataset.phase='stopped';
    $$('.dust').forEach(e => e.remove());
    $('#hopper').style.visibility = 'hidden';
  };
  const animate = (el, keyframes, options) => {
    if (!motionAllowed()) return Promise.resolve();
    const animation = el.animate(keyframes, options); effects.add(animation);
    return animation.finished.catch(() => {}).finally(() => {effects.delete(animation);if(animation.playState==='finished'){try{animation.commitStyles();}catch{/* detached or hidden */}animation.cancel();}});
  };
  const appearance=data.appearance || {default_theme:'light',traveler:{default:'star',per_slide:{},characters:{star:'★'}}};
  const params=new URLSearchParams(location.search);
  const saved=key=>{try{return localStorage.getItem('presentation-kit:'+key);}catch{return null;}};
  const save=(key,value)=>{try{localStorage.setItem('presentation-kit:'+key,value);}catch{/* file previews can deny local storage */}};
  const motionPreference=exporting?'system':(params.get('motion') || saved('motion') || 'system');
  forceMotion=motionPreference==='on'; paused=motionPreference==='off';
  const syncMotionUI=()=>{
    const systemBlocked=reduced.matches&&!forceMotion;
    const on=!paused&&!systemBlocked;
    document.body.classList.toggle('motion-forced',forceMotion);
    document.body.classList.toggle('reduced',systemBlocked);
    document.body.classList.toggle('paused',paused);
    const label=on?'Выключить анимации':'Включить анимации';
    $('#motion-button').textContent=label;$('#motion-button').setAttribute('aria-label',label);$('#motion-button').setAttribute('aria-pressed',String(on));
    $('#motion-status').textContent=on?'Анимации включены: персонаж, графики и события.':systemBlocked&&!paused?'На устройстве включено уменьшение движения. Можно включить анимации только для этой презентации.':'Анимации выключены. Слайды остаются доступны.';
    $('#motion-notice').hidden=exporting||paused||!systemBlocked;
  };
  syncMotionUI();
  const setTheme=(value,persist=false)=>{const theme=value==='dark'?'dark':'light';document.body.dataset.theme=theme;$('#theme-button').setAttribute('aria-pressed',String(theme==='dark'));$('#theme-button').setAttribute('aria-label',theme==='dark'?'Включить светлую тему':'Включить тёмную тему');$('#theme-button').textContent=theme==='dark'?'Включить светлую тему':'Включить тёмную тему';if(persist)save('theme',theme);};
  setTheme(params.get('theme') || (exporting ? 'light' : saved('theme')) || appearance.default_theme);
  const setTraveler=()=>{const kind=appearance.traveler.per_slide[slides[current]?.id] || appearance.traveler.default;const glyph=appearance.traveler.characters[kind] || '★';const spin=$('#hopper .traveler-spin');spin.replaceChildren();if(kind==='star')spin.append($('#star-template').content.cloneNode(true));else{const icon=document.createElement('span');icon.className='traveler-glyph';icon.textContent=glyph;spin.append(icon);}$('#hopper').dataset.kind=kind;};
  const theme=()=>setTheme(document.body.dataset.theme==='dark'?'light':'dark',true);
  $('#theme-button').addEventListener('click',theme);
  const format = n => Math.round(n).toLocaleString('ru-RU');
  const level = v => v >= 85 ? ['critical', '#dc347a'] : v >= 60 ? ['high', '#dc651b'] : v >= 30 ? ['medium', '#b7740b'] : ['low', '#078659'];
  const fit = () => { stage.style.transform = `translate(-50%,-50%) scale(${Math.min(innerWidth / 1920, innerHeight / 1080)})`; };
  window.addEventListener('resize', fit); fit();
  document.body.classList.toggle('export-mode', exporting);
  syncMotionUI();

  // Illustrative charts: these arrays are deliberately separate from measured results.
  const bars = (selector, values, hot) => {
    const parent = $(selector);
    values.forEach((value, i) => { const bar = document.createElement('i'); bar.style.height = `${value}%`; bar.style.setProperty('--i', i); if (hot(value, i)) bar.className = 'hot'; parent.append(bar); });
  };
  bars('#problem-bars', [15,12,18,16,22,18,15,17,13,19,25,16,14,19,100,96,87,23,21,18,17,20], v => v > 70);
  bars('#day-chart', [22,25,21,28,24,23,100,27,24,25], v => v > 70);
  bars('#buy-chart', Array.from({length:96}, (_,i) => i >= 46 && i < 54 ? 72 + 20 * Math.sin((i-46)/7*Math.PI) : 5 + i*13%7), v => v > 30);
  bars('#viral-chart', Array.from({length:96}, (_,i) => 6 + 69*Math.exp(-Math.pow((i-47)/22,2)) + i*7%5), v => v > 30);
  let seed = 17; const random = () => (seed = seed * 16807 % 2147483647) / 2147483647;
  const colors = ['#edf0ed','#d8ecda','#96cfa2','#47aa6d','#168646'];
  for (let i = 0; i < 182; i++) { const cell = document.createElement('i'); if(Math.floor(i/7)===19)cell.className='spike'; cell.style.background = Math.floor(i/7) === 19 ? '#dc347a' : colors[Math.floor(random()*5)]; $('#contribution-grid').append(cell); }
  for (let i = 0; i < 32; i++) { const piece = document.createElement('i'); piece.className = 'confetti-piece'; piece.style.cssText = `--x:${random()*100}%;--delay:${-random()*4.5}s;--piece-color:${['#3557eb','#7945e8','#dc347a','#ffcf3e'][i%4]}`; $('#confetti').append(piece); }
  // Original pixel owl, retained from the supplied kit.
  const owl = ['...k........k...','..kbk......kbk..','..kbbkkkkkkbbk..','.kbbbbbbbbbbbbk.','.kbwwwwbbwwwwbk.','kbwwppwbbwppwwbk','kbwwppwyywppwwbk','.kbwwwwyywwwwbk.','.kbbbbbbbbbbbbk.','.kbdllllllllldk.','.kbllgllllgllbk.','.kbllllllllllbk.','..kbllgllgllbk..','..kkbbbbbbbbkk..','...kookkkkook...','................'];
  const owlBlink = owl.map((r,i) => i === 5 ? 'kbwkkkkbbkkkkwbk' : i === 6 ? 'kbwwwwwyywwwwwbk' : r);
  const palette = {k:'#171927',p:'#171927',b:'#7945e8',d:'#5130aa',l:'#e9ddff',w:'#fff',y:'#ffcf3e',o:'#df9f20',g:'#ffcf3e'};
  const canvas = document.createElement('canvas'); canvas.width=256; canvas.height=128; const ctx=canvas.getContext('2d');
  [owl,owlBlink].forEach((f,n) => f.forEach((r,y) => [...r].forEach((c,x) => { if(c!=='.'){ctx.fillStyle=palette[c];ctx.fillRect((x+n*16)*8,y*8,8,8);} })));
  $$('[data-mascot]').forEach(el => el.style.backgroundImage=`url(${canvas.toDataURL()})`);

  const updateCase = (index, animated = true) => {
    caseIndex = index % data.cases.length;
    const item = data.cases[caseIndex], [label] = level(item.score), color = `var(--${{low:'green',medium:'amber',high:'orange',critical:'pink'}[label]})`, gauge = $('#gauge');
    $('#case-repo').textContent=item.repo; $('#case-reason').textContent=item.reason; $('#score-level').textContent=label.toUpperCase();
    gauge.style.setProperty('--score-color',color);
    $$('.heuristic').forEach(el => el.classList.toggle('hit',item.hits.includes(el.dataset.key)));
    $$('[data-case]').forEach((b,i) => b.setAttribute('aria-pressed',String(i===caseIndex)));
    const from = Number($('#score-value').textContent), token=generation;
    if (!animated || !motionAllowed()) { gauge.style.setProperty('--score',item.score); $('#score-value').textContent=item.score; return; }
    const start=performance.now();
    const tick = time => { if(token!==generation) return; const p=Math.min((time-start)/850,1), value=from+(item.score-from)*(1-Math.pow(1-p,3)); gauge.style.setProperty('--score',value); $('#score-value').textContent=Math.round(value); if(p<1)frame(tick); };
    frame(tick);
  };
  // Translation, squash and 3D rotation have separate layers, so landing cannot erase spin.
  const idleTraveler=(token)=>{
    if(token!==generation || !motionAllowed())return;
    const hopper=$('#hopper'),body=$('.traveler-body',hopper),spin=$('.traveler-spin',hopper),shadow=$('.traveler-shadow',hopper);
    hopper.dataset.phase='idle';
    const loop=(element,keys,options)=>{const animation=element.animate(keys,options);effects.add(animation);};
    loop(spin,[{transform:'rotateX(16deg) rotateY(0deg) rotateZ(-9deg)'},{transform:'rotateX(-12deg) rotateY(180deg) rotateZ(9deg)'},{transform:'rotateX(16deg) rotateY(360deg) rotateZ(-9deg)'}],{duration:6800,iterations:Infinity,easing:'linear'});
    loop(body,[{transform:'translateY(0) scale(1)'},{transform:'translateY(-9px) scale(1)'},{transform:'translateY(0) scale(1)'}],{duration:2400,iterations:Infinity,easing:'ease-in-out'});
    loop(shadow,[{transform:'scaleX(1)',opacity:.24},{transform:'scaleX(.72)',opacity:.12},{transform:'scaleX(1)',opacity:.24}],{duration:2400,iterations:Infinity,easing:'ease-in-out'});
  };
  const hops = async (slide, token) => {
    if (!motionAllowed() || token!==generation) return;
    const hopper=$('#hopper'),body=$('.traveler-body',hopper),spin=$('.traveler-spin',hopper),shadow=$('.traveler-shadow',hopper);
    const k=Math.min(innerWidth/1920,innerHeight/1080),sr=stage.getBoundingClientRect();
    const point=el=>{const r=el.getBoundingClientRect();return{x:Math.min(1770,Math.max(30,(r.left-sr.left+r.width*.65)/k-50)),y:Math.max(75,(r.top-sr.top)/k-110)};};
    const title=$('h1,h2',slide);
    const targets=$$('[data-hop], .member, .metric, .method-evidence',slide).filter(e=>e!==title).slice(0,3);
    const points=targets.map(point);
    if(title){const range=document.createRange();range.selectNodeContents(title);const rects=[...range.getClientRects()].filter(r=>r.width>2);const last=rects[rects.length-1]||title.getBoundingClientRect();points.push({x:Math.min(1770,Math.max(30,(last.right-sr.left)/k+20)),y:Math.max(75,(last.top-sr.top)/k-35)});}
    let previous={x:1740,y:840};hopper.style.visibility='visible';
    body.style.transform='none';spin.style.transform='rotateX(16deg) rotateY(0deg) rotateZ(-9deg)';
    for(const p of points){
      if(token!==generation || !motionAllowed())return;
      hopper.dataset.phase='jump';
      const peak=Math.max(20,Math.min(p.y,previous.y)-170);
      const path=Array.from({length:25},(_,i)=>{const t=i/24;return{transform:`translate(${previous.x+(p.x-previous.x)*t}px,${(1-t)**2*previous.y+2*(1-t)*t*peak+t*t*p.y}px)`};});
      const rotation=Array.from({length:13},(_,i)=>{const t=i/12;return{transform:`rotateX(${16+24*Math.sin(t*Math.PI)}deg) rotateY(${360*t}deg) rotateZ(${-9+720*t}deg)`};});
      await Promise.all([
        animate(hopper,path,{duration:820,fill:'forwards',easing:'cubic-bezier(.2,.55,.35,1)'}),
        animate(spin,rotation,{duration:820,fill:'forwards',easing:'linear'}),
        animate(shadow,[{opacity:.22,transform:'scaleX(1)'},{opacity:.05,transform:'scaleX(.4)'},{opacity:.22,transform:'scaleX(1)'}],{duration:820,fill:'forwards'})
      ]);
      if(token!==generation)return;
      hopper.dataset.phase='landing';
      await animate(body,[{transform:'translateY(4px) scale(1.18,.78)'},{transform:'translateY(-5px) scale(.94,1.06)'},{transform:'translateY(0) scale(1)'}],{duration:260,fill:'forwards',easing:'ease-out'});
      if(token!==generation)return;
      previous=p;
    }
    idleTraveler(token);
  };
  const play = () => {
    stopEffects(); $$('.heuristic').forEach(el=>el.classList.remove('checking')); const slide=slides[current], token=generation;
    if(!slide) return;
    $$('[data-count]',slide).forEach(el => el.textContent=(el.dataset.prefix||'')+format(Number(el.dataset.count)));
    if(slide.id==='s7')updateCase(caseIndex,false);
    if(!motionAllowed())return;
    $$('[data-count]',slide).forEach(el => {
      const start=performance.now(), target=Number(el.dataset.count);
      const tick = t => {if(token!==generation)return;const p=Math.min((t-start)/1700,1);el.textContent=(el.dataset.prefix||'')+format(target*(1-(1-p)**3));if(p<1)frame(tick);};frame(tick);
    });
    later(()=>hops(slide,token),900);
    if(slide.id==='s7'){
      every(()=>updateCase(caseIndex+1),4400);
      let checkIndex=0;const checks=$$('.heuristic');
      every(()=>{checks.forEach((el,i)=>el.classList.toggle('checking',i===checkIndex%checks.length));checkIndex++;},650);
    }
    if(slide.id==='s8'){let n=0;const rows=$$('.method-step',slide);every(()=>{rows.forEach((r,i)=>r.classList.toggle('lit',i===n%rows.length));n++;},1400);}
    if(slide.id==='s9'){let n=0;const rows=$$('tbody tr[data-result]',slide);every(()=>{rows.forEach((r,i)=>r.classList.toggle('scan',i===n%rows.length));n++;},900);}
  };
  const chapters=[...new Set(slides.map(s=>s.dataset.chapter))];
  chapters.forEach(ch=>{const b=document.createElement('button');b.textContent=ch;b.addEventListener('click',()=>go(slides.findIndex(s=>s.dataset.chapter===ch)));$('#chapters').append(b);});
  slides.forEach((s,i)=>{s.dataset.page=`${String(i+1).padStart(2,'0')} / ${slides.length}`;$$('.reveal',s).forEach((el,j)=>el.style.setProperty('--delay',`${Math.min(j*80,480)}ms`));});
  function go(index){
    const next=Math.max(0,Math.min(slides.length-1,Math.trunc(Number(index))||0));
    if(next===current)return;
    const old=slides[current]; if(old?.contains(document.activeElement)) document.activeElement.blur();
    current=next;setTraveler();
    slides.forEach((s,i)=>{s.classList.toggle('active',i===current);s.setAttribute('aria-hidden',String(i!==current));s.inert=i!==current;});
    $('#counter').textContent=`${current+1} / ${slides.length}`; $('#page-label').textContent=slides[current].dataset.page;
    $('#progress').style.width=`${(current+1)/slides.length*100}%`;$('#prev').disabled=current===0;$('#next').disabled=current===slides.length-1;
    $$('#chapters button').forEach(b=>b.setAttribute('aria-current',String(b.textContent===slides[current].dataset.chapter)));
    $$('[data-goto]').forEach(b=>b.setAttribute('aria-current',String(Number(b.dataset.goto)===current)));
    $('#note-heading').textContent=`${current+1}. ${slides[current].dataset.title}`;$('#note-text').textContent=data.notes[slides[current].id]||'';
    try{history.replaceState(null,'',`#slide-${current+1}`);}catch{/* sandboxed file previews may disallow history */}
    play();
  }
  const next=()=>go(current+1),prev=()=>go(current-1);
  $('#next').addEventListener('click',next);$('#prev').addEventListener('click',prev);
  const settings=$('#settings');
  $('#settings-button').addEventListener('click',()=>settings.showModal());
  $('#settings-close').addEventListener('click',()=>settings.close());
  const notes=()=>{settings.close();const hidden=!$('#notes').hidden;$('#notes').hidden=hidden;$('#notes-button').setAttribute('aria-expanded',String(!hidden));$('#notes-button').textContent=hidden?'Показать заметки докладчика':'Скрыть заметки докладчика';};
  $('#notes-button').addEventListener('click',notes);
  const overview=$('#overview');
  const openOverview=()=>{if(overview.open){overview.close();return;}overview.showModal();};
  $('#overview-button').addEventListener('click',openOverview);$('#overview-close').addEventListener('click',()=>overview.close());
  $$('[data-goto]').forEach(b=>b.addEventListener('click',()=>{go(Number(b.dataset.goto));overview.close();}));
  const motion=()=>{
    if(paused || (reduced.matches&&!forceMotion)){paused=false;forceMotion=true;save('motion','on');}
    else{paused=true;forceMotion=false;save('motion','off');}
    syncMotionUI();play();
  };
  $('#motion-button').addEventListener('click',motion);
  $('#enable-motion').addEventListener('click',motion);
  const fullscreen=async()=>{settings.close();try{if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen();}catch{$('#fullscreen-button').title='Полноэкранный режим недоступен в этом просмотрщике';}};
  $('#fullscreen-button').addEventListener('click',fullscreen);
  $$('[data-case]').forEach(b=>b.addEventListener('click',()=>{stopEffects();updateCase(Number(b.dataset.case));}));
  const interactive=target=>target instanceof Element && target.closest('button,a,input,textarea,select,dialog,[contenteditable="true"]');
  document.addEventListener('keydown',e=>{
    if(overview.open || settings.open || interactive(e.target) || e.ctrlKey || e.altKey || e.metaKey)return;
    if(['ArrowRight','PageDown',' ','Enter'].includes(e.key)){e.preventDefault();next();}
    else if(['ArrowLeft','PageUp','Backspace'].includes(e.key)){e.preventDefault();prev();}
    else if(e.key==='Home'){e.preventDefault();go(0);}else if(e.key==='End'){e.preventDefault();go(slides.length-1);}
    else if(['n','т'].includes(e.key.toLowerCase()))notes();else if(['f','а'].includes(e.key.toLowerCase()))fullscreen();
    else if(['t','е'].includes(e.key.toLowerCase()))theme();
    else if(['m','ь'].includes(e.key.toLowerCase()))motion();else if(['o','щ'].includes(e.key.toLowerCase()))openOverview();
  });
  viewport.addEventListener('pointerdown',e=>{if(!interactive(e.target)&&e.isPrimary)pointerStart={x:e.clientX,y:e.clientY,id:e.pointerId};});
  viewport.addEventListener('pointercancel',()=>pointerStart=null);
  viewport.addEventListener('pointerup',e=>{if(!pointerStart||pointerStart.id!==e.pointerId)return;const dx=e.clientX-pointerStart.x,dy=e.clientY-pointerStart.y;pointerStart=null;if(Math.abs(dx)>50&&Math.abs(dx)>Math.abs(dy)*1.3){ignoreClickUntil=performance.now()+600;(dx<0?next:prev)();}});
  viewport.addEventListener('click',e=>{if(interactive(e.target)||performance.now()<ignoreClickUntil)return;(e.clientX>innerWidth/3?next:prev)();});
  const fromHash=()=>{const m=/^#slide-(\d+)$/.exec(location.hash);return m?Number(m[1])-1:0;};
  window.addEventListener('hashchange',()=>go(fromHash()));
  reduced.addEventListener('change',()=>{syncMotionUI();play();});
  document.addEventListener('visibilitychange',()=>play());
  window.addEventListener('beforeprint',()=>{printMode=true;themeBeforePrint=document.body.dataset.theme;setTheme('light');stopEffects();updateCase(0,false);});
  window.addEventListener('afterprint',()=>{printMode=false;if(themeBeforePrint)setTheme(themeBeforePrint);play();});
  window.__go=go;
  window.deckState=()=>({slide:current+1,total:slides.length,timers:timers.size,frames:frames.size,effects:effects.size,paused,forceMotion,motionEnabled:!paused&&(!reduced.matches||forceMotion),reduced:reduced.matches,exporting,theme:document.body.dataset.theme,traveler:$('#hopper').dataset.kind,travelerPhase:$('#hopper').dataset.phase});
  go(fromHash());
})();
