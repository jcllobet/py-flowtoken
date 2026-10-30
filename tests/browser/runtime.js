export async function runtimeChecks({FlowToken,FlowMarkdown,mount,unmount,mountAll,tokenize},cases) {
  const ours=document.getElementById('ours');
  let checks=0;
  const equal=(actual,expected,label)=>{
    if(JSON.stringify(actual)!==JSON.stringify(expected))throw new Error(label+': '+JSON.stringify({actual,expected}));checks++;
  };
  const ok=(actual,label)=>equal(Boolean(actual),true,label);
  const tick=()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
  const open=(html,options={interval:0})=>{
    ours.innerHTML=html;
    return new FlowMarkdown(ours.firstElementChild,options);
  };
  const html=text=>`<div data-flowtoken="markdown"><p>${text}</p></div>`;
  let view=open(cases.diffBefore);
  const paragraph=ours.querySelector('p'),prefix=ours.querySelector('.ft-token');
  const prefixAnimation=prefix.getAnimations()[0];
  view.setRenderedHTML(cases.diffAfter);await view.whenIdle();
  equal(ours.textContent.trim(),'Hello world','diff append text');
  ok(ours.querySelector('p')===paragraph,'paragraph retained');
  ok(ours.querySelector('.ft-token')===prefix,'diff prefix retained');
  ok(prefix.getAnimations()[0]===prefixAnimation,'prefix animation retained');
  const selection=getSelection();const range=document.createRange();range.selectNodeContents(prefix);selection.removeAllRanges();selection.addRange(range);
  view.setRenderedHTML(cases.diffAfter);
  equal(selection.toString(),'Hello','prefix selection retained');selection.removeAllRanges();
  equal([...ours.querySelectorAll('.ft-chunk')].map(node=>node.textContent),['Hello',' world'],'diff boundaries');
  view.setRenderedHTML(cases.diffAfter);
  equal(ours.querySelectorAll('.ft-chunk').length,2,'duplicate is no-op');view.destroy();

  view=open(cases.structuredBefore);const strong=ours.querySelector('strong');
  view.setRenderedHTML(cases.structuredAfter);
  ok(ours.querySelector('strong')===strong,'nested element retained');
  equal(ours.textContent.trim(),'Hello world again','nested append');view.destroy();
  view=open(html('A <em>word</em> end'));
  view.setRenderedHTML(html('<em>A word</em> end'));
  equal(ours.querySelector('p').textContent,'A word end','Markdown structure change');
  equal(ours.querySelector('em').textContent,'A word','formatting move');view.destroy();
  view=open('<div data-flowtoken="markdown"><p data-ft-key="a">A</p><p data-ft-key="b">B</p></div>');
  const keyed=ours.querySelector('[data-ft-key="a"]');
  view.setRenderedHTML('<div data-flowtoken="markdown"><p data-ft-key="b">B</p><p data-ft-key="a">A!</p></div>');
  ok(ours.querySelector('[data-ft-key="a"]')===keyed,'keyed node retained after reorder');
  equal(ours.textContent,'BA!','key reorder text');view.destroy();

  view=open(cases.table);view.setRenderedHTML(cases.table);
  equal([...ours.querySelectorAll('th')].map(node=>getComputedStyle(node).textAlign),['left','right'],'table alignment');view.destroy();
  view=open(cases.diffBefore);view.setRenderedHTML(cases.badLink);await view.whenIdle();
  ok(!ours.querySelector('a[href]'),'malformed Python URL rejected');
  for(const unsafe of ['http://[','http://%5B','javascript:alert(1)','data:text/html,foo','java\nscript:alert(1)']) {
    view.setRenderedHTML(html(`<a href="${unsafe}">safe</a>`));
    ok(!ours.querySelector('a[href]'),'malformed or unsafe browser URL rejected');
  }
  view.setRenderedHTML(html('<a href="https://example.com" target="_blank" onclick="bad()">safe</a><script>bad()</script>'));
  equal(ours.querySelector('a').rel,'noopener noreferrer','safe blank link');
  ok(!ours.querySelector('script,[onclick]'),'unsafe markup rejected');view.destroy();

  view=open(cases.multilineCode);
  const code=ours.querySelector('code');
  equal(code.textContent,'first = 1\nsecond = 2\n','code exact whitespace');
  const codeWords=[...code.querySelectorAll('.ft-token')];
  ok(codeWords.find(node=>node.textContent==='second').getBoundingClientRect().top>codeWords.find(node=>node.textContent==='first').getBoundingClientRect().top,'code visual line break');
  ok(!codeWords.some(node=>/^\s+$/.test(node.textContent)),'whitespace uses native text');
  ok([...code.querySelectorAll('span[style]')].some(node=>node.style.color),'syntax highlighting');
  equal(ours.querySelector('[data-ft-code]').dataset.ftTheme,'monokai','code theme');
  equal(getComputedStyle(ours.querySelector('[data-ft-code]')).backgroundColor,'rgb(39, 40, 34)','theme background');
  let copied;
  Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async text=>{copied=text;}}});
  ours.querySelector('button').click();await tick();
  equal(copied,'first = 1\nsecond = 2\n','exact clipboard text');
  equal(ours.querySelector('button').textContent,'Copied!','copy success feedback');
  navigator.clipboard.writeText=async()=>{throw new Error('denied');};
  ours.querySelector('button').click();await tick();
  equal(ours.querySelector('button').textContent,'Copy failed','copy failure feedback');
  await new Promise(resolve=>setTimeout(resolve,2050));
  equal(ours.querySelector('button').textContent,'Copy code','copy feedback resets');view.destroy();

  view=open(cases.custom);const mark=ours.querySelector('mark');view.setRenderedHTML(cases.customAfter);
  ok(ours.querySelector('mark')===mark,'custom node retained');view.destroy();
  view=open(cases.diffBefore);view.setRenderedHTML(cases.disabled);
  equal(ours.textContent.trim(),'Hello world again','disabled animation immediate');
  ok([...ours.querySelectorAll('.ft-token')].every(node=>!node.style.animationName||node.style.animationName==='none'),'disabled animation styles');view.destroy();

  ours.innerHTML='<div class="ft-text"></div>';
  const smooth=new FlowToken(ours.firstElementChild,{interval:60});
  smooth.setText('One two three four');await tick();
  ok(ours.textContent.length>0&&ours.textContent!=='One two three four','paced words');
  await smooth.whenIdle();equal(ours.textContent,'One two three four','paced completion');
  const first=ours.querySelector('.ft-token');smooth.append(' five');await smooth.whenIdle();
  ok(first===ours.querySelector('.ft-token'),'word prefix retained');
  for(const text of ['One changed','A','', '👩🏽‍💻 café 日本語','<img src=x onerror=bad()>']) {
    smooth.setText(text);smooth.flush();equal(ours.textContent,text,'corrections and Unicode');
  }
  ok(!ours.querySelector('img'),'plain text escaped');smooth.destroy();
  for(const sep of ['word','char','diff']) {
    ours.innerHTML='<div class="ft-text"></div>';
    const text=new FlowToken(ours.firstElementChild,{interval:0,sep});
    for(const chunk of ['Hel','lo','  ','world','\n','👩','🏽','‍','💻']) text.append(chunk);
    equal(ours.textContent,'Hello  world\n👩🏽‍💻','chunk boundaries '+sep);
    text.destroy();
  }
  equal(tokenize('A  B\nC','word'),['A','  ','B','\n','C'],'whitespace tokens');
  equal(tokenize('😀','char'),['😀'],'Unicode codepoints');
  ours.innerHTML='<div></div>';const configured=new FlowToken(ours.firstElementChild,{interval:0});
  configured.setText('Hello world');configured.configure({sep:'char'});configured.append('!');
  equal(ours.textContent,'Hello world!','separator configuration preserves text');
  equal(ours.querySelectorAll('.ft-token').length,11,'separator configuration retokenizes');
  let invalid=false;try{configured.configure({duration:'invalid'});}catch{invalid=true;}
  ok(invalid,'invalid configuration rejects');
  configured.configure({sep:'word'});configured.append(' valid');
  equal(ours.textContent,'Hello world! valid','invalid configuration leaves state usable');configured.destroy();
  ours.innerHTML='<div class="ft-text"></div>';
  const multiline=new FlowToken(ours.firstElementChild,{interval:0});multiline.setText('A\nB');
  const words=ours.querySelectorAll('.ft-token');ok(words[1].getBoundingClientRect().top>words[0].getBoundingClientRect().top,'plain text visual newline');multiline.destroy();

  ours.innerHTML=cases.initial;mountAll(ours.firstElementChild);
  const mounted=mount(ours.firstElementChild);
  equal(ours.querySelector('.ft-token').style.animationName,'ft-fadeIn','SSR initial animation');
  mounted.destroy();const remounted=mount(ours.firstElementChild,{interval:0});
  ok(mounted!==remounted,'destroy removes cached instance');remounted.setText('Remounted');
  equal(ours.textContent,'Remounted','remount works');unmount(ours.firstElementChild);
  const again=mount(ours.firstElementChild,{interval:0});ok(again!==remounted,'explicit unmount');again.destroy();
  ours.innerHTML=cases.initial;const quiet=mount(ours.firstElementChild,{animateInitial:false});
  equal(ours.textContent,'Hello initial animation','skip initial animation keeps text');
  ok([...ours.querySelectorAll('.ft-token')].every(node=>!node.style.animationName),'skip initial animation styles');quiet.destroy();
  ours.innerHTML=cases.initial;const reduced=mount(ours.firstElementChild,{reducedMotion:true});
  ok([...ours.querySelectorAll('.ft-token')].every(node=>!node.style.animationName),'reduced motion initial');reduced.destroy();
  ours.innerHTML='<div></div>';const cancelled=new FlowToken(ours.firstElementChild,{interval:1000});
  cancelled.setText('one two three');const idle=cancelled.whenIdle();cancelled.destroy();await idle;
  const before=ours.textContent;await tick();equal(ours.textContent,before,'destroy cancels queue');
  let threw=false;try{cancelled.append('late');}catch{threw=true;}ok(threw,'destroyed methods reject');

  ours.innerHTML='<div></div>';const fast=new FlowToken(ours.firstElementChild,{interval:0,animateInitial:false});
  fast.setText('word '.repeat(1000));
  const split=String.prototype.split;let maximum=0;
  String.prototype.split=function(...args){maximum=Math.max(maximum,this.length);return split.apply(this,args);};
  try{for(let index=0;index<100;index++)fast.append('next ');}finally{String.prototype.split=split;}
  ok(maximum<=6,'append only tokenizes boundary, not full history');
  equal(ours.textContent,'word '.repeat(1000)+'next '.repeat(100),'long stream output');fast.destroy();
  return checks;
}
