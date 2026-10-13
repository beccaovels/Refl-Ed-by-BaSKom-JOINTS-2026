import { describe, expect, it } from 'vitest'

import { baselineFrom, DEFAULT_BASELINE } from '@vision/calibration'
import { faceLiveliness, faceShape, facing, handsMoving, headAngles, NEUTRAL_FACE, postureOk, reliable, uprightness } from '@vision/features'
import type { Baseline, Frame } from '@vision/types'

const baseline: Baseline = { shape: NEUTRAL_FACE, yaw: 0, pitch: 0, uprightness: 0.9 }

// A person sitting upright: shoulders level at y = 0.6, 0.4 of the picture apart, nose 0.36 above them.
function body(overrides: Partial<NonNullable<Frame['body']>> = {}): NonNullable<Frame['body']> {
  return {
    leftShoulder: { x: 0.7, y: 0.6, visibility: 0.9 },
    rightShoulder: { x: 0.3, y: 0.6, visibility: 0.9 },
    leftWrist: { x: 0.7, y: 0.9, visibility: 0.9 },
    rightWrist: { x: 0.3, y: 0.9, visibility: 0.9 },
    nose: { x: 0.5, y: 0.24, visibility: 0.9 },
    ...overrides,
  }
}

function frame(overrides: Partial<Frame> = {}): Frame {
  return { t_ms: 0, brightness: 120, face: { shape: NEUTRAL_FACE, yaw: 0, pitch: 0, size: 0.25 }, body: body(), ...overrides }
}

describe('face', () => {
  it('measures movement from the teacher\'s own neutral face, not from zero', () => {
    const restingSmile = { ...NEUTRAL_FACE, smile: 0.4 } // some faces rest in a slight smile
    expect(faceLiveliness(restingSmile, restingSmile)).toBe(0)
    expect(faceLiveliness({ ...restingSmile, smile: 0.7 }, restingSmile)).toBeCloseTo(0.3)
  })

  it('counts raised brows as much as a smile: a serious face can be lively', () => {
    expect(faceLiveliness({ ...NEUTRAL_FACE, browUp: 0.3 }, NEUTRAL_FACE)).toBeCloseTo(0.3)
    expect(faceLiveliness({ ...NEUTRAL_FACE, browDown: 0.3 }, NEUTRAL_FACE)).toBeCloseTo(0.3)
  })

  it('reads the four movements from named blendshapes and ignores the jaw', () => {
    const shape = faceShape([
      { categoryName: 'mouthSmileLeft', score: 0.6 },
      { categoryName: 'mouthSmileRight', score: 0.4 },
      { categoryName: 'jawOpen', score: 0.9 }, // talking
    ])
    expect(shape).toEqual({ smile: 0.5, browUp: 0, browDown: 0, cheek: 0 })
  })

  it('treats reading the slide as facing, and only a big turn as turned away', () => {
    const face = { shape: NEUTRAL_FACE, yaw: 0, pitch: 0, size: 0.25 }
    expect(facing({ ...face, yaw: 20, pitch: -15 }, baseline)).toBe(true)
    expect(facing({ ...face, yaw: 50 }, baseline)).toBe(false)
  })

  it('gets head turn in degrees from the transformation matrix', () => {
    const turn = (30 * Math.PI) / 180
    const matrix = [Math.cos(turn), 0, -Math.sin(turn), 0, 0, 1, 0, 0, Math.sin(turn), 0, Math.cos(turn), 0, 0, 0, 0, 1]
    expect(headAngles(matrix).yaw).toBeCloseTo(30)
    expect(headAngles(matrix).pitch).toBeCloseTo(0)
  })
})

describe('body', () => {
  it('accepts an upright, level sitting position', () => {
    expect(uprightness(body())).toBeCloseTo(0.9)
    expect(postureOk(body(), baseline)).toBe(true)
  })

  it('notices a slouch: the nose sinks toward the shoulders', () => {
    expect(postureOk(body({ nose: { x: 0.5, y: 0.4, visibility: 0.9 } }), baseline)).toBe(false)
  })

  it('notices tilted shoulders', () => {
    expect(postureOk(body({ leftShoulder: { x: 0.7, y: 0.75, visibility: 0.9 } }), baseline)).toBe(false)
  })

  it('says nothing when the shoulders are out of the picture', () => {
    expect(postureOk(body({ leftShoulder: { x: 0.7, y: 0.6, visibility: 0.1 } }), baseline)).toBeNull()
  })

  it('sees hands moving in shoulder widths, so distance from the camera does not matter', () => {
    const still = body()
    const waved = body({ leftWrist: { x: 0.6, y: 0.8, visibility: 0.9 } }) // 0.14 of the picture = 0.35 shoulder widths
    expect(handsMoving(still, waved, 0.2)).toBe(true) // in 0.2 s: 1.8 widths a second
    expect(handsMoving(still, still, 0.2)).toBe(false)
    expect(handsMoving(still, body({ leftWrist: { x: 0.6, y: 0.8, visibility: 0.1 } }), 0.2)).toBe(false) // hand not seen
  })
})

describe('what is never scored', () => {
  it('marks a dark frame or a tiny face as unreliable instead of judging it', () => {
    expect(reliable(frame())).toBe(true)
    expect(reliable(frame({ brightness: 20 }))).toBe(false)
    expect(reliable(frame({ face: { shape: NEUTRAL_FACE, yaw: 0, pitch: 0, size: 0.03 } }))).toBe(false)
    expect(reliable(frame({ face: null }))).toBe(true) // out of frame is a fact, not a bad picture
  })
})

describe('calibration', () => {
  it('takes the middle value, so one glance away does not shift the baseline', () => {
    const resting = { shape: { ...NEUTRAL_FACE, smile: 0.2 }, yaw: 5, pitch: -8, size: 0.25 }
    const frames = [frame({ face: resting }), frame({ face: resting }), frame({ face: { ...resting, yaw: 60 } })]
    const measured = baselineFrom(frames)
    expect(measured.yaw).toBe(5)
    expect(measured.shape.smile).toBeCloseTo(0.2)
    expect(measured.uprightness).toBeCloseTo(0.9)
  })

  it('falls back to a typical position when the camera saw nobody', () => {
    expect(baselineFrom([frame({ face: null, body: null })])).toEqual(DEFAULT_BASELINE)
  })
})
