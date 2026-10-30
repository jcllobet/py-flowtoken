export const animations = Object.fromEntries(['fadeIn','slideUp','wave','elastic','bounceIn','rotateIn','colorTransition','fadeAndScale','slideInFromLeft','blurIn','typewriter','highlight','blurAndSharpen','dropIn'].map(name => [name, `ft-${name}`]));

export function tokenize(text, sep = 'word') {
  if (sep === 'word') return text.split(/(\s+)/u).filter(Boolean);
  if (sep === 'char') return Array.from(text);
  if (sep === 'diff') return text ? [text] : [];
  throw new Error('sep must be "word", "char", or "diff"');
}

function settings(element, options) {
  const value = {
    sep: element.dataset.sep || 'word',
    animation: element.dataset.animation || 'fadeIn',
    duration: element.dataset.duration || '0.25s',
    easing: element.dataset.easing || 'ease-out',
    interval: Number(element.dataset.interval ?? 35),
    reducedMotion: matchMedia('(prefers-reduced-motion: reduce)').matches,
    ...options,
  };
  tokenize('', value.sep);
  if (!Number.isFinite(value.interval) || value.interval < 0 || value.interval > 1000) throw new Error('Invalid interval');
  if (value.animation !== null && !/^[\w-]+$/.test(value.animation)) throw new Error('Invalid animation');
  return value;
}

export class FlowToken {
  constructor(element, options = {}) {
    this.element = element;
    this.options = settings(element, options);
    this.text = '';
    this.parts = [];
    this.nodes = [];
    this.frame = null;
    this.lastPaint = 0;
    this.disposed = false;
    this.waiters = [];
    const initial = element.textContent || '';
    element.replaceChildren();
    this.setText(initial);
    if (!options.animateInitial) this.flush();
  }

  setText(text) {
    if (this.disposed) throw new Error('FlowToken has been destroyed');
    if (typeof text !== 'string') throw new TypeError('Expected text');
    if (text === this.text) return;
    const previous = this.text;
    this.text = text;
    const next = this.options.sep === 'diff'
      ? text.startsWith(previous) ? [...this.parts, ...(text.length > previous.length ? [text.slice(previous.length)] : [])] : tokenize(text, 'diff')
      : tokenize(text, this.options.sep);
    this.element.dispatchEvent(new Event('flowtoken:before-render'));
    let common = 0;
    while (common < this.nodes.length && common < next.length && this.nodes[common].textContent === next[common]) common++;
    if (common < this.nodes.length && common < next.length && next[common].startsWith(this.nodes[common].textContent) && !/^\s*$/u.test(next[common])) {
      this.nodes[common].textContent = next[common];
      common++;
    }
    for (const node of this.nodes.splice(common)) node.remove();
    this.parts = next;
    this.element.setAttribute('aria-busy', String(this.nodes.length < next.length));
    this.element.dispatchEvent(new Event('flowtoken:render'));
    if (this.options.reducedMotion || !this.options.animation || this.options.animation === 'none' || this.options.interval === 0) this.flush();
    else this.schedule();
  }

  append(delta) { this.setText(this.text + delta); }

  schedule() {
    if (this.frame !== null || this.disposed) return;
    if (this.nodes.length >= this.parts.length) { this.complete(); return; }
    this.frame = requestAnimationFrame(now => {
      this.frame = null;
      if (!this.lastPaint || now - this.lastPaint >= this.options.interval) {
        this.reveal();
        this.lastPaint = now;
      }
      this.schedule();
    });
  }

  reveal(animate = true) {
    this.element.dispatchEvent(new Event('flowtoken:before-render'));
    let wordShown = false;
    while (this.nodes.length < this.parts.length) {
      const text = this.parts[this.nodes.length];
      const whitespace = /^\s+$/u.test(text);
      if (wordShown && !whitespace) break;
      const node = document.createElement('span');
      node.className = 'ft-token';
      node.textContent = text;
      if (animate && !whitespace && !this.options.reducedMotion) {
        node.style.animationName = animations[this.options.animation] || this.options.animation || 'none';
        node.style.animationDuration = this.options.duration;
        node.style.animationTimingFunction = this.options.easing;
        node.style.animationIterationCount = '1';
        node.style.animationFillMode = 'both';
        node.addEventListener('animationend', () => { node.style.animationName = 'none'; }, {once:true});
      }
      this.element.append(node);
      this.nodes.push(node);
      if (!whitespace) wordShown = true;
    }
    this.element.dispatchEvent(new Event('flowtoken:render'));
  }

  flush() {
    if (this.frame !== null) cancelAnimationFrame(this.frame);
    this.frame = null;
    while (this.nodes.length < this.parts.length) this.reveal(false);
    this.complete();
  }

  complete() {
    this.element.setAttribute('aria-busy', 'false');
    for (const resolve of this.waiters.splice(0)) resolve();
    this.element.dispatchEvent(new Event('flowtoken:idle'));
  }

  whenIdle() {
    if (this.nodes.length === this.parts.length) return Promise.resolve();
    return new Promise(resolve => this.waiters.push(resolve));
  }

  destroy() {
    if (this.frame !== null) cancelAnimationFrame(this.frame);
    this.frame = null;
    this.disposed = true;
    for (const resolve of this.waiters.splice(0)) resolve();
  }
}

export class FlowMarkdown {
  constructor(element, options = {}) {
    this.element = element;
    this.options = settings(element, options);
    this.tokens = [...element.querySelectorAll('[data-ft-token]')].map(node => node.textContent);
  }

  setRenderedHTML(html) {
    const parsed = new DOMParser().parseFromString(html, 'text/html');
    const source = parsed.querySelector('[data-flowtoken="markdown"]');
    if (!source) throw new Error('Expected AnimatedMarkdown.render() output');
    const allowed = new Set(['DIV','P','SPAN','H1','H2','H3','H4','H5','H6','STRONG','EM','S','DEL','BLOCKQUOTE','UL','OL','LI','A','IMG','PRE','CODE','HR','BR','TABLE','THEAD','TBODY','TR','TH','TD','INPUT']);
    for (const node of [...source.querySelectorAll('*')]) {
      if (!allowed.has(node.tagName)) { node.replaceWith(document.createTextNode(node.textContent)); continue; }
      for (const attribute of [...node.attributes]) {
        if (!['class','data-ft-token','href','src','alt','title','start','type','checked','disabled'].includes(attribute.name)) node.removeAttribute(attribute.name);
        if (['href','src'].includes(attribute.name) && !['http:','https:','mailto:'].includes(new URL(attribute.value, 'https://flowtoken.invalid/').protocol)) node.removeAttribute(attribute.name);
      }
      if (node.tagName === 'INPUT') { node.type = 'checkbox'; node.disabled = true; }
    }
    let common = 0;
    const next = [...source.querySelectorAll('[data-ft-token]')];
    while (common < next.length && common < this.tokens.length && next[common].textContent === this.tokens[common]) common++;
    next.forEach((node,index) => {
      if (index >= common && !this.options.reducedMotion && this.options.animation) {
        node.style.animation = `${animations[this.options.animation] || this.options.animation} ${this.options.duration} ${this.options.easing} ${(index-common)*this.options.interval}ms both`;
      }
    });
    this.element.dispatchEvent(new Event('flowtoken:before-render'));
    this.element.replaceChildren(...source.childNodes);
    this.tokens = next.map(node => node.textContent);
    this.element.dispatchEvent(new Event('flowtoken:render'));
  }
}

const mounted = new WeakMap();
export function mount(element, options = {}) {
  if (!mounted.has(element)) mounted.set(element, element.dataset.flowtoken === 'markdown' ? new FlowMarkdown(element, options) : new FlowToken(element, options));
  return mounted.get(element);
}
export function mountAll(root = document) {
  for (const element of root.querySelectorAll('[data-flowtoken]')) mount(element);
}
if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => mountAll(), {once:true});
  else mountAll();
}
