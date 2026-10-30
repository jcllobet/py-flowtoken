import { chromium } from '@playwright/test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import { createServer } from 'node:http';
import { once } from 'node:events';

const fixtures = JSON.parse(await readFile('tests/fixtures.json', 'utf8'));
const python = process.env.PYTHON || '.venv/bin/python';
const rendered = JSON.parse(execFileSync(python, ['tests/render_fixtures.py'], {encoding:'utf8',env:{...process.env,PYTHONPATH:'src'}}));
const paths = {
  '/flowtoken.js':'src/py_flowtoken/static/py_flowtoken/flowtoken.js',
  '/flowtoken.css':'src/py_flowtoken/static/py_flowtoken/flowtoken.css',
  '/oracle.js':'.local/oracle.js',
  '/parity.js':'tests/browser/parity.js',
  '/runtime.js':'tests/browser/runtime.js',
  '/upstream.css':'node_modules/flowtoken/dist/styles.css',
};
const server = createServer(async(request,response) => {
  if (paths[request.url]) {
    response.setHeader('Content-Type',request.url.endsWith('.css')?'text/css':'text/javascript');
    response.end(await readFile(paths[request.url]));
  } else if (request.url.endsWith('.png')) {
    response.writeHead(404);response.end();
  } else {
    response.end('<!doctype html><link rel="stylesheet" href="/flowtoken.css"><main id="ours"></main><main id="upstream"></main><script type="module" src="/oracle.js"></script>');
  }
});
server.listen(0,'127.0.0.1');
await once(server,'listening');
const browser = await chromium.launch({channel:process.env.CI?undefined:'chrome',headless:true});
try {
  const page = await browser.newPage({extraHTTPHeaders:{'User-Agent':'OpenAI File Downloader, XaiImageApiFetch/1.0'}});
  await page.route('https://example.com/image.png',route=>route.abort());
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto(`http://127.0.0.1:${server.address().port}`);
  await page.waitForFunction(()=>window.renderMarkdown);
  const result = await page.evaluate(async({fixtures,rendered})=>{
    const runtime = await import('/flowtoken.js');
    const {parityChecks} = await import('/parity.js');
    const {runtimeChecks} = await import('/runtime.js');
    return {
      parity:await parityChecks(runtime,fixtures,rendered),
      regressions:await runtimeChecks(runtime,rendered.cases),
    };
  },{fixtures,rendered});
  assert.deepEqual(errors,[]);
  const png=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/l9sAAAAASUVORK5CYII=','base64');
  let finishImage;
  await page.route('**/delayed.png',async route=>{
    await new Promise(resolve=>{finishImage=resolve;});
    await route.fulfill({contentType:'image/png',body:png});
  });
  await page.evaluate(async html=>{
    const {mount}=await import('/flowtoken.js');
    const host=document.createElement('div');host.id='image-test';host.innerHTML=html;document.body.append(host);
    window.imageRenderer=mount(host.firstElementChild,{interval:0});
  },rendered.cases.image);
  await page.waitForFunction(()=>document.querySelector('#image-test img')?.dataset.ftState==='pending');
  assert.equal(await page.locator('#image-test img').evaluate(img=>getComputedStyle(img).opacity),'0');
  assert.equal(await page.locator('#image-test img').evaluate(img=>getComputedStyle(img).height),'112px');
  while(!finishImage) await new Promise(resolve=>setTimeout(resolve,10));
  finishImage();
  await page.waitForFunction(()=>document.querySelector('#image-test img')?.dataset.ftState==='loaded');
  const retained=await page.evaluate(async html=>{
    const image=document.querySelector('#image-test img');
    imageRenderer.setRenderedHTML(html);await imageRenderer.whenIdle();
    return image===document.querySelector('#image-test img') && image.dataset.ftState==='loaded';
  },rendered.cases.imageAfter);
  assert(retained,'loaded image retained across append');
  await page.unroute('**/delayed.png');
  await page.route('**/delayed.png',route=>route.fulfill({contentType:'image/png',body:png}));
  await page.evaluate(async html=>{
    const {mountAll}=await import('/flowtoken.js');
    const host=document.createElement('div');host.innerHTML=html;host.id='standalone';document.body.append(host);
    mountAll(host.firstElementChild);
  },rendered.cases.standaloneImage);
  await page.waitForFunction(()=>document.querySelector('#standalone img').dataset.ftState==='loaded');
  await page.evaluate(async html=>{
    const {mount}=await import('/flowtoken.js');
    const host=document.createElement('div');host.innerHTML=html.replace('/delayed.png','/missing.png');host.id='missing';document.body.append(host);
    mount(host.firstElementChild);
  },rendered.cases.standaloneImage);
  await page.waitForFunction(()=>document.querySelector('#missing img').dataset.ftState==='error');
  assert.equal(await page.locator('#missing img').evaluate(img=>getComputedStyle(img).opacity),'1');
  const initialPage=await browser.newPage();
  await initialPage.route('**/initial',route=>route.fulfill({contentType:'text/html',body:`<!doctype html><link rel="stylesheet" href="/flowtoken.css">${rendered.cases.initial}<script type="module" src="/flowtoken.js"></script>`}));
  await initialPage.goto(`http://127.0.0.1:${server.address().port}/initial`);
  await initialPage.waitForFunction(()=>document.querySelector('.ft-token'));
  assert.equal(await initialPage.locator('.ft-token').first().evaluate(el=>getComputedStyle(el).animationName),'ft-fadeIn');
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({result:'passed',...result,imageChecks:7,autoMountChecks:1,upstream:'flowtoken@1.0.40'}));
} finally {await browser.close();await new Promise(resolve=>server.close(resolve));}
