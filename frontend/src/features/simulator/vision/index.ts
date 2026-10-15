// The one entry point the Simulator Room needs:
//
//   const signals = await startSignals({ stream, video, now, onBin })
//   await signals.calibrate()          // three seconds, "sit how you teach"; optional
//   ...lesson...
//   signals.stop()
//
// `onBin` receives one Bin every ten seconds; the room sends them to POST /sessions/{id}/signals.
// Leave `video` out (camera off or denied) and bins carry voice only. If the camera models
// cannot load, it also carries on with voice only.

import { VoiceMeter } from './audioSignals'
import { Binner } from './binning'
import { baselineFrom, CALIBRATION_MS, DEFAULT_BASELINE } from './calibration'
import { Camera } from './camera'
import type { Baseline, Bin, Frame, VoiceSample } from './types'

export type { Baseline, Bin, Frame, VoiceSample } from './types'
export { BIN_MS } from './types'

export interface SignalOptions {
  /** The microphone stream (and camera, if on) from getUserMedia. */
  stream: MediaStream
  /** The <video> element showing the teacher's camera. Omit when the camera is off. */
  video?: HTMLVideoElement
  /** Milliseconds since the lesson started, the same clock the audio chunks use. */
  now: () => number
  onBin: (bin: Bin) => void
  /** Optional, for a live HUD. */
  onFrame?: (frame: Frame) => void
  onVoice?: (sample: VoiceSample) => void
}

export interface Signals {
  /** True when the camera is being read; false means voice only. */
  cameraOn: boolean
  /** Record the teacher's resting position for three seconds. Resolves with what was measured. */
  calibrate: () => Promise<Baseline>
  /** Stop reading and emit the last, partly filled bin. */
  stop: () => void
}

export async function startSignals(options: SignalOptions): Promise<Signals> {
  const binner = new Binner(DEFAULT_BASELINE, options.onBin)
  const voice = new VoiceMeter()
  let camera: Camera | null = null
  let calibrating: Frame[] | null = null

  if (options.video) {
    try {
      camera = new Camera()
      await camera.load()
    } catch (error) {
      console.warn('Camera signals are off; continuing with voice only.', error)
      camera = null
    }
  }

  if (options.stream.getAudioTracks().length > 0) {
    voice.start(options.stream, options.now, (sample) => {
      binner.addVoice(sample)
      options.onVoice?.(sample)
    })
  }
  if (camera && options.video) {
    camera.start(options.video, options.now, (frame) => {
      calibrating?.push(frame)
      binner.addFrame(frame)
      options.onFrame?.(frame)
    })
  }

  return {
    cameraOn: camera !== null,
    calibrate: () =>
      new Promise((resolve) => {
        calibrating = []
        setTimeout(() => {
          const baseline = baselineFrom(calibrating ?? [])
          calibrating = null
          binner.setBaseline(baseline)
          resolve(baseline)
        }, CALIBRATION_MS)
      }),
    stop: () => {
      voice.stop()
      camera?.close()
      binner.flush()
    },
  }
}
