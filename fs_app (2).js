globalThis.__noLangAsk = globalThis.__noLangAsk === undefined ? true : globalThis.__noLangAsk; // tests: no language question after login unless a test asks for it
export function initializeApp(cfg) { if (!cfg.projectId) throw new Error('no projectId'); return { cfg }; }
