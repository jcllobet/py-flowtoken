export async function parityChecks({FlowMarkdown,animations},fixtures,rendered) {
  const ours=document.getElementById('ours'),upstream=document.getElementById('upstream');
  let checks=0;
  const equal=(actual,expected,label)=>{
    if(JSON.stringify(actual)!==JSON.stringify(expected))throw new Error(label+': '+JSON.stringify({actual,expected}));
    checks++;
  };
  const tick=()=>new Promise(resolve=>setTimeout(resolve,0));
  const semantics=root=>({
    paragraphs:[...root.querySelectorAll('p')].map(node=>node.textContent),
    headings:[...root.querySelectorAll('h1,h2,h3')].map(node=>node.textContent),
    links:[...root.querySelectorAll('a')].map(node=>[node.textContent,node.getAttribute('href'),node.target,node.rel]),
    tables:[...root.querySelectorAll('tr')].map(row=>[...row.querySelectorAll('th,td')].map(node=>node.textContent)),
    items:[...root.querySelectorAll('li')].map(node=>node.textContent),
    code:[...root.querySelectorAll('pre code')].map(node=>node.textContent.replace(/\n$/,'')),
    images:[...root.querySelectorAll('img')].map(node=>[node.alt,node.getAttribute('src')]),
    tasks:[...root.querySelectorAll('input')].map(node=>[node.type,node.checked,node.disabled]),
  });
  equal(animations,window.upstreamAnimations,'animation names');
  const reference=document.createElement('link');reference.rel='stylesheet';reference.href='/upstream.css';
  document.head.append(reference);await new Promise(resolve=>reference.onload=resolve);
  const projectSheet=document.querySelector('link[href="/flowtoken.css"]').sheet;
  const properties=['opacity','transform','filter','color','backgroundColor','offset'];
  const frames=element=>element.getAnimations()[0].effect.getKeyframes().map(frame=>Object.fromEntries(properties.filter(key=>frame[key]!==undefined).map(key=>[key,frame[key]])));
  for(const animation of Object.keys(animations).filter(name=>name!=='typewriter')) {
    reference.sheet.disabled=false;projectSheet.disabled=true;
    window.renderMarkdown(upstream,{content:'Animation '+animation,animation,animationDuration:'100s',animationTimingFunction:'cubic-bezier(0.2, 0, 0.4, 1)'});
    await tick();
    const original=upstream.querySelector('span[style*="animation-name"]');
    const expected=frames(original);
    reference.sheet.disabled=true;projectSheet.disabled=false;
    ours.innerHTML=rendered.cases.diffBefore;
    const view=new FlowMarkdown(ours.firstElementChild,{animation,duration:'100s',easing:'cubic-bezier(0.2, 0, 0.4, 1)',interval:0});
    const token=ours.querySelector('.ft-token');
    equal(frames(token),expected,'computed keyframes '+animation);
    equal(getComputedStyle(token).animationTimingFunction,'cubic-bezier(0.2, 0, 0.4, 1)','easing '+animation);
    view.destroy();
  }
  reference.remove();
  for(let i=0;i<fixtures.markdown.length;i++) {
    window.renderMarkdown(upstream,{content:fixtures.markdown[i],sep:'word'});await tick();
    ours.innerHTML=rendered.markdown[i];const view=new FlowMarkdown(ours.firstElementChild,{interval:0});
    equal(semantics(ours),semantics(upstream),'public Markdown '+i);
    view.destroy();
  }
  for(const sep of ['word','char','diff']) {
    ours.innerHTML=rendered.cases.diffBefore;
    const view=new FlowMarkdown(ours.firstElementChild,{sep,interval:0});
    for(const text of fixtures.snapshots) {
      window.renderMarkdown(upstream,{content:text,sep});await tick();
      const safe=text.replaceAll('&','&amp;').replaceAll('<','&lt;');
      view.setRenderedHTML(`<div data-flowtoken="markdown"><p>${safe}</p></div>`);
      equal(ours.textContent,upstream.textContent,sep+' public snapshots');
    }
    view.destroy();
  }
  for(const text of fixtures.text.filter(Boolean)) {
    window.renderMarkdown(upstream,{content:text,sep:'word'});await tick();
    equal(upstream.querySelector('p').textContent,text,'upstream exact whitespace');
  }
  window.renderCustom(upstream);await tick();
  ours.innerHTML=rendered.cases.custom;const custom=new FlowMarkdown(ours.firstElementChild,{interval:0});
  equal(ours.querySelector('mark').textContent,upstream.querySelector('mark').textContent,'custom component');custom.destroy();
  return checks;
}
