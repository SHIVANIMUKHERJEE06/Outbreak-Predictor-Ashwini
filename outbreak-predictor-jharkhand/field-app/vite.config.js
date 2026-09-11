import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

// This config is what makes the app "offline-first". The VitePWA
// plugin auto-generates a service worker - a small background script
// that caches the app's files (HTML/CSS/JS) so the app still loads
// even with no internet connection, and auto-updates itself when a
// new version is deployed.
export default defineConfig({
  plugins: [
    VitePWA({
      registerType: 'autoUpdate',
      manifest: {
        name: 'ASHA Field Log - Outbreak Watch',
        short_name: 'ASHA Log',
        description: 'Offline symptom logging for community health workers',
        theme_color: '#c2185b',
        background_color: '#e8e2d0',
        display: 'standalone',
        icons: [
          {
            src: 'icon-192.png',
            sizes: '192x192',
            type: 'image/png',
          },
          {
            src: 'icon-512.png',
            sizes: '512x512',
            type: 'image/png',
          },
        ],
      },
      workbox: {
        // Caches every file the app needs so it works fully offline,
        // including the self-hosted font files (woff/woff2).
        globPatterns: ['**/*.{js,css,html,png,svg,woff,woff2}'],
      },
    }),
  ],
})
