import {animate, settings} from './settings.js';

export class Behaviors {
  constructor(options) {this.options = options; this.bound = new Map();}

  bind(element) {
    if (element.hasAttribute('data-ft-copy')) this.copy(element);
    if (element.tagName === 'IMG') this.image(element);
  }

  copy(button) {
    if (this.bound.has(button)) return;
    const state = {controller:new AbortController(),timer:null};
    this.bound.set(button, state);
    button.addEventListener('click', async () => {
      const block = button.closest('[data-ft-code]');
      try {
        await navigator.clipboard.writeText(block?.dataset.ftSource ?? block?.querySelector('code')?.textContent ?? '');
        if (state.controller.signal.aborted) return;
        button.textContent = 'Copied!';button.setAttribute('aria-label','Copied!');
      } catch {
        if (state.controller.signal.aborted) return;
        button.textContent = 'Copy failed';button.setAttribute('aria-label','Copy failed; try again');
      }
      clearTimeout(state.timer);
      state.timer = setTimeout(() => {button.textContent='Copy code';button.setAttribute('aria-label','Copy code');},2000);
    }, {signal:state.controller.signal});
  }

  image(image) {
    const source = image.getAttribute('src');
    const old = this.bound.get(image);
    if (old?.source === source) return;
    this.release(image);
    const state = {source,controller:new AbortController()};
    this.bound.set(image,state);
    image.dataset.ftState = 'pending';
    const loaded = () => {image.dataset.ftState='loaded';animate(image,settings(image,this.options));};
    const failed = () => {image.dataset.ftState='error';image.style.animationName='none';};
    image.addEventListener('load', loaded, {once:true,signal:state.controller.signal});
    image.addEventListener('error', failed, {once:true,signal:state.controller.signal});
    if (image.complete) {
      if (image.naturalWidth) loaded();
      else failed();
    }
  }

  release(element) {
    const state = this.bound.get(element);
    if (state) {state.controller.abort();clearTimeout(state.timer);this.bound.delete(element);}
  }

  releaseTree(element) {
    this.release(element);
    for (const child of element.querySelectorAll?.('*') || []) this.release(child);
  }

  destroy() {
    for (const element of [...this.bound.keys()]) this.release(element);
  }
}
