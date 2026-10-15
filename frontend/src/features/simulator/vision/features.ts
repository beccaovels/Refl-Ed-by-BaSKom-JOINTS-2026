// Pure functions from one frame to plain facts about it. No camera, no MediaPipe import,
// so every rule here can be unit-tested with made-up numbers.
//
// What is deliberately not here: eye contact, any emotion, and any score for lighting
// or camera quality. Brightness and face size only decide whether a frame can be trusted.

import type { Baseline, FaceShape, Frame, Point } from './types'

// Provisional until tuned on our labelled clips.
export const TURNED_AWAY_DEG = 35
export const LOOKING_AWAY_DEG = 30
export const SHOULDER_TILT_DEG = 12
export const SLOUCH_SHARE = 0.8 // nose this much lower than its calibrated height above the shoulders
export const HAND_SPEED = 0.5 // shoulder widths per second
export const TOO_DARK = 40 // average brightness, 0-255
export const TOO_SMALL = 0.08 // face width as a share of the picture
const SEEN = 0.5

export const NEUTRAL_FACE: FaceShape = { smile: 0, browUp: 0, browDown: 0, cheek: 0 }

/** Can this frame be trusted? If not, it is left out, never counted against the teacher. */
export function reliable(frame: Frame): boolean {
  if (frame.brightness < TOO_DARK) return false
  return frame.face === null || frame.face.size >= TOO_SMALL
}

/**
 * How far the face has moved from the teacher's own neutral face, 0-1.
 * A smile, raised or lowered brows and raised cheeks all count the same way: as movement.
 * Jaw movement is left out because talking alone would then look expressive.
 */
export function faceLiveliness(shape: FaceShape, neutral: FaceShape): number {
  const moved = Math.max(
    Math.abs(shape.smile - neutral.smile),
    Math.abs(shape.browUp - neutral.browUp),
    Math.abs(shape.browDown - neutral.browDown),
    Math.abs(shape.cheek - neutral.cheek),
  )
  return Math.min(Math.max(moved, 0), 1)
}

/** Turned toward the device, within a wide margin. Reading the shared slide still counts as facing. */
export function facing(face: NonNullable<Frame['face']>, baseline: Baseline): boolean {
  return (
    Math.abs(face.yaw - baseline.yaw) <= TURNED_AWAY_DEG && Math.abs(face.pitch - baseline.pitch) <= LOOKING_AWAY_DEG
  )
}

function distance(a: Point, b: Point): number {
  return Math.hypot(a.x - b.x, a.y - b.y)
}

function seen(...points: Point[]): boolean {
  return points.every((p) => (p.visibility ?? 1) >= SEEN)
}

/** Height of the nose above the shoulder line, in shoulder widths. Drops when slouching. */
export function uprightness(body: NonNullable<Frame['body']>): number | null {
  const width = distance(body.leftShoulder, body.rightShoulder)
  if (width === 0 || !seen(body.leftShoulder, body.rightShoulder, body.nose)) return null
  const shoulderY = (body.leftShoulder.y + body.rightShoulder.y) / 2
  return (shoulderY - body.nose.y) / width // y grows downward in the picture
}

/** Upright with level shoulders. Null when the shoulders are not in the picture. */
export function postureOk(body: NonNullable<Frame['body']>, baseline: Baseline): boolean | null {
  const height = uprightness(body)
  if (height === null) return null
  const dx = body.leftShoulder.x - body.rightShoulder.x
  const dy = body.leftShoulder.y - body.rightShoulder.y
  const tilt = Math.abs((Math.atan2(dy, Math.abs(dx)) * 180) / Math.PI)
  return tilt <= SHOULDER_TILT_DEG && height >= baseline.uprightness * SLOUCH_SHARE
}

/** Are the hands moving between two frames? Speed is measured in shoulder widths, so distance from the camera does not matter. */
export function handsMoving(previous: Frame['body'], current: Frame['body'], seconds: number): boolean {
  if (!previous || !current || seconds <= 0) return false
  const width = distance(current.leftShoulder, current.rightShoulder)
  if (width === 0) return false
  const speeds: number[] = []
  if (seen(previous.leftWrist, current.leftWrist)) speeds.push(distance(previous.leftWrist, current.leftWrist))
  if (seen(previous.rightWrist, current.rightWrist)) speeds.push(distance(previous.rightWrist, current.rightWrist))
  return speeds.some((moved) => moved / width / seconds >= HAND_SPEED)
}

/**
 * Head turn in degrees from MediaPipe's face transformation matrix (16 numbers, column by column).
 * Used only to notice being turned well away from the device.
 */
export function headAngles(matrix: ArrayLike<number>): { yaw: number; pitch: number } {
  const degrees = 180 / Math.PI
  return {
    yaw: Math.atan2(matrix[8], matrix[10]) * degrees,
    pitch: Math.asin(Math.max(-1, Math.min(1, -matrix[9]))) * degrees,
  }
}

/** The four face movements we read, from MediaPipe's list of named blendshapes. */
export function faceShape(blendshapes: ReadonlyArray<{ categoryName: string; score: number }>): FaceShape {
  const value = (name: string) => blendshapes.find((b) => b.categoryName === name)?.score ?? 0
  const mean = (...names: string[]) => names.reduce((sum, name) => sum + value(name), 0) / names.length
  return {
    smile: mean('mouthSmileLeft', 'mouthSmileRight'),
    browUp: mean('browInnerUp', 'browOuterUpLeft', 'browOuterUpRight'),
    browDown: mean('browDownLeft', 'browDownRight'),
    cheek: mean('cheekSquintLeft', 'cheekSquintRight'),
  }
}
