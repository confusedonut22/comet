import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

// https://vite.dev/config/
export default defineConfig({
  base: "./",
  plugins: [svelte()],
  server: {
    allowedHosts: true,
  },
  build: {
    // Flatten output — Stake Engine upload expects all files at the root
    // of the frontend folder with no subdirectories
    assetsDir: '',
    rollupOptions: {
      output: {
        // Keep hashed filenames for cache-busting but no assets/ subfolder
        assetFileNames: '[name]-[hash][extname]',
        chunkFileNames: '[name]-[hash].js',
        entryFileNames: '[name]-[hash].js',
      },
    },
  },
})
