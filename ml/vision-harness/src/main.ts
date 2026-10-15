// A plain page for trying the signal code with a webcam, a microphone or a recorded clip.
// It is also the labelling tool: replay a clip, download its bins, and label each ten seconds.

import { faceLiveliness, facing, postureOk, reliable } from '@vision/features'
import { DEFAULT_BASELINE } from '@vision/calibration'
import { startSignals } from '@vision/index'
import type { Baseline, Bin, Frame, Signals, VoiceSample } from '@vision/index'

function element<T extends HTMLElement>(id: string): T {
  return document.getElementById(id) as T
}

const video = element<HTMLVideoElement>('video')
const hud = element<HTMLDivElement>('hud')
const status = element<HTMLDivElement>('status')
const rows = element<HTMLTableSectionElement>('bins')
const buttons = {
  webcam: element<HTMLButtonElement>('webcam'),
  micOnly: element<HTMLButtonElement>('micOnly'),
  calibrate: element<HTMLButtonElement>('calibrate'),
  stop: element<HTMLButtonElement>('stop'),
  export: element<HTMLButtonElement>('export'),
}
const clipInput = element<HTMLInputElement>('clip')

let signals: Signals | null = null
let stream: MediaStream | null = null
let baseline: Baseline = DEFAULT_BASELINE
let bins: Bin[] = []
let lastFrame: Frame | null = null
let lastVoice: VoiceSample | null = null
let clipName = 'live'

const show = (value: number | null, digits = 2) => (value === null ? '-' : value.toFixed(digits))
const clock = (ms: number) => `${String(Math.floor(ms / 60_000)).padStart(2, '0')}:${String(Math.floor(ms / 1000) % 60).padStart(2, '0')}`

function drawHud(): void {
  const lines: string[] = []
  if (lastFrame) {
    const { face, body } = lastFrame
    lines.push(`picture     ${reliable(lastFrame) ? 'usable' : 'too dark or too far: not measured'}  (brightness ${lastFrame.brightness.toFixed(0)})`)
    lines.push(`face        ${face ? `seen, ${facing(face, baseline) ? 'facing' : 'turned away'}` : 'not in frame'}`)
    lines.push(`liveliness  ${face ? faceLiveliness(face.shape, baseline.shape).toFixed(2) : '-'}   (movement from your neutral face)`)
    const posture = body ? postureOk(body, baseline) : null
    lines.push(`posture     ${posture === null ? 'shoulders not seen' : posture ? 'upright' : 'slouched or tilted'}`)
  } else {
    lines.push('camera      off')
  }
  if (lastVoice) {
    lines.push(`volume      ${'#'.repeat(Math.round(lastVoice.volume * 20)).padEnd(20, '.')} ${lastVoice.volume.toFixed(2)}`)
    lines.push(`pitch       ${lastVoice.pitch === null ? 'no voice' : `${lastVoice.pitch.toFixed(0)} Hz`}`)
  }
  hud.textContent = lines.join('\n')
}

function addRow(bin: Bin): void {
  bins.push(bin)
  const row = rows.insertRow()
  if (!bin.measured) row.className = 'unmeasured'
  const cells = [
    clock(bin.t_start_ms), bin.measured ? 'yes' : 'no', show(bin.face_visible_pct), show(bin.facing_pct), show(bin.posture_ok_pct),
    show(bin.gesture_rate), show(bin.expressiveness), show(bin.volume), show(bin.pitch_variation, 1),
  ]
  for (const text of cells) row.insertCell().textContent = text
  buttons.export.disabled = false
}

async function run(source: MediaStream, withCamera: boolean, now: () => number): Promise<void> {
  bins = []
  rows.replaceChildren()
  lastFrame = lastVoice = null
  baseline = DEFAULT_BASELINE
  status.textContent = withCamera ? 'Loading the camera models (a few seconds the first time)...' : 'Listening.'
  signals = await startSignals({
    stream: source,
    video: withCamera ? video : undefined,
    now,
    onBin: addRow,
    onFrame: (frame) => {
      lastFrame = frame
      drawHud()
    },
    onVoice: (sample) => {
      lastVoice = sample
      drawHud()
    },
  })
  status.textContent = signals.cameraOn ? 'Running: camera and voice.' : 'Running: voice only.'
  buttons.calibrate.disabled = !signals.cameraOn
  buttons.stop.disabled = false
}

function stop(): void {
  signals?.stop()
  signals = null
  stream?.getTracks().forEach((track) => track.stop())
  stream = null
  video.pause()
  buttons.calibrate.disabled = buttons.stop.disabled = true
  status.textContent = `Stopped. ${bins.length} bins.`
}

async function live(withCamera: boolean): Promise<void> {
  stop()
  clipName = 'live'
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: withCamera })
  } catch {
    if (!withCamera) {
      status.textContent = 'The microphone is needed. Allow it in the browser and try again.'
      return
    }
    // Camera denied: carry on with the microphone alone.
    stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    withCamera = false
  }
  video.className = ''
  video.srcObject = withCamera ? stream : null
  const began = performance.now()
  await run(stream, withCamera, () => performance.now() - began)
}

buttons.webcam.onclick = () => void live(true)
buttons.micOnly.onclick = () => void live(false)
buttons.stop.onclick = stop

buttons.calibrate.onclick = async () => {
  if (!signals) return
  status.textContent = 'Calibrating: sit how you teach and look at the screen...'
  baseline = await signals.calibrate()
  status.textContent = 'Calibrated. Running: camera and voice.'
}

clipInput.onchange = async () => {
  const file = clipInput.files?.[0]
  if (!file) return
  stop()
  clipName = file.name.replace(/\.[^.]+$/, '')
  video.className = 'clip'
  video.srcObject = null
  video.src = URL.createObjectURL(file)
  video.muted = false
  await video.play()
  // The clip's own sound track feeds the voice signals; its timeline is the lesson clock.
  const captured = (video as HTMLVideoElement & { captureStream(): MediaStream }).captureStream()
  video.onended = stop
  await run(captured, file.type.startsWith('video/'), () => video.currentTime * 1000)
}

buttons.export.onclick = () => {
  const link = document.createElement('a')
  link.href = URL.createObjectURL(new Blob([JSON.stringify({ clip: clipName, bins }, null, 2)], { type: 'application/json' }))
  link.download = `${clipName}-bins.json`
  link.click()
}
