import { chromium } from '@playwright/test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import { createServer } from 'node:http';
import { once } from 'node:events';

const fixtures = JSON.parse(await readFile('tests/fixtures.json','utf8'));
const python = process.env.PYTHON || '.venv/bin/python';
const rendered = JSON.parse(execFileSync(python,['tests/render_fixtures.py'],{encoding:'utf8',env:{...process.env,PYTHONPATH:'src'}}));
const paths = {'/flowtoken.js':'src/py_flowtoken/static/flowtoken.js','/flowtoken.css':'src/py_flowtoken/static/flowtoken.css','/oracle.js':'.local/oracle.js'};
const server = createServer(async(request,response) => {
  if (paths[request.url]) {
    response.setHeader('Content-Type',request.url.endsWith('.css')?'text/css':'text/javascript');
    response.end(await readFile(paths[request.url]));
  } else response.end('<!doctype html><link rel="stylesheet" href="/flowtoken.css"><main id="ours"></main><main id="upstream"></main><script type="module" src="/oracle.js"></script>');
});
server.listen(0,'127.0.0.1');
await once(server,'listening');
const browser = await chromium.launch({channel:process.env.CI?undefined:'chrome',headless:true});
let checks = 0;
try {
 const page = await browser.newPage({extraHTTPHeaders:{'User-Agent':'OpenAI File Downloader, XaiImageApiFetch/1.0'}});
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.goto(`http://127.0.0.1:${server.address().port}`);
 await page.waitForFunction(()=>window.renderUpstream);
 const result = await page.evaluate(async({fixtures,rendered})=>{
  const {FlowToken,FlowMarkdown,animations,tokenize} = await import('/flowtoken.js');
  const ours=document.getElementById('ours'),upstream=document.getElementById('upstream');
  let checks=0;
  const equal=(a,b,label)=>{if(JSON.stringify(a)!==JSON.stringify(b))throw new Error(label+': '+JSON.stringify({a,b}));checks++;};
  equal(animations,window.upstreamAnimations,'animation map');
  for(const sep of ['word','char','diff']) {
   for(const text of fixtures.text) {
    window.renderUpstream(upstream,text,sep);
    await new Promise(resolve=>setTimeout(resolve,0));
    const flow=new FlowToken(ours,{sep,interval:0});flow.setText(text);
    equal(ours.textContent,upstream.textContent,sep+' text');
    if(sep!=='diff')equal(tokenize(text,sep),[...upstream.children].map(node=>node.textContent),sep+' tokens');
    flow.destroy();ours.replaceChildren();
   }
  }
  const flow=new FlowToken(ours,{sep:'word',interval:0});
  for(const text of fixtures.snapshots) {
   window.renderUpstream(upstream,text,'word');
   await new Promise(resolve=>setTimeout(resolve,0));
   flow.setText(text);equal(ours.textContent,upstream.textContent,'snapshot');
  }
  flow.destroy();ours.replaceChildren();
  const semantic=root=>({text:root.textContent.replace(/\s+/g,''),headings:[...root.querySelectorAll('h1,h2,h3')].map(n=>n.textContent),links:[...root.querySelectorAll('a')].map(n=>n.getAttribute('href')),tables:root.querySelectorAll('table').length,items:root.querySelectorAll('li').length,code:[...root.querySelectorAll('pre')].filter(node=>!node.querySelector('pre')).map(n=>n.textContent.replace(/\n$/, ''))});
  for(let i=0;i<fixtures.markdown.length;i++) {
   window.renderUpstream(upstream,fixtures.markdown[i],'word',true);
   await new Promise(resolve=>setTimeout(resolve,0));
   ours.innerHTML=rendered[i];
   equal(semantic(ours),semantic(upstream),'Markdown '+i);
  }
  ours.replaceChildren();
  const smooth=new FlowToken(ours,{interval:40});
  smooth.setText('One two three four');
  await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
  if(!ours.textContent || ours.textContent==='One two three four')throw new Error('Words did not arrive progressively');checks++;
  await smooth.whenIdle();equal(ours.textContent,'One two three four','paced completion');
  const first=ours.firstElementChild;smooth.setText('One two three four five');
  await smooth.whenIdle();if(first!==ours.firstElementChild)throw new Error('Existing words remounted');checks++;
  smooth.setText('A correction');await smooth.whenIdle();equal(ours.textContent,'A correction','correction');
  smooth.setText('A');await smooth.whenIdle();equal(ours.textContent,'A','shorter');
  smooth.setText('');await smooth.whenIdle();equal(ours.textContent,'','reset');
  smooth.setText('👩🏽‍💻 café 日本語');await smooth.whenIdle();equal(ours.textContent,'👩🏽‍💻 café 日本語','unicode');
  smooth.setText('<img src=x onerror="window.injected=true">');await smooth.whenIdle();
  if(ours.querySelector('img')||window.injected)throw new Error('Unsafe plain text');checks++;
  smooth.destroy();ours.replaceChildren();
  const reduced=new FlowToken(ours,{reducedMotion:true});reduced.setText('Immediate readable text');equal(ours.textContent,'Immediate readable text','reduced motion');reduced.destroy();
  ours.replaceChildren();const cancelled=new FlowToken(ours,{interval:200});cancelled.setText('one two three');cancelled.destroy();const before=ours.textContent;
  await new Promise(resolve=>setTimeout(resolve,250));equal(ours.textContent,before,'destroy cancels queue');
  ours.innerHTML=rendered[0];const markdown=new FlowMarkdown(ours);markdown.setRenderedHTML(rendered[1]);equal(semantic(ours).text,'onetwofirstsecond','Markdown update');
  markdown.setRenderedHTML('<div data-flowtoken="markdown"><p onclick="window.injected=true"><script>window.injected=true</script><a href="javascript:alert(1)">safe</a></p></div>');
  if(ours.querySelector('script,[onclick],[href^="javascript:"]'))throw new Error('Unsafe Markdown update');checks++;
  return checks;
 },{fixtures,rendered});
 checks+=result;
 assert.deepEqual(errors,[]);
 console.log(JSON.stringify({result:'passed',browserChecks:checks,upstream:'flowtoken@1.0.40',coverage:['word/char/diff text','animation names','Markdown semantics','incremental snapshots','word pacing','node reuse','corrections','Unicode','reduced motion','cleanup','HTML safety']}));
} finally {await browser.close();server.close();}
