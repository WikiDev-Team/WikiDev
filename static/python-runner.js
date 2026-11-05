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
const MAX_FIGURES = 6;
const BASE64_RE = /^[A-Za-z0-9+/]+={0,2}$/;

// Antes do código: matplotlib desenha em memória (Agg) e plt.show() não faz nada.
const MATPLOTLIB_SETUP = `
import os
os.environ['MPLBACKEND'] = 'Agg'
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.close('all')
plt.show = lambda *args, **kwargs: None
`;

// Depois do código: cada figura aberta vira um PNG em base64.
const COLLECT_FIGURES = `
def _wikidev_figures():
    import base64, io, sys
    plt = sys.modules.get('matplotlib.pyplot')
    if plt is None:
        return []
    images = []
    for number in plt.get_fignums()[:${MAX_FIGURES}]:
        buffer = io.BytesIO()
        plt.figure(number).savefig(buffer, format='png', dpi=96, bbox_inches='tight')
        images.append(base64.b64encode(buffer.getvalue()).decode('ascii'))
    plt.close('all')
    return images
_wikidev_figures()
`;

const WORKER_SOURCE = `
const MATPLOTLIB_SETUP = ${JSON.stringify(MATPLOTLIB_SETUP)};
const COLLECT_FIGURES = ${JSON.stringify(COLLECT_FIGURES)};
let pyodideReady = null;
function load(indexURL) {
    if (!pyodideReady) {
        importScripts(indexURL + 'pyodide.js');
        pyodideReady = loadPyodide({ indexURL });
    }
    return pyodideReady;
}
function figures(pyodide) {
    if (!pyodide.loadedPackages.matplotlib) return [];
    const scratch = pyodide.globals.get('dict')();
    try {
        const proxy = pyodide.runPython(COLLECT_FIGURES, { globals: scratch });
        const list = proxy.toJs();
        proxy.destroy();
        return list;
    } catch (exc) {
        return [];
    } finally {
        scratch.destroy();
    }
}
self.onmessage = async (event) => {
    const { id, code, indexURL } = event.data;
    const out = [];
    const err = [];
    try {
        const pyodide = await load(indexURL);
        pyodide.setStdout({ batched: (line) => out.push(line) });
        pyodide.setStderr({ batched: (line) => err.push(line) });
        pyodide.setStdin({ error: true });
        await pyodide.loadPackagesFromImports(code);
        if (pyodide.loadedPackages.matplotlib) pyodide.runPython(MATPLOTLIB_SETUP, { globals: pyodide.globals.get('dict')() });
        // Só a partir daqui conta o tempo limite de execução (download de pacotes não conta).
        self.postMessage({ id, type: 'loaded' });
        const globals = pyodide.globals.get('dict')();
        const started = performance.now();
        let error = null;
        try {
            const value = await pyodide.runPythonAsync(code, { globals });
            if (value !== undefined && value !== null && out.length === 0) out.push(String(value));
            if (value && typeof value.destroy === 'function') value.destroy();
        } catch (exc) {
            error = String(exc.message || exc);
        } finally {
            globals.destroy();
        }
        const images = figures(pyodide);
        self.postMessage({ id, type: 'result', stdout: out.join('\\n'), stderr: err.join('\\n'), error, images, ms: Math.round(performance.now() - started) });
    } catch (exc) {
        self.postMessage({ id, type: 'result', stdout: '', stderr: '', error: 'Não foi possível carregar o Python: ' + (exc.message || exc), images: [], ms: 0 });
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
            request.resolve({ stdout: '', stderr: '', error: reason, images: [], ms: 0 });
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
            arm(LOAD_TIMEOUT_MS, 'O Python demorou demais para carregar. Verifique a conexão e tente de novo.');
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
            this.loaded = true;
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

// As imagens vêm do iframe isolado: só aceitamos base64 puro, exibido como PNG.
function safeImages(images) {
    if (!Array.isArray(images)) return [];
    return images.filter((image) => typeof image === 'string' && BASE64_RE.test(image)).slice(0, MAX_FIGURES);
}

function button(label, className) {
    const element = document.createElement('button');
    element.type = 'button';
    element.className = `code-action-button ${className}`;
    element.textContent = label;
    return element;
}

function renderRunOutput(panel, result, { saveable }) {
    panel.replaceChildren();
    const images = safeImages(result.images);
    const lines = [];
    if (result.stdout) lines.push(['run-stdout', result.stdout]);
    if (result.stderr) lines.push(['run-stderr', result.stderr]);
    if (result.error) lines.push(['run-error', result.error]);
    if (result.error && result.error.includes('ModuleNotFoundError')) {
        lines.push(['run-muted', 'No navegador só estão disponíveis a biblioteca padrão e os pacotes do Pyodide (numpy, pandas, matplotlib etc.). Frameworks como FastAPI precisam rodar no seu computador.']);
    }
    if (!lines.length && !images.length) lines.push(['run-muted', '(sem saída)']);

    const meta = document.createElement('div');
    meta.className = 'run-meta';
    meta.textContent = result.error ? 'Terminou com erro' : `Concluído em ${result.ms} ms`;
    panel.append(meta);

    if (images.length) {
        const gallery = document.createElement('div');
        gallery.className = 'run-images';
        images.forEach((image, index) => {
            const img = document.createElement('img');
            img.src = `data:image/png;base64,${image}`;
            img.alt = `Gráfico ${index + 1} gerado pelo código`;
            gallery.appendChild(img);
        });
        panel.append(gallery);
    }
    if (lines.length) {
        const pre = document.createElement('pre');
        for (const [cls, text] of lines) {
            const span = document.createElement('span');
            span.className = cls;
            span.textContent = text.endsWith('\n') ? text : `${text}\n`;
            pre.appendChild(span);
        }
        panel.append(pre);
    }
    if (saveable) {
        const actions = document.createElement('div');
        actions.className = 'run-actions';
        const save = button('Salvar saída na página', 'save-output-button');
        save.title = 'Quem abrir a página vê esta saída sem precisar executar';
        save.runResult = { stdout: result.stdout || '', stderr: result.stderr || '', error: result.error || null, ms: result.ms || 0, images };
        actions.append(save);
        panel.append(actions);
    }
}

function codeOf(wrapper) {
    const editor = wrapper.querySelector('.try-editor');
    return editor ? editor.value : (wrapper.querySelector('code')?.innerText ?? '');
}

async function runBlock(wrapper) {
    const runButton = wrapper.querySelector('.run-code-button');
    const panel = wrapper.querySelector('.run-output');
    if (!runButton || !panel) return;

    if (runButton.dataset.running === 'true') {
        PythonRunner.reset('Execução interrompida.');
        return;
    }
    const experimenting = Boolean(wrapper.querySelector('.try-editor'));
    runButton.dataset.running = 'true';
    runButton.textContent = 'Parar';
    panel.hidden = false;
    panel.innerHTML = `<div class="run-meta">${PythonRunner.loaded ? 'Executando…' : 'Carregando o Python no navegador (só na primeira vez)…'}</div>`;
    const result = await PythonRunner.run(codeOf(wrapper), () => {
        const meta = panel.querySelector('.run-meta');
        if (meta) meta.textContent = 'Executando…';
    });
    // Só dá para salvar a saída do código que está na página, não de uma versão experimental.
    renderRunOutput(panel, result, { saveable: Boolean(wrapper.dataset.outputUrl) && !experimenting });
    runButton.dataset.running = 'false';
    runButton.textContent = 'Executar';
}

async function sendOutput(wrapper, method, body) {
    const response = await fetch(wrapper.dataset.outputUrl, {
        method,
        credentials: 'same-origin',
        headers: body ? { 'Content-Type': 'application/json' } : {},
        body: body ? JSON.stringify(body) : undefined,
    });
    if (!response.ok) {
        let detail = 'Não foi possível salvar.';
        try { detail = (await response.json()).detail || detail; } catch { /* resposta sem JSON */ }
        throw new Error(typeof detail === 'string' ? detail : 'Saída inválida.');
    }
}

function toggleExperiment(wrapper, tryButton) {
    const pre = wrapper.querySelector('pre.code-block');
    const existing = wrapper.querySelector('.try-editor');
    if (existing) {
        existing.remove();
        pre.hidden = false;
        tryButton.textContent = 'Experimentar';
        tryButton.title = 'Mudar o código e rodar aqui, sem alterar a página';
        wrapper.classList.remove('is-experimenting');
        return;
    }
    const editor = document.createElement('textarea');
    editor.className = 'try-editor code-input';
    editor.spellcheck = false;
    editor.value = pre.querySelector('code')?.innerText ?? '';
    editor.rows = Math.min(Math.max(editor.value.split('\n').length + 1, 4), 30);
    editor.setAttribute('aria-label', 'Cópia editável do código (só no seu navegador)');
    pre.hidden = true;
    pre.after(editor);
    wrapper.classList.add('is-experimenting');
    tryButton.textContent = 'Restaurar';
    tryButton.title = 'Voltar ao código original da página';
    editor.focus();
}

document.addEventListener('click', async (event) => {
    const wrapper = event.target.closest('.code-block-wrapper');
    if (!wrapper) return;

    if (event.target.closest('.run-code-button')) {
        await runBlock(wrapper);
        return;
    }
    const tryButton = event.target.closest('.try-code-button');
    if (tryButton) {
        toggleExperiment(wrapper, tryButton);
        return;
    }
    const save = event.target.closest('.save-output-button');
    if (save && save.runResult) {
        save.disabled = true;
        save.textContent = 'Salvando…';
        try {
            await sendOutput(wrapper, 'PUT', save.runResult);
            save.textContent = 'Salvo na página';
            const meta = wrapper.querySelector('.run-meta');
            if (meta) meta.textContent = 'Saída salva com a página';
            const clear = button('Remover saída salva', 'clear-output-button');
            save.replaceWith(clear);
        } catch (error) {
            save.disabled = false;
            save.textContent = 'Salvar saída na página';
            window.showToast?.(error.message);
        }
        return;
    }
    const clear = event.target.closest('.clear-output-button');
    if (clear) {
        clear.disabled = true;
        try {
            await sendOutput(wrapper, 'DELETE');
            const panel = wrapper.querySelector('.run-output');
            panel.replaceChildren();
            panel.hidden = true;
        } catch (error) {
            clear.disabled = false;
            window.showToast?.(error.message);
        }
    }
});

// Na cópia experimental: Tab indenta e Ctrl+Enter executa.
document.addEventListener('keydown', (event) => {
    const editor = event.target.closest?.('.try-editor');
    if (!editor) return;
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
        event.preventDefault();
        runBlock(editor.closest('.code-block-wrapper'));
    } else if (event.key === 'Tab' && !event.shiftKey) {
        event.preventDefault();
        editor.setRangeText('    ', editor.selectionStart, editor.selectionEnd, 'end');
    }
});
