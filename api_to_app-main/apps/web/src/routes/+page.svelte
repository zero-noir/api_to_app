<script lang="ts">
  import { api, type ApiFile, type GenerateResponse, type Health, type HumanDecision, type UploadedApi } from '$lib/api/client';

  type Stage = 'upload' | 'scope' | 'decide' | 'artifacts';

  let stage = $state<Stage>('upload');
  let health = $state<Health | null>(null);
  let upload = $state<UploadedApi | null>(null);
  let files = $state<ApiFile[]>([]);
  let selected = $state<string[]>([]);
  let query = $state('');
  let loading = $state(false);
  let error = $state('');
  let appName = $state('Generated API Console');
  let objective = $state('Generate a production SvelteKit app from this API contract, including typed API client, page scaffold, env matrix, tests and implementation README.');
  let framework = $state('sveltekit');
  let apiStyle = $state('hybrid');
  let useLlm = $state(true);
  let copied = $state('');
  let activeArtifact = $state(0);
  let result = $state<GenerateResponse | null>(null);
  let decisions = $state<HumanDecision[]>([
    { id: 'auth', question: 'Authenticated API requests?', answer: 'yes' },
    { id: 'proxy', question: 'Route sensitive calls through a backend proxy?', answer: 'yes' },
    { id: 'writes', question: 'Require confirmation before mutating requests?', answer: 'yes' },
    { id: 'tests', question: 'Generate contract tests and mock-safe checks?', answer: 'yes' }
  ]);

  const visibleFiles = $derived(files.filter((file) => {
    const needle = query.toLowerCase();
    return !needle || `${file.path} ${file.kind}`.toLowerCase().includes(needle);
  }));

  const selectedCount = $derived(selected.length);
  const endpointCount = $derived(result?.endpoints.length ?? upload?.endpoint_count ?? 0);

  $effect(() => {
    api.health().then((data) => health = data).catch(() => {});
  });

  async function uploadInput(event: Event) {
    const file = (event.currentTarget as HTMLInputElement).files?.[0];
    if (!file) return;

    loading = true;
    error = '';

    try {
      upload = await api.upload(file);
      const data = await api.files(upload.session_id);
      files = data.files;
      selected = data.default_targets;
      stage = 'scope';
    } catch (e) {
      error = e instanceof Error ? e.message : 'Upload failed';
    } finally {
      loading = false;
    }
  }

  function setStage(next: Stage) {
    if (next === 'scope' && !upload) return;
    if (next === 'decide' && !upload) return;
    if (next === 'artifacts' && !result) return;
    stage = next;
  }

  function toggleFile(path: string) {
    selected = selected.includes(path) ? selected.filter((item) => item !== path) : [...selected, path];
  }

  function answer(id: string, value: 'yes' | 'no') {
    decisions = decisions.map((decision) => decision.id === id ? { ...decision, answer: value } : decision);
  }

  async function generate() {
    if (!upload) return;

    loading = true;
    error = '';

    try {
      result = await api.generate({
        session_id: upload.session_id,
        app_name: appName,
        objective,
        target_files: selected,
        framework,
        api_style: apiStyle,
        human_decisions: decisions,
        use_llm: useLlm
      });
      activeArtifact = 0;
      stage = 'artifacts';
    } catch (e) {
      error = e instanceof Error ? e.message : 'Generation failed';
    } finally {
      loading = false;
    }
  }

  async function copy(label: string, text: string) {
    await navigator.clipboard.writeText(text);
    copied = label;
    setTimeout(() => copied = '', 1300);
  }
</script>

<svelte:head>
  <title>API-to-App Generator</title>
</svelte:head>

<main class="studio">
  <aside class="side-panel" aria-label="Generator navigation">
    <div class="brand">
      <span class="brand-mark" aria-hidden="true">
        <svg viewBox="0 0 32 32"><path d="M8 17.2 14.2 11l6.4 6.4L14.2 24 8 17.2Z"/><path d="M18.6 8h5.6v5.6"/><path d="m17.8 14.2 6.1-6.1"/></svg>
      </span>
      <strong>ApiForge</strong>
    </div>

    <nav>
      <button type="button" class:active={stage === 'upload'} onclick={() => setStage('upload')}>Input</button>
      <button type="button" class:active={stage === 'scope'} disabled={!upload} onclick={() => setStage('scope')}>Scope</button>
      <button type="button" class:active={stage === 'decide'} disabled={!upload} onclick={() => setStage('decide')}>Decisions</button>
      <button type="button" class:active={stage === 'artifacts'} disabled={!result} onclick={() => setStage('artifacts')}>Artifacts</button>
    </nav>

    <section class="signal-card">
      <span class:online={health?.ai_enabled}></span>
      <div>
        <strong>{health?.ai_enabled ? 'Generation online' : 'Offline mode'}</strong>
        <small>{health?.provider ?? 'offline'} synthesis</small>
      </div>
    </section>
  </aside>

  <section class="workspace">
    <header class="hero">
      <div>
        <p class="eyebrow">API-to-app generator</p>
        <h1>Turn contracts and backend routes into production app artifacts.</h1>
        <span>Upload an API spec or repo, choose the target surface, answer build gates, and export implementation files.</span>
      </div>

      <div class="hero-metrics" aria-label="Current generation status">
        <div><strong>{endpointCount}</strong><span>Endpoints</span></div>
        <div><strong>{selectedCount}</strong><span>Files</span></div>
      </div>
    </header>

    {#if error}<p class="error">{error}</p>{/if}

    {#if stage === 'upload'}
      <section class="upload-stage">
        <div class="upload-card glass">
          <label for="api-upload">API spec, docs, Postman collection, or repository ZIP</label>
          <input id="api-upload" type="file" accept=".zip,.json,.yaml,.yml,.md,.txt" onchange={uploadInput} />
          <p>OpenAPI, Swagger, Postman, FastAPI, Express and Markdown API docs are converted into app-building artifacts.</p>
          <div class="supported">
            <span>OpenAPI</span><span>Postman</span><span>FastAPI</span><span>Express</span><span>Docs</span>
          </div>
        </div>

        <div class="futuristic-visual" aria-hidden="true">
          <svg viewBox="0 0 720 440" class="orbital-ui">
            <defs>
              <radialGradient id="orbGlow" cx="42%" cy="48%" r="58%">
                <stop offset="0%" stop-color="#ffffff" stop-opacity="0.7" />
                <stop offset="42%" stop-color="#9ea0a7" stop-opacity="0.22" />
                <stop offset="100%" stop-color="#050506" stop-opacity="0" />
              </radialGradient>
              <linearGradient id="panelLine" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stop-color="#f5f5f6" stop-opacity="0.85" />
                <stop offset="100%" stop-color="#777982" stop-opacity="0.12" />
              </linearGradient>
            </defs>

            <rect class="screen" x="48" y="38" width="624" height="364" rx="34" />
            <circle class="orb" cx="278" cy="228" r="132" fill="url(#orbGlow)" />
            <path class="ring r1" d="M130 230c52-78 204-116 318-73 104 39 136 127 66 183-72 58-222 61-316 7-87-51-99-123-68-117Z" />
            <path class="ring r2" d="M148 252c84-26 211-33 303 0 78 28 101 80 52 111-51 33-167 34-257 6-100-31-158-88-98-117Z" />
            <path class="ring r3" d="M182 190c46-45 154-74 246-48 84 24 125 83 91 132-37 53-147 73-244 46-99-28-149-81-93-130Z" />

            <g class="node source">
              <rect x="92" y="92" width="144" height="102" rx="20" />
              <path d="M118 128h68M118 152h88M118 176h54" />
              <circle cx="206" cy="122" r="7" />
            </g>

            <g class="node build">
              <rect x="462" y="96" width="150" height="118" rx="22" />
              <path d="M492 136h70M492 162h48M492 188h78" />
              <path class="tiny-check" d="M568 134l10 10 18-24" />
            </g>

            <g class="node export">
              <rect x="436" y="276" width="158" height="72" rx="20" />
              <path d="M464 308h88M464 330h58" />
              <circle cx="564" cy="314" r="12" />
            </g>

            <path class="connector" d="M242 146c70-28 142-26 214 0" />
            <path class="connector" d="M246 312c64 28 126 26 184 2" />
            <path class="arrow" d="M424 309l22 3-16 16" />
          </svg>
        </div>
      </section>
    {/if}

    {#if stage === 'scope' && upload}
      <section class="builder-grid">
        <div class="panel file-panel">
          <div class="panel-head">
            <div>
              <h2>{upload.name}</h2>
              <p>{upload.detected_stack.join(' / ')}</p>
            </div>
            <input aria-label="Filter files" placeholder="Filter files" bind:value={query} />
          </div>

          <div class="file-list">
            {#each visibleFiles as file}
              <button type="button" class:selected={selected.includes(file.path)} onclick={() => toggleFile(file.path)}>
                <span>{file.path}</span>
                <small>{file.kind}</small>
              </button>
            {/each}
          </div>
        </div>

        <aside class="panel config-panel">
          <label for="app-name">Generated app name</label>
          <input id="app-name" bind:value={appName} />

          <label for="objective">Generation objective</label>
          <textarea id="objective" bind:value={objective}></textarea>

          <label for="style">API integration style</label>
          <select id="style" bind:value={apiStyle}>
            <option value="direct_client">Direct browser client</option>
            <option value="backend_proxy">Backend proxy</option>
            <option value="hybrid">Hybrid</option>
          </select>

          <label class="check-row" for="llm">
            <input id="llm" type="checkbox" bind:checked={useLlm} />
            <span>Use LLM synthesis when configured</span>
          </label>

          <button type="button" class="primary wide" onclick={() => setStage('decide')} disabled={!selected.length}>Continue</button>
        </aside>
      </section>
    {/if}

    {#if stage === 'decide' && upload}
      <section class="decision-panel">
        <div class="section-title">
          <p>Build gates</p>
          <h2>Choose the production behavior before generation.</h2>
        </div>

        <div class="decision-list">
          {#each decisions as decision}
            <article>
              <span>{decision.question}</span>
              <div>
                <button type="button" class:active={decision.answer === 'yes'} onclick={() => answer(decision.id, 'yes')}>Yes</button>
                <button type="button" class:active={decision.answer === 'no'} onclick={() => answer(decision.id, 'no')}>No</button>
              </div>
            </article>
          {/each}
        </div>

        <button type="button" class="primary" onclick={generate} disabled={loading}>{loading ? 'Generating…' : 'Generate artifacts'}</button>
      </section>
    {/if}

    {#if stage === 'artifacts' && result}
      <section class="artifact-view">
        <div class="artifact-summary">
          <div>
            <p>Generated package</p>
            <h2>{result.summary}</h2>
          </div>
          <button type="button" onclick={() => copy('report', result.markdown_report)}>{copied === 'report' ? 'Copied' : 'Copy report'}</button>
        </div>

        <div class="artifact-body">
          <div class="artifact-tabs" aria-label="Generated artifacts">
            {#each result.artifacts as artifact, i}
              <button type="button" class:active={activeArtifact === i} onclick={() => activeArtifact = i}>{artifact.name}</button>
            {/each}
          </div>

          <div class="code-panel">
            <div class="code-head">
              <strong>{result.artifacts[activeArtifact].name}</strong>
              <button type="button" onclick={() => copy(result.artifacts[activeArtifact].name, result.artifacts[activeArtifact].content)}>{copied === result.artifacts[activeArtifact].name ? 'Copied' : 'Copy'}</button>
            </div>
            <pre>{result.artifacts[activeArtifact].content}</pre>
          </div>
        </div>
      </section>
    {/if}
  </section>
</main>

<style>
  :global(body) {
    margin: 0;
    min-width: 320px;
    background:
      radial-gradient(circle at 35% -12%, rgba(255,255,255,.16), transparent 30%),
      radial-gradient(circle at 88% 8%, rgba(170,174,190,.12), transparent 28%),
      #050506;
    color: #f5f5f6;
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 14px;
  }

  :global(*) { box-sizing: border-box; }

  .studio {
    min-height: 100vh;
    display: grid;
    grid-template-columns: 238px minmax(0, 1fr);
  }

  .side-panel {
    min-height: 100vh;
    position: sticky;
    top: 0;
    padding: 24px 16px;
    border-right: 1px solid rgba(255,255,255,.09);
    background: linear-gradient(180deg, rgba(12,12,14,.94), rgba(4,4,5,.98));
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .brand {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 10px;
  }

  .brand-mark {
    width: 34px;
    height: 34px;
    display: grid;
    place-items: center;
    border-radius: 13px;
    background: rgba(255,255,255,.08);
    border: 1px solid rgba(255,255,255,.14);
  }

  .brand svg {
    width: 20px;
    height: 20px;
    fill: none;
    stroke: #f5f5f6;
    stroke-width: 2.1;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  .brand strong { font-size: 15px; letter-spacing: -.01em; }

  nav {
    display: grid;
    gap: 7px;
  }

  button {
    font: inherit;
  }

  nav button {
    border: 1px solid transparent;
    border-radius: 15px;
    background: transparent;
    color: #9d9ea5;
    text-align: left;
    padding: 11px 12px;
    cursor: pointer;
  }

  nav button:hover,
  nav button.active {
    color: #fff;
    background: rgba(255,255,255,.08);
    border-color: rgba(255,255,255,.11);
  }

  nav button:disabled,
  button:disabled {
    opacity: .42;
    cursor: not-allowed;
  }

  .signal-card {
    margin-top: auto;
    display: flex;
    align-items: center;
    gap: 10px;
    border: 1px solid rgba(255,255,255,.1);
    border-radius: 22px;
    padding: 14px;
    background: rgba(255,255,255,.045);
  }

  .signal-card > span {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: #74757c;
    box-shadow: 0 0 0 5px rgba(255,255,255,.04);
  }

  .signal-card > span.online {
    background: #d8ff8f;
    box-shadow: 0 0 22px rgba(216,255,143,.45);
  }

  .signal-card strong,
  .signal-card small {
    display: block;
  }

  .signal-card strong { font-size: 13px; }
  .signal-card small { color: #9d9ea5; margin-top: 3px; }

  .workspace {
    padding: 28px 34px 46px;
  }

  .hero {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 24px;
    margin-bottom: 24px;
  }

  .eyebrow,
  .section-title p,
  .artifact-summary p {
    margin: 0 0 10px;
    color: #b9bac0;
    text-transform: uppercase;
    letter-spacing: .18em;
    font-size: 11px;
  }

  .hero h1 {
    max-width: 960px;
    margin: 0;
    font-size: clamp(36px, 5vw, 68px);
    line-height: .98;
    letter-spacing: -.065em;
    font-weight: 520;
  }

  .hero span {
    display: block;
    margin-top: 16px;
    max-width: 760px;
    color: #a2a3aa;
    line-height: 1.6;
  }

  .hero-metrics {
    min-width: 210px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }

  .hero-metrics div {
    border: 1px solid rgba(255,255,255,.1);
    background: rgba(255,255,255,.045);
    border-radius: 20px;
    padding: 14px;
  }

  .hero-metrics strong {
    display: block;
    font-size: 26px;
    font-weight: 520;
  }

  .hero-metrics span {
    display: block;
    margin-top: 4px;
    color: #9d9ea5;
    font-size: 12px;
  }

  .error {
    border: 1px solid rgba(255,111,96,.4);
    background: rgba(255,111,96,.08);
    color: #ffd4ce;
    padding: 11px 13px;
    border-radius: 16px;
  }

  .upload-stage,
  .builder-grid {
    display: grid;
    grid-template-columns: minmax(320px, .72fr) minmax(0, 1.28fr);
    gap: 18px;
  }

  .glass,
  .panel,
  .decision-panel,
  .artifact-summary,
  .code-panel {
    border: 1px solid rgba(255,255,255,.12);
    background: linear-gradient(145deg, rgba(255,255,255,.08), rgba(255,255,255,.035));
    box-shadow: 0 35px 100px rgba(0,0,0,.34);
    border-radius: 34px;
  }

  .upload-card,
  .panel,
  .decision-panel {
    padding: 20px;
  }

  label {
    display: block;
    margin: 0 0 9px;
    color: #c4c5ca;
    font-size: 12px;
  }

  input,
  textarea,
  select {
    width: 100%;
    border: 1px solid rgba(255,255,255,.13);
    background: rgba(5,5,6,.64);
    color: #fff;
    border-radius: 18px;
    padding: 12px 13px;
    outline: none;
  }

  input:focus,
  textarea:focus,
  select:focus {
    border-color: rgba(255,255,255,.35);
    box-shadow: 0 0 0 4px rgba(255,255,255,.06);
  }

  textarea {
    min-height: 140px;
    resize: vertical;
    line-height: 1.55;
  }

  .upload-card p {
    margin: 18px 0 16px;
    color: #b6b7bd;
    line-height: 1.6;
  }

  .supported {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .supported span {
    border: 1px solid rgba(255,255,255,.11);
    border-radius: 999px;
    padding: 7px 10px;
    color: #d4d5d9;
    background: rgba(255,255,255,.045);
    font-size: 12px;
  }

  .futuristic-visual {
    min-height: 410px;
    display: grid;
    place-items: center;
    border-radius: 34px;
    overflow: hidden;
    background:
      radial-gradient(circle at 46% 48%, rgba(255,255,255,.18), transparent 24%),
      radial-gradient(circle at 20% 10%, rgba(255,255,255,.12), transparent 30%),
      linear-gradient(145deg, #161618, #030304 72%);
    border: 1px solid rgba(255,255,255,.12);
  }

  .orbital-ui {
    width: min(720px, 98%);
  }

  .orbital-ui .screen {
    fill: rgba(255,255,255,.03);
    stroke: rgba(255,255,255,.1);
    stroke-width: 1.5;
  }

  .orbital-ui .orb {
    opacity: .95;
  }

  .orbital-ui .ring {
    fill: none;
    stroke: url(#panelLine);
    stroke-width: 2.2;
  }

  .orbital-ui .r2 { opacity: .64; }
  .orbital-ui .r3 { opacity: .48; }

  .orbital-ui .node rect {
    fill: rgba(255,255,255,.075);
    stroke: rgba(255,255,255,.17);
    stroke-width: 1.4;
  }

  .orbital-ui .node path,
  .orbital-ui .connector,
  .orbital-ui .arrow {
    fill: none;
    stroke: rgba(255,255,255,.82);
    stroke-width: 3.4;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  .orbital-ui .node circle {
    fill: #fff;
    opacity: .9;
  }

  .orbital-ui .tiny-check {
    stroke: #fff;
    stroke-width: 3.2;
  }

  .orbital-ui .connector {
    stroke: rgba(255,255,255,.28);
    stroke-width: 2.2;
  }

  .panel-head {
    display: flex;
    justify-content: space-between;
    gap: 14px;
    align-items: center;
    margin-bottom: 14px;
  }

  .panel-head h2,
  .section-title h2,
  .artifact-summary h2 {
    margin: 0;
    font-size: 20px;
    letter-spacing: -.03em;
    font-weight: 520;
  }

  .panel-head p {
    margin: 6px 0 0;
    color: #9d9ea5;
    font-size: 12px;
  }

  .panel-head input {
    max-width: 260px;
  }

  .file-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(245px, 1fr));
    gap: 10px;
    max-height: 66vh;
    overflow: auto;
  }

  .file-list button {
    border: 1px solid rgba(255,255,255,.1);
    background: rgba(0,0,0,.22);
    color: #fff;
    border-radius: 18px;
    padding: 12px;
    text-align: left;
    cursor: pointer;
  }

  .file-list button.selected {
    background: #f5f5f6;
    color: #050506;
    border-color: #f5f5f6;
  }

  .file-list span,
  .file-list small {
    display: block;
  }

  .file-list span {
    font-size: 12px;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .file-list small {
    margin-top: 6px;
    color: #9d9ea5;
  }

  .file-list button.selected small {
    color: #5b5d64;
  }

  .config-panel {
    display: grid;
    gap: 11px;
    align-self: start;
  }

  .check-row {
    display: flex;
    align-items: center;
    gap: 9px;
  }

  .check-row input {
    width: auto;
  }

  .primary {
    border: 1px solid rgba(255,255,255,.2);
    background: #f5f5f6;
    color: #050506;
    border-radius: 999px;
    padding: 12px 17px;
    cursor: pointer;
    font-weight: 650;
  }

  .wide { width: 100%; text-align: center; }

  .decision-panel {
    max-width: 900px;
  }

  .decision-list {
    margin: 18px 0;
    display: grid;
    gap: 10px;
  }

  .decision-list article {
    display: flex;
    justify-content: space-between;
    gap: 18px;
    align-items: center;
    padding: 14px;
    border-radius: 20px;
    background: rgba(0,0,0,.18);
    border: 1px solid rgba(255,255,255,.09);
  }

  .decision-list article span {
    font-weight: 570;
  }

  .decision-list article div {
    display: flex;
    gap: 8px;
  }

  .decision-list article button,
  .artifact-summary button,
  .code-head button {
    border: 1px solid rgba(255,255,255,.14);
    background: rgba(255,255,255,.05);
    color: #fff;
    border-radius: 999px;
    padding: 8px 13px;
    cursor: pointer;
  }

  .decision-list article button.active {
    background: #f5f5f6;
    color: #050506;
  }

  .artifact-view {
    display: grid;
    gap: 16px;
  }

  .artifact-summary {
    padding: 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 18px;
  }

  .artifact-body {
    display: grid;
    grid-template-columns: 300px minmax(0, 1fr);
    gap: 16px;
  }

  .artifact-tabs {
    display: grid;
    gap: 9px;
    align-self: start;
  }

  .artifact-tabs button {
    border: 1px solid rgba(255,255,255,.1);
    background: rgba(255,255,255,.045);
    color: #d9dade;
    border-radius: 16px;
    padding: 12px;
    text-align: left;
    cursor: pointer;
  }

  .artifact-tabs button.active {
    background: #f5f5f6;
    color: #050506;
    border-color: #f5f5f6;
  }

  .code-panel {
    min-width: 0;
    padding: 16px;
  }

  .code-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
  }

  pre {
    max-height: 66vh;
    overflow: auto;
    margin: 0;
    border-radius: 22px;
    background: #030304;
    color: #f7f7f8;
    border: 1px solid rgba(255,255,255,.09);
    padding: 16px;
    font-size: 12px;
    line-height: 1.55;
  }

  @media (max-width: 1120px) {
    .studio { grid-template-columns: 1fr; }
    .side-panel { position: static; min-height: auto; }
    .upload-stage,
    .builder-grid,
    .artifact-body { grid-template-columns: 1fr; }
    .hero { display: grid; }
    .hero-metrics { max-width: 280px; }
  }
</style>
