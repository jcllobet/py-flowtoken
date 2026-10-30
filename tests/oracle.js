import React from 'react';
import { createRoot } from 'react-dom/client';
import { flushSync } from 'react-dom';
import { AnimatedMarkdown } from 'flowtoken';
import animationsImport from 'flowtoken/dist/utils/animations.js';
const roots = new WeakMap();
window.upstreamAnimations = animationsImport.animations;
window.renderMarkdown = (element, props) => {
  if (!roots.has(element)) roots.set(element, createRoot(element));
  flushSync(() => roots.get(element).render(React.createElement(AnimatedMarkdown,props)));
};
window.renderCustom = element => window.renderMarkdown(element,{content:'<badge>Hello</badge>',customComponents:{badge:({children})=>React.createElement('mark',null,children)}});
