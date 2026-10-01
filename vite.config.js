import { defineConfig } from 'vite';
import { sites } from '@openai/sites-vite-plugin';
export default defineConfig({plugins:[sites()],build:{ssr:'server/worker.js',outDir:'dist',rollupOptions:{output:{entryFileNames:'server/index.js'}},minify:false}});
