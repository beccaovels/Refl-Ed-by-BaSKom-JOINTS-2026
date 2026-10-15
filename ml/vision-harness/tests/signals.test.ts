import { describe, expect, it } from 'vitest'

import { detectPitch, loudness, semitoneSpread } from '@vision/audioSignals'
import { Binner, makeBin } from '@vision/binning'
import { NEUTRAL_FACE } from '@vision/features'
import type { Baseline, Bin, Frame, VoiceSample } from '@vision/types'

const baseline: Baseline = { shape: NEUTRAL_FACE, yaw: 0, pitch: 0, uprightness: 0.9 }
const SAMPLE_RATE = 48_000

function tone(hz: number, level = 0.3): Float32Array {
  const samples = new Float32Array(2048)
  for (let i = 0; i < samples.length; i++) samples[i] = level * Math.sin((2 * Math.PI * hz * i) / SAMPLE_RATE)
  return samples
}

function frame(t_ms: number, overrides: Partial<Frame> = {}): Frame {
  return {
    t_ms,
    brightness: 120,
    face: { shape: NEUTRAL_FACE, yaw: 0, pitch: 0, size: 0.25 },
    body: {
      leftShoulder: { x: 0.7, y: 0.6 },
      rightShoulder: { x: 0.3, y: 0.6 },
      leftWrist: { x: 0.7, y: 0.9 },
      rightWrist: { x: 0.3, y: 0.9 },
      nose: { x: 0.5, y: 0.24 },
    },
    ...overrides,
  }
}

function voice(t_ms: number, pitch: number | null, volume = 0.5): VoiceSample {
  return { t_ms, pitch, volume }
}

describe('voice', () => {
  it('finds the pitch of a steady tone in the speaking range', () => {
    expect(detectPitch(tone(120), SAMPLE_RATE)).toBeCloseTo(120, -1) // a low voice
    expect(detectPitch(tone(220), SAMPLE_RATE)).toBeCloseTo(220, -1) // a higher voice
  })

  it('hears no pitch in silence or in noise', () => {
    expect(detectPitch(new Float32Array(2048), SAMPLE_RATE)).toBeNull()
    let seed = 7
    const noise = Float32Array.from({ length: 2048 }, () => {
      seed = (seed * 16807) % 2147483647
      return (seed / 2147483647 - 0.5) * 0.6
    })
    expect(detectPitch(noise, SAMPLE_RATE)).toBeNull()
  })

  it('scores a flat voice low and a moving voice high, whatever the speaker\'s register', () => {
    const flat = [118, 120, 121, 119, 120, 122, 120, 119]
    const lively = [110, 150, 125, 180, 140, 200, 120, 165]
    expect(semitoneSpread(flat)).toBeLessThan(1)
    expect(semitoneSpread(lively)).toBeGreaterThan(3)
    // The same movement an octave higher scores the same.
    expect(semitoneSpread(lively.map((hz) => hz * 2))).toBeCloseTo(semitoneSpread(lively))
  })

  it('puts loudness on a 0-1 scale', () => {
    expect(loudness(new Float32Array(2048))).toBe(0)
    expect(loudness(tone(200, 0.5))).toBeGreaterThan(loudness(tone(200, 0.05)))
    expect(loudness(tone(200, 1))).toBeLessThanOrEqual(1)
  })
})

describe('bins', () => {
  it('sends voice only when the camera is off', () => {
    const samples = Array.from({ length: 20 }, (_, i) => voice(i * 50, i % 2 ? 110 : 190))
    const bin = makeBin(0, [], samples, baseline)
    expect(bin.measured).toBe(true)
    expect(bin.expressiveness).toBeNull()
    expect(bin.face_visible_pct).toBeNull()
    expect(bin.pitch_variation).toBeGreaterThan(3)
    expect(bin.volume).toBeCloseTo(0.5)
  })

  it('leaves pitch empty when nobody spoke', () => {
    expect(makeBin(0, [], [voice(0, null, 0.02), voice(50, null, 0.02)], baseline).pitch_variation).toBeNull()
  })

  it('marks a dark stretch as not measured rather than scoring it', () => {
    const dark = Array.from({ length: 10 }, (_, i) => frame(i * 200, { brightness: 15 }))
    const bin = makeBin(0, dark, [], baseline)
    expect(bin.measured).toBe(false)
    expect(bin.expressiveness).toBeNull()
    expect(bin.posture_ok_pct).toBeNull()
  })

  it('reports a lively face, moving hands and time out of frame', () => {
    const smiling = { shape: { ...NEUTRAL_FACE, smile: 0.4 }, yaw: 0, pitch: 0, size: 0.25 }
    const frames = Array.from({ length: 10 }, (_, i) =>
      frame(i * 200, {
        face: i < 8 ? smiling : null, // out of frame for the last two
        body: {
          leftShoulder: { x: 0.7, y: 0.6 },
          rightShoulder: { x: 0.3, y: 0.6 },
          leftWrist: { x: 0.7 - (i % 2) * 0.15, y: 0.9 }, // waving
          rightWrist: { x: 0.3, y: 0.9 },
          nose: { x: 0.5, y: 0.24 },
        },
      }),
    )
    const bin = makeBin(0, frames, [], baseline)
    expect(bin.expressiveness).toBeCloseTo(0.4)
    expect(bin.face_visible_pct).toBeCloseTo(0.8)
    expect(bin.facing_pct).toBeCloseTo(0.8)
    expect(bin.gesture_rate).toBe(1)
    expect(bin.posture_ok_pct).toBe(1)
  })

  it('emits one bin per ten seconds, and the last partial one on flush', () => {
    const bins: Bin[] = []
    const binner = new Binner(baseline, (bin) => bins.push(bin))
    for (let t = 0; t < 25_000; t += 1_000) binner.addVoice(voice(t, 150))
    expect(bins.map((bin) => bin.t_start_ms)).toEqual([0, 10_000])
    binner.flush()
    expect(bins.map((bin) => bin.t_start_ms)).toEqual([0, 10_000, 20_000])
  })

  it('has exactly the fields of Bin in the API contract', () => {
    expect(Object.keys(makeBin(0, [frame(0)], [], baseline)).sort()).toEqual(
      ['expressiveness', 'face_visible_pct', 'facing_pct', 'gesture_rate', 'measured', 'pitch_variation', 'posture_ok_pct', 't_start_ms', 'volume'].sort(),
    )
  })
})
