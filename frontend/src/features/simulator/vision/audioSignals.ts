// Voice signals from the microphone: loudness and pitch. This is what "tone" is measured from;
// speech-to-text only produces words. Works with the camera off.
//
// The maths (detectPitch, semitoneSpread, loudness) are pure functions; VoiceMeter is the thin
// part that reads the microphone through the browser's Web Audio API.

import type { VoiceSample } from './types'

const LOWEST_HZ = 75 // below a low adult voice
const HIGHEST_HZ = 400 // above a high adult speaking voice
const QUIET = 0.01 // loudness under this is treated as no voice
const CLEAR = 0.5 // how well the wave repeats itself; under this it is noise, not a pitch
const NEARLY_BEST = 0.9
const READ_EVERY_MS = 50

/** Root-mean-square level of the samples, 0-1 for normal microphone input. */
export function rms(samples: Float32Array): number {
  let sum = 0
  for (let i = 0; i < samples.length; i++) sum += samples[i] * samples[i]
  return Math.sqrt(sum / (samples.length || 1))
}

/** Loudness on a 0-1 scale where 0 is about -60 dB and 1 is full level. */
export function loudness(samples: Float32Array): number {
  const level = rms(samples)
  if (level <= 0) return 0
  return Math.min(Math.max((20 * Math.log10(level) + 60) / 60, 0), 1)
}

/**
 * Pitch of a short piece of sound in hertz, or null when it holds no clear voice.
 * Method: autocorrelation, that is, sliding the wave along itself to find after how many
 * samples it repeats. Only repeat lengths inside the human speaking range are tried.
 */
export function detectPitch(samples: Float32Array, sampleRate: number): number | null {
  if (rms(samples) < QUIET) return null
  const shortest = Math.floor(sampleRate / HIGHEST_HZ)
  const longest = Math.min(Math.floor(sampleRate / LOWEST_HZ), samples.length - 1)
  let energy = 0
  for (let i = 0; i < samples.length; i++) energy += samples[i] * samples[i]
  const matches: number[] = []
  let best = 0
  for (let lag = shortest; lag <= longest; lag++) {
    let sum = 0
    for (let i = 0; i + lag < samples.length; i++) sum += samples[i] * samples[i + lag]
    // Fewer samples overlap at a long lag; scale so lags are comparable.
    const match = (sum / (samples.length - lag)) / (energy / samples.length)
    matches.push(match)
    if (match > best) best = match
  }
  if (best < CLEAR) return null
  // A wave also repeats after two or three of its periods, which would read as a voice an
  // octave too low. So take the shortest repeat that matches nearly as well as the best one.
  for (let i = 1; i < matches.length - 1; i++) {
    const isPeak = matches[i] >= matches[i - 1] && matches[i] >= matches[i + 1]
    if (isPeak && matches[i] >= best * NEARLY_BEST) return sampleRate / (shortest + i)
  }
  return sampleRate / (shortest + matches.indexOf(best))
}

/**
 * How much the pitch moved, as a standard deviation in semitones. Semitones make a low voice
 * and a high voice comparable: both score the same for the same musical movement.
 * Roughly, under 1.5 sounds flat and over 3 sounds lively.
 */
export function semitoneSpread(pitches: number[]): number {
  if (pitches.length < 2) return 0
  const semitones = pitches.map((hz) => 12 * Math.log2(hz))
  // The middle 90% only, so one misread pitch does not look like expressiveness.
  const sorted = [...semitones].sort((a, b) => a - b)
  const cut = Math.floor(sorted.length * 0.05)
  const kept = sorted.slice(cut, sorted.length - cut)
  const mean = kept.reduce((sum, s) => sum + s, 0) / kept.length
  return Math.sqrt(kept.reduce((sum, s) => sum + (s - mean) ** 2, 0) / kept.length)
}

/** Reads the microphone twenty times a second and reports loudness and pitch. Audio never leaves this object. */
export class VoiceMeter {
  private context: AudioContext | null = null
  private timer: ReturnType<typeof setInterval> | null = null

  /** `now` returns milliseconds since the lesson started, so readings line up with the transcript. */
  start(stream: MediaStream, now: () => number, onSample: (sample: VoiceSample) => void): void {
    const context = new AudioContext()
    const analyser = context.createAnalyser()
    analyser.fftSize = 2048
    context.createMediaStreamSource(stream).connect(analyser)
    const samples = new Float32Array(analyser.fftSize)
    this.context = context
    this.timer = setInterval(() => {
      analyser.getFloatTimeDomainData(samples)
      onSample({ t_ms: now(), volume: loudness(samples), pitch: detectPitch(samples, context.sampleRate) })
    }, READ_EVERY_MS)
  }

  stop(): void {
    if (this.timer !== null) clearInterval(this.timer)
    void this.context?.close()
    this.timer = null
    this.context = null
  }
}
