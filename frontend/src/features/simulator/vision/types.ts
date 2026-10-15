// Shapes shared by the signal code. `Bin` is the one in docs/api-contract.md.
// Only bins leave the browser: no frame, landmark or audio sample is ever uploaded.

export const BIN_MS = 10_000

/** Ten seconds of delivery signals, exactly as POST /sessions/{id}/signals expects them. */
export interface Bin {
  t_start_ms: number
  /** Share of the bin the head was turned toward the device, 0-1. Not eye contact. */
  facing_pct: number | null
  /** Share of the bin sitting upright with level shoulders, 0-1. */
  posture_ok_pct: number | null
  /** Share of the bin with the hands moving, 0-1. */
  gesture_rate: number | null
  /** How far the face moved from the teacher's own neutral face, 0-1. Never an emotion. */
  expressiveness: number | null
  /** Share of the bin with the face found, 0-1. */
  face_visible_pct: number | null
  /** Average loudness, 0-1. */
  volume: number | null
  /** Spread of the voice's pitch within the bin, in semitones. Null when nobody spoke. */
  pitch_variation: number | null
  /** False when the picture was too dark or the face too small to trust; never counted against the teacher. */
  measured: boolean
}

export interface Point {
  x: number
  y: number
  /** 0-1; how sure the model is that this point is in the picture. */
  visibility?: number
}

/** The few face movements we read, each 0-1, taken from MediaPipe blendshapes. */
export interface FaceShape {
  smile: number
  browUp: number
  browDown: number
  cheek: number
}

/** What one camera frame gives us, already reduced from landmarks to a handful of numbers. */
export interface Frame {
  t_ms: number
  /** Average brightness of the picture, 0-255. Used only to decide whether the frame can be trusted. */
  brightness: number
  face: {
    shape: FaceShape
    /** Head turn left-right and up-down, in degrees. */
    yaw: number
    pitch: number
    /** Width of the face as a share of the picture width. */
    size: number
  } | null
  body: {
    leftShoulder: Point
    rightShoulder: Point
    leftWrist: Point
    rightWrist: Point
    nose: Point
  } | null
}

/** The teacher's own resting values, from three seconds of sitting as they teach. */
export interface Baseline {
  shape: FaceShape
  yaw: number
  pitch: number
  /** Height of the nose above the shoulder line, in shoulder widths. */
  uprightness: number
}

/** What one reading of the microphone gives us. */
export interface VoiceSample {
  t_ms: number
  /** Loudness 0-1. */
  volume: number
  /** Pitch in hertz, or null when no voice was heard. */
  pitch: number | null
}
