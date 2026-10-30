import { chromium } from '@playwright/test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { createServer } from 'node:net';
import { once } from 'node:events';
import { resolve } from 'node:path';

const python=process.env.PYTHON||'.venv/bin/python';
const browser=await chromium.launch({channel:process.env.CI?undefined:'chrome',headless:true});
const variants=[
  {name:'FastHTML', command:port=>['-m','uvicorn','examples.fasthtml_chat:app','--host','127.0.0.1','--port',String(port),'--no-access-log'],expected:'Python sends chunks. The browser reveals their words smoothly, without repeating the text already on screen.'},
  {name:'Flask',command:port=>['-m','flask','--app','examples.flask_chat','run','--host','127.0.0.1','--port',String(port),'--no-debugger','--no-reload'],expected:'Flask sends chunks. The browser reveals their words smoothly.'},
  {name:'Django',command:port=>['examples/django_demo/manage.py','runserver',`127.0.0.1:${port}`,'--noreload'],expected:'Django sends chunks. The browser reveals their words smoothly.'},
];
try {
 for(const variant of variants) {
  const reservation=createServer();reservation.listen(0,'127.0.0.1');await once(reservation,'listening');
  const port=reservation.address().port;await new Promise(resolve=>reservation.close(resolve));
  const child=spawn(python,variant.command(port),{env:{...process.env,PYTHONPATH:resolve('src'),PYTHONUNBUFFERED:'1'},stdio:['ignore','pipe','pipe']});
  let output='';child.stdout.on('data',data=>output+=data);child.stderr.on('data',data=>output+=data);
  const origin=`http://127.0.0.1:${port}`;
  try {
   let ready=false;
   for(let attempt=0;attempt<100;attempt++) {
    if(child.exitCode!==null)throw new Error(output);
    try {const response=await fetch(origin,{headers:{'User-Agent':'OpenAI File Downloader, XaiImageApiFetch/1.0'}});if(response.ok){ready=true;break;}}catch{}
    await new Promise(resolve=>setTimeout(resolve,100));
   }
   assert(ready,variant.name+' did not start: '+output);
   const page=await browser.newPage({extraHTTPHeaders:{'User-Agent':'OpenAI File Downloader, XaiImageApiFetch/1.0'}});
   const errors=[];page.on('pageerror',error=>errors.push(error.message));
   await page.goto(origin);
   assert.notEqual(await page.locator('#answer').innerText(),variant.expected);
   await page.waitForFunction(expected=>document.getElementById('answer')?.textContent===expected,variant.expected);
   await page.waitForFunction(()=>document.getElementById('answer')?.getAttribute('aria-busy')==='false');
   assert(await page.locator('#answer .ft-token').count()>5);
   const script=await page.request.get(origin+'/flowtoken/flowtoken.js');
   const css=await page.request.get(origin+'/flowtoken/flowtoken.css');
   assert(script.ok()&&css.ok());
   assert(script.headers()['content-type'].includes('javascript'));
   assert(css.headers()['content-type'].includes('text/css'));
   assert.equal((await page.request.get(origin+'/flowtoken/core.py')).status(),404);
   assert.deepEqual(errors,[]);
   await page.close();
   console.log(JSON.stringify({framework:variant.name,result:'passed',checks:['real HTTP assets','template rendering','live SSE','progressive word rendering','invalid asset isolation']}));
  } finally {
   if(child.exitCode===null){child.kill('SIGTERM');await once(child,'exit');}
  }
 }
} finally {await browser.close();}
