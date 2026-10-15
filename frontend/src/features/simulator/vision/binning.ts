// Collects frames and voice readings and hands back one Bin for every ten seconds.

import { faceLiveliness, facing, handsMoving, postureOk, reliable } from './features'
import { semitoneSpread } from './audioSignals'
import { BIN_MS } from './types'
import type { Baseline, Bin, Frame, VoiceSample } from './types'

const MIN_RELIABLE_SHARE = 0.5 // below this the bin is marked "not measured"
const MIN_VOICED = 8 // voice readings needed before a pitch spread means anything

function share(flags: boolean[]): number | null {
  return flags.length ? flags.filter(Boolean).length / flags.length : null
}

function mean(values: number[]): number | null {
  return values.length ? values.reduce((sum, v) => sum + v, 0) / values.length : null
}

/** One bin from the frames and voice readings that fall inside it. */
export function makeBin(t_start_ms: number, frames: Frame[], voice: VoiceSample[], baseline: Baseline): Bin {
  const volume = mean(voice.map((v) => v.volume))
  const pitches = voice.flatMap((v) => (v.pitch === null ? [] : [v.pitch]))
  const sound = { volume, pitch_variation: pitches.length >= MIN_VOICED ? semitoneSpread(pitches) : null }

  if (frames.length === 0) {
    // Camera off: voice only. Nothing was unreliable, so the bin still counts as measured.
    return { t_start_ms, facing_pct: null, posture_ok_pct: null, gesture_rate: null, expressiveness: null, face_visible_pct: null, ...sound, measured: true }
  }

  const good = frames.filter(reliable)
  if (good.length / frames.length < MIN_RELIABLE_SHARE) {
    // Too dark or too far to trust: say so instead of guessing.
    return { t_start_ms, facing_pct: null, posture_ok_pct: null, gesture_rate: null, expressiveness: null, face_visible_pct: null, ...sound, measured: false }
  }

  const faces = good.flatMap((frame) => (frame.face ? [frame.face] : []))
  const posture = good.flatMap((frame) => {
    const ok = frame.body ? postureOk(frame.body, baseline) : null
    return ok === null ? [] : [ok]
  })
  const moving: boolean[] = []
  for (let i = 1; i < good.length; i++) {
    moving.push(handsMoving(good[i - 1].body, good[i].body, (good[i].t_ms - good[i - 1].t_ms) / 1000))
  }
  // A face that is found but out of view the rest of the time is not "facing" for that time.
  const facingFlags = good.map((frame) => frame.face !== null && facing(frame.face, baseline))

  return {
    t_start_ms,
    facing_pct: share(facingFlags),
    posture_ok_pct: share(posture),
    gesture_rate: share(moving) ?? 0,
    expressiveness: mean(faces.map((face) => faceLiveliness(face.shape, baseline.shape))) ?? 0,
    face_visible_pct: faces.length / good.length,
    ...sound,
    measured: true,
  }
}

/** Feed it frames and voice readings as they come; it calls `onBin` each time ten seconds are complete. */
export class Binner {
  private frames: Frame[] = []
  private voice: VoiceSample[] = []
  private start = 0

  constructor(
    private baseline: Baseline,
    private onBin: (bin: Bin) => void,
  ) {}

  setBaseline(baseline: Baseline): void {
    this.baseline = baseline
  }

  addFrame(frame: Frame): void {
    this.advance(frame.t_ms)
    this.frames.push(frame)
  }

  addVoice(sample: VoiceSample): void {
    this.advance(sample.t_ms)
    this.voice.push(sample)
  }

  /** Emit the last, partly filled bin when the lesson ends. */
  flush(): void {
    if (this.frames.length || this.voice.length) this.emit()
  }

  private advance(t_ms: number): void {
    while (t_ms >= this.start + BIN_MS) this.emit()
  }

  private emit(): void {
    this.onBin(makeBin(this.start, this.frames, this.voice, this.baseline))
    this.frames = []
    this.voice = []
    this.start += BIN_MS
  }
}
