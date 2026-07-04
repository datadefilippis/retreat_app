import { defineConfig } from 'vite';
import { resolve } from 'node:path';

/**
 * Embed SDK Vite config — Phase 0 Step 11 (2026-05-28).
 *
 * Two output formats:
 *   - ESM (afianco-embed.es.js)  — moderno, importabile via <script type="module">
 *   - UMD (afianco-embed.umd.js) — legacy fallback per WordPress / siti vecchi
 *
 * Target ES2017 perché:
 *   - Async/await nativo (no babel-polyfill)
 *   - Class fields supportate (necessario per Lit @property decorators)
 *   - Funziona su Safari 11+ / Edge 80+ / Chrome 60+ / WP visitor target
 *
 * Lit è bundled inline (no peer dep) per evitare version drift sul lato
 * merchant: il merchant copia 1 <script> tag e basta.
 */
export default defineConfig({
  build: {
    target: 'es2017',
    outDir: 'dist',
    emptyOutDir: true,
    minify: 'esbuild',
    sourcemap: true,
    lib: {
      entry: resolve(__dirname, 'src/index.ts'),
      name: 'AfiancoEmbed',
      fileName: (format) => `afianco-embed.${format}.js`,
      formats: ['es', 'umd'],
    },
    rollupOptions: {
      // NESSUNA external — vogliamo bundle self-contained (~80KB gzip target)
      // Merchant copy-paste un solo <script> → tutto incluso.
      output: {
        // UMD global per legacy `<script src="..."></script>` senza type=module
        globals: {},
      },
    },
  },
  esbuild: {
    legalComments: 'none',
  },
  test: {
    environment: 'happy-dom',
    globals: false,
    include: ['tests/**/*.test.ts'],
    setupFiles: ['./tests/setup.ts'],
  },
});
