// Executa blocos de Python no navegador com Pyodide.
//
// Segurança: o código vem de páginas escritas por outras pessoas, então ele
// roda num Web Worker criado dentro de um <iframe sandbox="allow-scripts">.
// O iframe tem origem opaca: o código não acessa o DOM do WikiDev, não lê
// cookies e não consegue fazer requisições autenticadas em nome de quem
// clicou em "Executar". Um laço infinito é interrompido removendo o iframe.

const PYODIDE_VERSION = '0.26.4';
const PYODIDE_URL = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;
const RUN_TIMEOUT_MS = 10000;
const LOAD_TIMEOUT_MS = 90000;

const WORKER_SOURCE = `
let pyodideReady = null;
function load(indexURL) {
    if (!pyodideReady) {
        importScripts(indexURL + 'pyodide.js');
        pyodideReady = loadPyodide({ indexURL });
    }
    return pyodideReady;
}
self.onmessage = async (event) => {
    const { id, code, indexURL } = event.data;
    const out = [];
    const err = [];
    try {
        const pyodide = await load(indexURL);
        self.postMessage({ id, type: 'loaded' });
        pyodide.setStdout({ batched: (line) => out.push(line) });
        pyodide.setStderr({ batched: (line) => err.push(line) });
        pyodide.setStdin({ error: true });
        await pyodide.loadPackagesFromImports(code);
        const globals = pyodide.globals.get('dict')();
        const started = performance.now();
        let error = null;
        try {
            const value = await pyodide.runPythonAsync(code, { globals });
            if (value !== undefined && value !== null && out.length === 0) out.push(String(value));
        } catch (exc) {
            error = String(exc.message || exc);
        } finally {
            globals.destroy();
        }
        self.postMessage({ id, type: 'result', stdout: out.join('\\n'), stderr: err.join('\\n'), error, ms: Math.round(performance.now() - started) });
    } catch (exc) {
        self.postMessage({ id, type: 'result', stdout: '', stderr: '', error: 'Não foi possível carregar o Python: ' + (exc.message || exc), ms: 0 });
    }
};`;

const FRAME_SOURCE = `<!doctype html><meta charset="utf-8"><script>
const worker = new Worker(URL.createObjectURL(new Blob([${JSON.stringify(WORKER_SOURCE)}], { type: 'text/javascript' })));
worker.onmessage = (event) => parent.postMessage(event.data, '*');
worker.onerror = (event) => parent.postMessage({ id: null, type: 'crash', error: event.message }, '*');
addEventListener('message', (event) => { if (event.source === parent) worker.postMessage(event.data); });
<\/script>`;

const PythonRunner = {
    frame: null,
    loaded: false,
    pending: new Map(),
    nextId: 1,

    ensureFrame() {
        if (this.frame) return this.frame;
        const frame = document.createElement('iframe');
        frame.setAttribute('sandbox', 'allow-scripts');
        frame.setAttribute('aria-hidden', 'true');
        frame.title = 'Executor de Python';
        frame.style.display = 'none';
        frame.srcdoc = FRAME_SOURCE;
        document.body.appendChild(frame);
        this.frame = frame;
        this.ready = new Promise((resolve) => frame.addEventListener('load', resolve, { once: true }));
        return frame;
    },

    reset(reason) {
        this.frame?.remove();
        this.frame = null;
        this.loaded = false;
        for (const [, request] of this.pending) {
            clearTimeout(request.timer);
            request.resolve({ stdout: '', stderr: '', error: reason, ms: 0 });
        }
        this.pending.clear();
    },

    async run(code, onLoaded) {
        this.ensureFrame();
        await this.ready;
        const id = this.nextId++;
        return new Promise((resolve) => {
            const request = { resolve, onLoaded, timer: null };
            const arm = (ms, message) => {
                clearTimeout(request.timer);
                request.timer = setTimeout(() => this.reset(message), ms);
            };
            request.armRun = () => arm(RUN_TIMEOUT_MS, `Execução interrompida depois de ${RUN_TIMEOUT_MS / 1000} s (laço infinito?).`);
            if (this.loaded) request.armRun();
            else arm(LOAD_TIMEOUT_MS, 'O Python demorou demais para carregar. Verifique a conexão e tente de novo.');
            this.pending.set(id, request);
            this.frame.contentWindow.postMessage({ id, code, indexURL: PYODIDE_URL }, '*');
        });
    },

    handleMessage(event) {
        if (!this.frame || event.source !== this.frame.contentWindow) return;
        const data = event.data || {};
        if (data.type === 'crash') { this.reset(`O executor falhou: ${data.error}`); return; }
        const request = this.pending.get(data.id);
        if (!request) return;
        if (data.type === 'loaded') {
            if (!this.loaded) { this.loaded = true; }
            request.armRun();
            request.onLoaded?.();
            return;
        }
        if (data.type === 'result') {
            clearTimeout(request.timer);
            this.pending.delete(data.id);
            request.resolve(data);
        }
    },
};
window.addEventListener('message', (event) => PythonRunner.handleMessage(event));

function renderRunOutput(panel, result) {
    panel.replaceChildren();
    const lines = [];
    if (result.stdout) lines.push(['run-stdout', result.stdout]);
    if (result.stderr) lines.push(['run-stderr', result.stderr]);
    if (result.error) lines.push(['run-error', result.error]);
    if (!lines.length) lines.push(['run-muted', '(sem saída)']);
    const pre = document.createElement('pre');
    for (const [cls, text] of lines) {
        const span = document.createElement('span');
        span.className = cls;
        span.textContent = text.endsWith('\n') ? text : `${text}\n`;
        pre.appendChild(span);
    }
    const meta = document.createElement('div');
    meta.className = 'run-meta';
    meta.textContent = result.error ? 'Terminou com erro' : `Concluído em ${result.ms} ms`;
    panel.append(meta, pre);
}

document.addEventListener('click', async (event) => {
    const button = event.target.closest('.run-code-button');
    if (!button) return;
    const wrapper = button.closest('.code-block-wrapper');
    const panel = wrapper?.querySelector('.run-output');
    const code = wrapper?.querySelector('code')?.innerText ?? '';
    if (!panel) return;

    if (button.dataset.running === 'true') {
        PythonRunner.reset('Execução interrompida.');
        return;
    }
    button.dataset.running = 'true';
    button.textContent = 'Parar';
    panel.hidden = false;
    panel.innerHTML = `<div class="run-meta">${PythonRunner.loaded ? 'Executando…' : 'Carregando o Python no navegador (só na primeira vez)…'}</div>`;
    const result = await PythonRunner.run(code, () => {
        const meta = panel.querySelector('.run-meta');
        if (meta) meta.textContent = 'Executando…';
    });
    renderRunOutput(panel, result);
    button.dataset.running = 'false';
    button.textContent = 'Executar';
});
