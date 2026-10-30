import {schema} from './settings.js';

export function safeURL(value) {
  try {
    value = value.trim();
    if (/[\u0000-\u0020\u007f]/u.test(value)) return null;
    const parsed = new URL(value, 'https://flowtoken.invalid/');
    return schema.protocols.includes(parsed.protocol.slice(0, -1)) ? value : null;
  } catch {return null;}
}

export function safeStyle(value) {
  return value.split(';').flatMap(declaration => {
    const index = declaration.indexOf(':');
    if (index < 0) return [];
    const name = declaration.slice(0, index).trim().toLowerCase();
    const content = declaration.slice(index + 1).trim();
    if (!schema.styles.includes(name) || /url|expression|javascript/i.test(content) || !/^[\w\s#.,()%/-]+$/.test(content)) return [];
    return [`${name}:${content}`];
  }).join(';');
}

export function parseHTML(html) {
  const document = new DOMParser().parseFromString(html, 'text/html');
  const source = document.querySelector('[data-flowtoken="markdown"]');
  if (!source) throw new Error('Expected AnimatedMarkdown.render() output');
  for (const node of [...source.querySelectorAll('*')]) {
    if (node.classList.contains('ft-token') || node.hasAttribute('data-ft-token')) {
      node.replaceWith(document.createTextNode(node.textContent));
      continue;
    }
    if (!schema.tags.includes(node.tagName.toLowerCase())) {
      node.replaceWith(document.createTextNode(node.textContent));
      continue;
    }
    for (const attr of [...node.attributes]) {
      if (attr.name === 'style') {
        const style = safeStyle(attr.value);
        if (style) node.setAttribute('style', style); else node.removeAttribute('style');
      } else if (!schema.attributes.includes(attr.name)) node.removeAttribute(attr.name);
      else if (['href','src'].includes(attr.name) && safeURL(attr.value) === null) node.removeAttribute(attr.name);
    }
    if (node.tagName === 'INPUT') {node.type = 'checkbox'; node.disabled = true;}
    if (node.tagName === 'BUTTON') node.type = 'button';
    if (node.tagName === 'A' && node.target === '_blank') node.rel = 'noopener noreferrer';
  }
  source.normalize();
  return source;
}

function key(node) {
  if (node.nodeType !== Node.ELEMENT_NODE) return null;
  return node.getAttribute('data-ft-key') || node.id || (node.tagName === 'IMG' ? `image:${node.getAttribute('src')}` : null);
}

function matches(current, desired, leaves) {
  if (desired.nodeType === Node.TEXT_NODE) return leaves.has(current);
  return !leaves.has(current) && current?.nodeType === desired.nodeType && current.nodeName === desired.nodeName && key(current) === key(desired);
}

export function reconcile(parent, desiredParent, owner) {
  let cursor = parent.firstChild;
  for (const desired of [...desiredParent.childNodes]) {
    let current = cursor;
    const identity = key(desired);
    if (identity && !matches(current, desired, owner.leaves)) {
      current = [...parent.childNodes].find(node => key(node) === identity && matches(node, desired, owner.leaves)) || cursor;
    }
    if (current && matches(current, desired, owner.leaves)) {
      if (current !== cursor) parent.insertBefore(current, cursor);
      if (desired.nodeType === Node.TEXT_NODE) owner.leaves.get(current).setText(desired.textContent);
      else {
        owner.attributes(current, desired);
        if (!current.hasAttribute('data-ft-copy')) reconcile(current, desired, owner);
        owner.behaviors.bind(current);
      }
      cursor = current.nextSibling;
    } else {
      const fresh = owner.hydrate(desired);
      parent.insertBefore(fresh, cursor);
    }
  }
  while (cursor) {
    const next = cursor.nextSibling;
    owner.remove(cursor);
    cursor.remove();
    cursor = next;
  }
}
