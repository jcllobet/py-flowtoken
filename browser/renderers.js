import {settings, schema} from './settings.js';
import {TextRenderer} from './text.js';
import {parseHTML,reconcile} from './dom.js';
import {Behaviors} from './behaviors.js';

class Renderer {
  constructor(element, options) {
    this.element=element;
    this.overrides={...options};
    this.options=settings(element,options);
    this.disposed=false;
  }

  event(name) {
    if (name==='before-render') this.element.setAttribute('aria-busy','true');
    if (name==='idle') this.element.setAttribute('aria-busy','false');
    this.element.dispatchEvent(new Event(`flowtoken:${name}`));
  }

  check() {if(this.disposed) throw new Error('FlowToken has been destroyed');}

  configure(options) {
    this.check();
    const overrides={...this.overrides,...options};
    const next=settings(this.element,overrides);
    this.overrides=overrides;this.options=next;
  }

  finishDestroy() {
    this.disposed=true;
    this.element.setAttribute('aria-busy','false');
    this.element.dispatchEvent(new Event('flowtoken:destroy'));
  }
}

export class FlowToken extends Renderer {
  constructor(element, options={}) {
    super(element, options);
    const initial=element.textContent || '';
    element.replaceChildren();
    this.renderer=new TextRenderer(element,this.options,name=>this.event(name));
    this.renderer.seed(initial,this.options.animateInitial);
  }

  get text() {return this.renderer.target;}
  setText(text) {this.check();this.renderer.setText(text);}
  append(delta) {this.check();this.renderer.append(delta);}
  flush() {this.check();this.renderer.flush();}
  whenIdle() {return this.renderer.whenIdle();}
  configure(options) {
    super.configure(options);this.renderer.configure(this.options);
  }
  destroy() {if(!this.disposed){this.renderer.destroy();this.finishDestroy();}}
}

export class FlowMarkdown extends Renderer {
  constructor(element, options={}) {
    super(element,options);
    this.leaves=new Map();
    this.behaviors=new Behaviors(this.options);
    const children=[...element.childNodes];
    element.replaceChildren(...children.map(child=>this.hydrate(child)));
    this.settle();
  }

  hydrate(node) {
    if (node.nodeType===Node.TEXT_NODE) {
      const leaf=document.createElement('span');leaf.className='ft-leaf';
      const renderer=new TextRenderer(leaf,this.options,name=>{if(name!=='idle')this.event(name);else this.settle();});
      this.leaves.set(leaf,renderer);
      renderer.seed(node.textContent,this.options.animateInitial);
      return leaf;
    }
    if (node.nodeType!==Node.ELEMENT_NODE) return node.cloneNode();
    const element=node.cloneNode(false);
    if (node.hasAttribute('data-ft-copy')) element.textContent=node.textContent;
    else for(const child of node.childNodes) element.append(this.hydrate(child));
    this.behaviors.bind(element);
    return element;
  }

  attributes(current, desired) {
    for(const attr of [...current.attributes]) {
      if(attr.name!=='style'&&attr.name!=='data-ft-state'&&!desired.hasAttribute(attr.name)) current.removeAttribute(attr.name);
    }
    for(const attr of desired.attributes) {
      if(attr.name!=='style'&&current.getAttribute(attr.name)!==attr.value) current.setAttribute(attr.name,attr.value);
    }
    for(const property of schema.styles) {
      const value=desired.style.getPropertyValue(property);
      if(value) current.style.setProperty(property,value);
      else current.style.removeProperty(property);
    }
  }

  remove(node) {
    const elements=[node,...(node.querySelectorAll?.('.ft-leaf')||[])];
    for(const element of elements) {
      const renderer=this.leaves.get(element);
      if(renderer){renderer.destroy();this.leaves.delete(element);}
    }
    this.behaviors.releaseTree(node);
  }

  setRenderedHTML(html) {
    this.check();
    const source=parseHTML(html);
    this.options=settings(source,this.overrides);
    this.behaviors.options=this.options;
    for(const renderer of this.leaves.values()) renderer.configure(this.options);
    this.event('before-render');
    reconcile(this.element,source,this);
    this.event('render');
    this.settle();
  }

  settle() {
    if(this.leaves&&[...this.leaves.values()].every(renderer=>renderer.nodes.length===renderer.parts.length)) this.event('idle');
  }

  whenIdle() {return Promise.all([...this.leaves.values()].map(renderer=>renderer.whenIdle()));}
  flush() {this.check();for(const renderer of this.leaves.values())renderer.flush();this.settle();}
  configure(options) {
    super.configure(options);
    this.behaviors.options=this.options;for(const renderer of this.leaves.values())renderer.configure(this.options);
  }
  destroy() {
    if(this.disposed)return;
    for(const renderer of this.leaves.values())renderer.destroy();
    this.leaves.clear();this.behaviors.destroy();this.finishDestroy();
  }
}

export class FlowImage extends Renderer {
  constructor(element, options={}) {
    super(element,options);this.behaviors=new Behaviors(this.options);this.behaviors.bind(element);
  }
  configure(options){super.configure(options);this.behaviors.options=this.options;}
  destroy(){if(!this.disposed){this.behaviors.destroy();this.finishDestroy();}}
}
