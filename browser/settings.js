import schema from '../src/py_flowtoken/schema.json';

export const animations = Object.fromEntries(schema.animations.map(name => [name, `ft-${name}`]));
export {schema};

export function tokenize(text, sep = 'word') {
  if (sep === 'word') return text.split(/(\s+)/u).filter(Boolean);
  if (sep === 'char') return Array.from(text);
  if (sep === 'diff') return text ? [text] : [];
  throw new Error('Invalid separator');
}

export function settings(element, overrides = {}) {
  const data = element.dataset;
  const result = {...schema.defaults,
    sep: data.sep ?? schema.defaults.sep,
    animation: data.animation ?? schema.defaults.animation,
    duration: data.duration ?? schema.defaults.duration,
    easing: data.easing ?? schema.defaults.easing,
    interval: Number(data.interval ?? schema.defaults.interval),
    animateInitial: data.animateInitial !== 'false',
    reducedMotion: matchMedia('(prefers-reduced-motion: reduce)').matches,
    ...overrides};
  if (!schema.separators.includes(result.sep)) throw new Error('Invalid separator');
  if (!Number.isFinite(result.interval) || result.interval < 0 || result.interval > 1000) throw new Error('Invalid interval');
  if (typeof result.animateInitial !== 'boolean') throw new Error('Invalid animateInitial');
  if (result.animation !== null && !/^[a-zA-Z_][\w-]*$/.test(result.animation)) throw new Error('Invalid animation');
  if (!/^(?:\d+(?:\.\d+)?|\.\d+)(?:ms|s)$/.test(result.duration)) throw new Error('Invalid duration');
  if (!CSS.supports('animation-timing-function', result.easing)) throw new Error('Invalid easing');
  return result;
}

export function animate(node, options) {
  if (options.reducedMotion || !options.animation || options.animation === 'none') return;
  node.style.animationName = animations[options.animation] || options.animation;
  node.style.animationDuration = options.duration;
  node.style.animationTimingFunction = options.easing;
  node.style.animationIterationCount = '1';
  node.style.animationFillMode = 'both';
  node.addEventListener('animationend', () => {node.style.animationName = 'none';}, {once:true});
}
