# Thermo-nuclear review: py-flowtoken v0.2.0

Review date: 2026-10-30. Reviewed source: [`0eb1cd0`](https://github.com/jcllobet/py-flowtoken/tree/0eb1cd0465ce10b190f3b0477519c78e9c104565), including the framework-adapter changes since v0.1.1 and the complete renderer. Reference: the published [`flowtoken@1.0.40`](https://www.npmjs.com/package/flowtoken/v/1.0.40), still the npm latest version when checked.

**Verdict: changes requested.** The adapters are useful and tested. The renderer does not yet meet functional parity with the npm package. Its main design problem is competing ownership of tokenization, rendering, and animation state between Python and JavaScript. Adding more feature branches to the current Markdown update loop would make that problem worse.

The framework changes were already committed, pushed, and tagged v0.2.0 before this review. This report records findings and a proposed implementation sequence; it does not silently change the implementation under review.

## Verification and limits

- `python -m pytest -q`: 38 tests passed.
- `npm test`: 53 browser/parity checks passed; live FastHTML, Flask, and Django examples passed.
- Additional Chrome probes reproduced the defects below despite that green baseline.
- The npm registry and installed package agree on version 1.0.40. The lockfile pins the reference package's integrity.
- No production source file crosses 1,000 lines. More file splitting is not the immediate need. The framework-independent core and optional adapter imports are worth retaining.

## Findings

### F1 — P1: Markdown's default diff mode does not preserve an appended suffix

Evidence: [Python token wrapping](../../src/py_flowtoken/rendering.py#L11), [Markdown rendering](../../src/py_flowtoken/rendering.py#L38), [browser reconciliation](../../src/py_flowtoken/static/py_flowtoken/flowtoken.js#L133).

The Python renderer produces one token for each text node in `sep='diff'` mode. Every later render starts from scratch. The browser only compares the full text of those tokens; it has no model of the append that happened inside a token.

Reproduction: render `Hello`, then update to `Hello world`, with default `AnimatedMarkdown` options.

| Implementation | Resulting text-token spans |
| --- | --- |
| npm public `AnimatedMarkdown` | `['Hello', ' world']` |
| Python renderer + `FlowMarkdown` | `['Hello world']` |

The port reanimates the whole paragraph instead of retaining the old text and animating the suffix. This is the default mode of the public npm component, not an obscure option.

The same update loop replaces every DOM descendant with `replaceChildren`. A probe updating `**Hello** world` to `**Hello** world again` confirmed that the unchanged first token was disconnected and replaced. Matching token strings merely suppress some new animation; it does not preserve node identity, selection, code scroll position, image state, or component state.

**Required change:** one browser-owned snapshot reconciler for both plain text and Markdown text leaves. Preserve stable block/leaf identities, compute suffixes within changed leaves, and keep animation state separate from the document tree. Python should produce semantic HTML and validated component configuration, rather than a competing animated-token tree that JavaScript must reinterpret.

### F2 — P1: The Markdown normalization boundary rejects its own renderer output

Evidence: [URL validation and attribute removal](../../src/py_flowtoken/static/py_flowtoken/flowtoken.js#L140).

Two verified failures share the same ownership problem:

1. `AnimatedMarkdown('[broken](http://[)').render()` produces an anchor with `href='http://%5B'`. Passing that exact output to `FlowMarkdown.setRenderedHTML()` throws `TypeError: Failed to construct 'URL': Invalid URL`. A malformed or intermediate model-generated link can abort a complete chat update.
2. A Markdown table with `:---` and `---:` alignment renders correctly in Python. Updating it through `setRenderedHTML()` strips the generated `text-align` styles. The probe changed left/right headers into centered headers.

The browser sanitizer duplicates decisions already made by the Python renderer, but does not share its schema. It both rejects valid pipeline input and removes semantically necessary attributes.

**Required change:** define the supported semantic HTML boundary once. Validate URLs through a total function that returns a safe URL or no URL; malformed input must not throw out the whole update. Preserve an explicit allowlist of generated presentation properties such as table alignment. Validate the next tree before committing it. Do not patch this with an empty catch around the full update function or permit arbitrary inline CSS.

### F3 — P1: Token wrappers destroy visible newline semantics

Evidence: [inline-block token styling](../../src/py_flowtoken/static/py_flowtoken/flowtoken.css#L3), [Python spans](../../src/py_flowtoken/rendering.py#L11), [browser token creation](../../src/py_flowtoken/static/py_flowtoken/flowtoken.js#L82).

All tokens, including whitespace, become inline-block spans. A newline inside its own inline block is not a line break between surrounding words.

Chrome probes:

- `FlowToken.setText('one\ntwo')` retained the newline in `textContent`, but all three spans had the same vertical position.
- A fenced code block containing `first\nsecond` placed both words on the same visible line.

This matters for readability, code correctness, and copied-versus-displayed content. The current text-content tests cannot detect it.

**Required change:** preserve whitespace as native text nodes or explicit structural breaks, and animate only actual word/character units. Keep code layout in native `pre` semantics. Add rendered-geometry assertions as well as string assertions.

### F4 — P2: Mounting and disposal have contradictory lifecycle contracts

Evidence: [constructor](../../src/py_flowtoken/static/py_flowtoken/flowtoken.js#L27), [destruction](../../src/py_flowtoken/static/py_flowtoken/flowtoken.js#L125), [mount registry](../../src/py_flowtoken/static/py_flowtoken/flowtoken.js#L168).

The constructor removes Python's rendered spans, then calls `flush()` unless the caller explicitly supplies `animateInitial`. Automatic mounting supplies no such option. A server-rendered `AnimatedText` probe went from five active `ft-fadeIn` animations to zero immediately after importing the module. Configuration for its initial animation is discarded by default.

Separately, `destroy()` leaves the renderer in the `mounted` WeakMap. Calling `mount(element)` again returns that destroyed object; the next `setText()` raises `FlowToken has been destroyed`.

**Required change:** give the mount owner responsibility for hydration, animation policy, and disposal. Add an explicit unmount operation that removes registry ownership and cancels pending work. Specify initial-animation behavior in the public configuration rather than implicitly overriding server output. Test repeated mount/unmount cycles and mounting populated elements.

### F5 — P2: The parity suite does not test the main parity risks

Evidence: [oracle imports](../../tests/oracle.js#L1), [comparisons](../../tests/browser.mjs#L32), [semantic projection](../../tests/browser.mjs#L50), [single Markdown update check](../../tests/browser.mjs#L75).

The number 53 is not 53 checks against the public npm API:

- Only eight static Markdown fixtures exercise the npm package's public `AnimatedMarkdown` export.
- Much of the comparison uses the private `SplitText` component, token-name mappings, and plain-text snapshots.
- The remaining checks test port-only behavior.
- The Markdown projection removes **all** whitespace and ignores styles, lifecycle, selection, images, and controls. It would consider `a b` and `ab` equivalent.
- There is no append sequence against the public component in default diff mode, no delayed-image test, and no syntax-highlighting or clipboard test.

That explains how F1–F4 coexist with a green suite. The tests are useful, but their current scope is too narrow to establish functional parity.

**Required change:** make the public npm component the primary oracle. Separate strict contract tests, intentional behavior differences, and port-only features. Test representative update sequences, DOM identity, layout, computed animation properties, image readiness, and code controls. Keep the framework integration tests; they cover a different boundary well.

### F6 — P2: Append work repeatedly copies the accumulated history

Evidence: [Python update and append](../../src/py_flowtoken/streaming.py#L47), [browser append and tokenization](../../src/py_flowtoken/static/py_flowtoken/flowtoken.js#L43).

Python `append()` constructs a full new string, rechecks the old prefix, and copies the complete chunks list. Browser `append()` similarly enters the full-snapshot path, retokenizes the accumulated text, and scans existing DOM nodes. A one-token append is treated like a document replacement.

Local median timings for Python one-character appends, three runs per size:

| Appends | Time |
| --- | ---: |
| 2,000 | 3.44 ms |
| 4,000 | 10.01 ms |
| 8,000 | 35.46 ms |
| 16,000 | 124.57 ms |

These are observations on this machine, not a performance SLA. The list-copying algorithm is quadratic regardless of the absolute times.

**Required change:** separate delta ingestion from snapshot reconciliation. Append to the internal chunk list in place; retokenize only the new suffix and any unfinished boundary word. Full snapshots still need comparison, and producing a full text snapshot still costs proportional to its size. Do not promise constant-time full snapshots.

## Functional parity matrix

The npm entry point exports `AnimatedMarkdown`. Its internal image/code helpers matter because their behavior is visible through that public component. React hooks and private implementation classes are not features a Python port needs to reproduce.

| npm behavior | v0.2.0 status | What is needed |
| --- | --- | --- |
| Plain Markdown text, headings, emphasis, links, lists | Basic static rendering works | Expand streamed/nested cases and preserve layout |
| GFM tables, tasks, strikethrough | Basic cases work | Preserve alignment and layout through updates |
| `sep='word'` and `sep='char'` | Basic token content works | Fix newline layout; verify rendering, not only text |
| Default `sep='diff'` append animation | Incorrect for Markdown updates | F1: retain old leaves and animate only new suffixes |
| `animation` and `null`/disabled animation | Names and basic disable paths exist | Test initial mount, updates, and the disabled transition |
| `animationDuration`, `animationTimingFunction` | Partial Python equivalent | Support the intended CSS value surface; current Python easing accepts only five keywords and rejects `cubic-bezier(...)` |
| Fourteen named animation effects | Names match; keyframes differ | Decide whether visual equivalence is required; compare computed keyframes and timing before claiming it |
| `codeStyle` / syntax highlighting | Missing | Add a syntax-highlighting renderer and a documented theme API |
| Fenced-code copy button and copied feedback | Missing | Add accessible clipboard control, failure handling, and feedback reset |
| `imgHeight` in `AnimatedMarkdown` | Missing | Add a Markdown-specific option; current input raises `TypeError` |
| Image load gating and load-triggered animation | Missing | Keep images hidden until loaded, then start the configured animation; handle failed loads |
| Image dimensions and fit controls | Partial | Add width, fit, and animation options to the Python image component |
| `customComponents` | Missing | Add a trusted Python renderer registry and, where needed, explicit client lifecycle hooks |
| Incomplete custom-component tag suppression | Missing | Buffer recognized partial tags until complete, without hiding unrelated text |
| Raw HTML via `rehype-raw` | Intentionally different | Keep safe defaults; add a clearly bounded trusted/allowlisted mode only if required |
| Links opening a new tab with safe rel attributes | Different default | Make the link policy explicit and test the chosen compatibility profile |
| Unicode code-point handling and corrected prefix matching | Intentional improvements | Preserve them; document differences rather than cloning upstream bugs |
| Extra smooth plain-text pacing, SSE helpers, Python framework adapters | Port additions | Keep separate from npm parity claims |

### Verified missing features

Additional probes confirmed:

- The npm code block renders a `Copy code` control; the port renders none. The port's styled spans are animation wrappers, not syntax-highlighting tokens.
- The npm image accepts `imgHeight='7rem'` and initially has zero opacity until loading. The port's Markdown image has no corresponding height or load-state behavior.
- A registered npm custom component rendered a custom `mark` element. Python `custom_components`, `code_style`, and `img_height` arguments all raised `TypeError` in the shared `Options` constructor.

The shared `AnimatedText`/`AnimatedMarkdown` options bag is not a suitable extension point for all these features. Introduce explicit component-level contracts while retaining the existing public facade for compatibility.

## Recommended design and implementation order

### 1. Establish the contract and failing tests

Freeze the npm reference at 1.0.40. Make a capability table executable: supported parity, intentional difference, and unsupported feature. Add reproductions for F1–F4 before implementation. Do not count framework health checks as renderer parity.

### 2. Remove duplicate rendering ownership

Keep the current Python/framework separation. Change the browser boundary:

- Python owns Markdown parsing, safe semantic HTML, and component configuration.
- The browser owns leaf reconciliation, stable DOM identities, token scheduling, animation, and lifecycle.
- Both plain-text and Markdown updates use that same reconciler.
- Whitespace stays structural text; animated words do not become layout containers for newlines.
- URL and attribute policies are explicit, total, and consistent across initial render and later updates.

This removes the need for Python to emit one animated-token tree while JavaScript discards or reconstructs it differently. It is a larger simplification than splitting the current update function into more helpers.

### 3. Close the missing public features

Add typed Markdown options for image behavior, code highlighting/theme selection, clipboard controls, link policy, and trusted custom renderers. Keep these out of text-only `Options`. Define server-rendered custom content separately from client-interactive components; do not try to execute Python callbacks in the browser.

### 4. Finish lifecycle and throughput

Make mount/unmount ownership explicit. Define what happens to pending completion promises after disposal. Give append operations an incremental path. Use one canonical declaration for option names/defaults and animation names, with cross-runtime validation fixtures, rather than allowing Python, JavaScript, and CSS to drift independently.

### 5. Re-run the release gate

Require:

- Existing Python and framework suites remain green.
- Public npm Markdown append/rewrite/reset sequences pass.
- Newline and multiline-code geometry is correct.
- Unchanged DOM nodes and image state survive updates.
- Invalid/incomplete URLs cannot abort rendering.
- Initial animation, disabled animation, and remount behavior are explicit and tested.
- Delayed images, code-copy success/failure, themes, and partial custom tags have browser tests.
- Every remaining deviation is listed in the compatibility matrix.

**Next recommended implementation:** the shared renderer/reconciliation change with F1–F4 regression tests. Adding syntax highlighting or custom tags first would build more behavior on top of an inconsistent update model.
