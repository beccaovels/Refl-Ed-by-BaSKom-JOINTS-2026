// Three seconds of "sit how you teach" give the teacher's own resting values. Every later
// measure is compared with these, so a naturally serious face or a low chair is not marked down.

import { NEUTRAL_FACE, reliable, uprightness } from './features'
import type { Baseline, Frame } from './types'

export const CALIBRATION_MS = 3_000

/** Used when calibration is skipped or the camera saw nothing: a typical seated position. */
export const DEFAULT_BASELINE: Baseline = { shape: NEUTRAL_FACE, yaw: 0, pitch: 0, uprightness: 0.9 }

function median(values: number[]): number {
  const sorted = [...values].sort((a, b) => a - b)
  const middle = Math.floor(sorted.length / 2)
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2
}

/** The middle value of each measure over the calibration frames. A blink or a glance away does not shift it. */
export function baselineFrom(frames: Frame[]): Baseline {
  const faces = frames.filter(reliable).flatMap((frame) => (frame.face ? [frame.face] : []))
  const heights = frames.flatMap((frame) => {
    const height = frame.body ? uprightness(frame.body) : null
    return height === null ? [] : [height]
  })
  if (faces.length === 0) return { ...DEFAULT_BASELINE, uprightness: heights.length ? median(heights) : DEFAULT_BASELINE.uprightness }
  return {
    shape: {
      smile: median(faces.map((f) => f.shape.smile)),
      browUp: median(faces.map((f) => f.shape.browUp)),
      browDown: median(faces.map((f) => f.shape.browDown)),
      cheek: median(faces.map((f) => f.shape.cheek)),
    },
    yaw: median(faces.map((f) => f.yaw)),
    pitch: median(faces.map((f) => f.pitch)),
    uprightness: heights.length ? median(heights) : DEFAULT_BASELINE.uprightness,
  }
}
