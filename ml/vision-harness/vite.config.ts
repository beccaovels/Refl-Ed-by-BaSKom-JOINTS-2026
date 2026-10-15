import { fileURLToPath } from 'node:url'

import { defineConfig } from 'vitest/config'

// The signal code lives in the frontend folder, where the Room will import it. This small
// project only borrows it, so it can be typechecked, tested and tried before the frontend exists.
const vision = fileURLToPath(new URL('../../frontend/src/features/simulator/vision', import.meta.url))
const mediapipe = fileURLToPath(new URL('./node_modules/@mediapipe/tasks-vision', import.meta.url))

export default defineConfig({
  resolve: { alias: { '@vision': vision, '@mediapipe/tasks-vision': mediapipe } },
  server: { port: 5174, fs: { allow: ['../..'] } },
  test: { include: ['tests/**/*.test.ts'] },
})
