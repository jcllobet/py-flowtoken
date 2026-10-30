import React from 'react';
import { createRoot } from 'react-dom/client';
import { flushSync } from 'react-dom';
import SplitTextImport from 'flowtoken/dist/components/SplitText.js';
import { AnimatedMarkdown } from 'flowtoken';
import animationsImport from 'flowtoken/dist/utils/animations.js';
const SplitText = SplitTextImport.default || SplitTextImport;
const roots = new WeakMap();
window.upstreamAnimations = animationsImport.animations;
window.renderUpstream = (element, content, sep, markdown = false) => {
  if (!roots.has(element)) roots.set(element, createRoot(element));
  flushSync(() => roots.get(element).render(React.createElement(markdown ? AnimatedMarkdown : SplitText,
    markdown ? {content, sep, animation:'fadeIn'} : {input:content, sep, animation:'ft-fadeIn', animationDuration:'0.25s', animationTimingFunction:'ease-out', animationIterationCount:1})));
};
