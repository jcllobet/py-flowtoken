export {animations,tokenize} from './settings.js';
export {FlowToken,FlowMarkdown,FlowImage} from './renderers.js';
import {FlowToken,FlowMarkdown,FlowImage} from './renderers.js';

const mounted=new WeakMap();
export function mount(element, options={}) {
  if(!mounted.has(element)) {
    const renderer=element.hasAttribute('data-ft-image')?new FlowImage(element,options):element.dataset.flowtoken==='markdown'?new FlowMarkdown(element,options):new FlowToken(element,options);
    mounted.set(element,renderer);
    element.addEventListener('flowtoken:destroy',()=>{if(mounted.get(element)===renderer)mounted.delete(element);},{once:true});
  }
  return mounted.get(element);
}
export function unmount(element) {
  const renderer=mounted.get(element);
  mounted.delete(element);
  renderer?.destroy();
}
export function mountAll(root=document) {
  if(root.matches?.('[data-flowtoken], [data-ft-image]'))mount(root);
  for(const element of root.querySelectorAll('[data-flowtoken], [data-ft-image]')) {
    if(element.hasAttribute('data-ft-image') && element.closest('[data-flowtoken="markdown"]'))continue;
    mount(element);
  }
}
if(typeof document!=='undefined') {
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>mountAll(),{once:true});
  else mountAll();
  document.addEventListener('htmx:afterSwap',event=>mountAll(event.detail?.target||event.target));
}
