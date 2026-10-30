import {animate, tokenize} from './settings.js';

export class TextRenderer {
  constructor(element, options, notify = () => {}) {
    this.element = element;
    this.options = options;
    this.notify = notify;
    this.target = '';
    this.parts = [];
    this.nodes = [];
    this.frame = null;
    this.lastPaint = 0;
    this.disposed = false;
    this.waiters = [];
  }

  seed(text, animated=true) {
    if(animated){this.setText(text);return;}
    this.target=text;this.parts=tokenize(text,this.options.sep);this.flush(false);
  }

  configure(options) {
    const separatorChanged = this.options.sep !== options.sep;
    this.options = options;
    if (separatorChanged) {
      this.parts = tokenize(this.target, options.sep);
      this.nodes = [];
      this.element.replaceChildren();
      this.flush(false);
    }
    if (options.reducedMotion || !options.animation || options.animation === 'none') {
      for (const node of this.element.querySelectorAll('.ft-token')) node.style.animationName = 'none';
    }
    if (this.immediate) this.flush();
  }

  get immediate() {
    return this.options.reducedMotion || !this.options.animation || this.options.animation === 'none' || this.options.interval === 0;
  }

  setText(text) {
    this.check(text);
    if (text === this.target) return;
    if (text.startsWith(this.target)) {this.append(text.slice(this.target.length)); return;}
    const parts = tokenize(text, this.options.sep);
    this.notify('before-render');
    let common = 0;
    while (common < this.nodes.length && common < parts.length && this.nodes[common].textContent === parts[common]) common++;
    for (const node of this.nodes.splice(common)) node.remove();
    this.target = text;
    this.parts = parts;
    this.notify('render');
    this.start();
  }

  append(delta) {
    this.check(delta);
    if (!delta) return;
    this.notify('before-render');
    this.target += delta;
    if (this.options.sep === 'diff') {
      this.parts.push(delta);
    } else {
      const index = Math.max(0, this.parts.length - 1);
      const tail = (this.parts[index] || '') + delta;
      const next = tokenize(tail, this.options.sep);
      this.parts.length = index;
      for (const part of next) this.parts.push(part);
      if (index < this.nodes.length) {
        const node = this.nodes[index];
        if (next[0] && next[0].startsWith(node.textContent) && this.isWhitespace(next[0]) === this.isWhitespace(node.textContent)) {
          node.textContent = next[0];
          for (const extra of this.nodes.splice(index + 1)) extra.remove();
        } else {
          for (const extra of this.nodes.splice(index)) extra.remove();
        }
      }
    }
    this.notify('render');
    this.start();
  }

  check(text) {
    if (this.disposed) throw new Error('FlowToken has been destroyed');
    if (typeof text !== 'string') throw new TypeError('Expected text');
  }

  isWhitespace(text) {return /^\s+$/u.test(text);}

  makeNode(text, animated) {
    if (this.isWhitespace(text)) return document.createTextNode(text);
    if (this.options.sep !== 'diff') {
      const node = document.createElement('span');
      node.className = 'ft-token';
      node.textContent = text;
      if (animated) animate(node, this.options);
      return node;
    }
    const chunk = document.createElement('span');
    chunk.className = 'ft-chunk';
    chunk.dataset.ftChunk = '';
    for (const word of tokenize(text, 'word')) {
      if (this.isWhitespace(word)) chunk.append(document.createTextNode(word));
      else {
        const node = document.createElement('span');
        node.className = 'ft-token';
        node.textContent = word;
        if (animated) animate(node, this.options);
        chunk.append(node);
      }
    }
    return chunk;
  }

  reveal(animated) {
    this.notify('before-render');
    let visible = false;
    while (this.nodes.length < this.parts.length) {
      const text = this.parts[this.nodes.length];
      if (visible && !this.isWhitespace(text)) break;
      const node = this.makeNode(text, animated);
      this.element.append(node);
      this.nodes.push(node);
      if (!this.isWhitespace(text)) visible = true;
    }
    this.notify('render');
  }

  start() {
    if (this.immediate) {this.flush(!this.options.reducedMotion); return;}
    if (this.frame !== null) return;
    if (this.nodes.length === this.parts.length) {this.complete(); return;}
    this.frame = requestAnimationFrame(now => {
      this.frame = null;
      if (this.disposed) return;
      if (!this.lastPaint || now - this.lastPaint >= this.options.interval) {
        this.reveal(true);
        this.lastPaint = now;
      }
      this.start();
    });
  }

  flush(animated = false) {
    if (this.frame !== null) cancelAnimationFrame(this.frame);
    this.frame = null;
    while (!this.disposed && this.nodes.length < this.parts.length) this.reveal(animated);
    this.complete();
  }

  complete() {
    for (const resolve of this.waiters.splice(0)) resolve();
    this.notify('idle');
  }

  whenIdle() {
    if (this.disposed || this.nodes.length === this.parts.length) return Promise.resolve();
    return new Promise(resolve => this.waiters.push(resolve));
  }

  destroy() {
    if (this.frame !== null) cancelAnimationFrame(this.frame);
    this.frame = null;
    this.disposed = true;
    this.complete();
  }
}
