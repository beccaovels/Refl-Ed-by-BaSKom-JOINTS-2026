// Reads the teacher's camera with MediaPipe's pretrained face and pose models and reduces
// each frame to the handful of numbers in `Frame`. Runs entirely in the browser: the models
// are downloaded once, and no picture is sent anywhere.

import { FaceLandmarker, FilesetResolver, PoseLandmarker } from '@mediapipe/tasks-vision'

import { faceShape, headAngles } from './features'
import type { Frame, Point } from './types'

// The wasm files must match the installed @mediapipe/tasks-vision version.
const WASM = 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm'
const FACE_MODEL =
  'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task'
const POSE_MODEL =
  'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task'

const NORMAL_EVERY_MS = 200 // about 5 frames a second
const SLOW_EVERY_MS = 500 // 2 frames a second on a device that cannot keep up
const SLOW_FRAME_MS = 150 // a frame taking longer than this means the device is struggling

// Pose landmark numbers, from MediaPipe's fixed list of 33 body points.
const NOSE = 0
const LEFT_SHOULDER = 11
const RIGHT_SHOULDER = 12
const LEFT_WRIST = 15
const RIGHT_WRIST = 16

export class Camera {
  private face: FaceLandmarker | null = null
  private pose: PoseLandmarker | null = null
  private timer: ReturnType<typeof setTimeout> | null = null
  private everyMs = NORMAL_EVERY_MS
  private canvas = document.createElement('canvas')

  /** Download and start the two models. Call once; takes a few seconds on first use. */
  async load(): Promise<void> {
    const files = await FilesetResolver.forVisionTasks(WASM)
    this.face = await FaceLandmarker.createFromOptions(files, {
      baseOptions: { modelAssetPath: FACE_MODEL },
      runningMode: 'VIDEO',
      numFaces: 1,
      outputFaceBlendshapes: true,
      outputFacialTransformationMatrixes: true,
    })
    this.pose = await PoseLandmarker.createFromOptions(files, {
      baseOptions: { modelAssetPath: POSE_MODEL },
      runningMode: 'VIDEO',
      numPoses: 1,
    })
    this.canvas.width = 32
    this.canvas.height = 18
  }

  /** Read frames from `video` until `stop()`. `now` returns milliseconds since the lesson started. */
  start(video: HTMLVideoElement, now: () => number, onFrame: (frame: Frame) => void): void {
    const tick = () => {
      const began = performance.now()
      if (video.readyState >= 2 && video.videoWidth > 0) onFrame(this.read(video, now()))
      // Weak laptop: drop to 2 frames a second rather than slow the lesson down.
      if (performance.now() - began > SLOW_FRAME_MS) this.everyMs = SLOW_EVERY_MS
      this.timer = setTimeout(tick, this.everyMs)
    }
    tick()
  }

  stop(): void {
    if (this.timer !== null) clearTimeout(this.timer)
    this.timer = null
  }

  close(): void {
    this.stop()
    this.face?.close()
    this.pose?.close()
  }

  /** Frames per second currently being read, for the HUD. */
  get rate(): number {
    return 1000 / this.everyMs
  }

  private read(video: HTMLVideoElement, t_ms: number): Frame {
    const stamp = performance.now()
    const faces = this.face?.detectForVideo(video, stamp)
    const poses = this.pose?.detectForVideo(video, stamp)

    let face: Frame['face'] = null
    const landmarks = faces?.faceLandmarks[0]
    if (faces && landmarks) {
      const xs = landmarks.map((p) => p.x)
      const matrix = faces.facialTransformationMatrixes[0]?.data
      face = {
        shape: faceShape(faces.faceBlendshapes[0]?.categories ?? []),
        ...(matrix ? headAngles(matrix) : { yaw: 0, pitch: 0 }),
        size: Math.max(...xs) - Math.min(...xs),
      }
    }

    let body: Frame['body'] = null
    const points = poses?.landmarks[0]
    if (points) {
      const at = (i: number): Point => ({ x: points[i].x, y: points[i].y, visibility: points[i].visibility })
      body = {
        nose: at(NOSE),
        leftShoulder: at(LEFT_SHOULDER),
        rightShoulder: at(RIGHT_SHOULDER),
        leftWrist: at(LEFT_WRIST),
        rightWrist: at(RIGHT_WRIST),
      }
    }
    return { t_ms, brightness: this.brightness(video), face, body }
  }

  /** Average brightness of the picture, 0-255, from a thumbnail. Only used to mark dark stretches "not measured". */
  private brightness(video: HTMLVideoElement): number {
    const context = this.canvas.getContext('2d', { willReadFrequently: true })
    if (!context) return 255
    context.drawImage(video, 0, 0, this.canvas.width, this.canvas.height)
    const pixels = context.getImageData(0, 0, this.canvas.width, this.canvas.height).data
    let sum = 0
    for (let i = 0; i < pixels.length; i += 4) sum += 0.299 * pixels[i] + 0.587 * pixels[i + 1] + 0.114 * pixels[i + 2]
    return sum / (pixels.length / 4)
  }
}
