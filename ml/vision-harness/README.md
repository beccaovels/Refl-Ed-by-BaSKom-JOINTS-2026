# Signal harness

A small standalone project for the voice and camera signal code in `frontend/src/features/simulator/vision/`. It exists because that code was written before the frontend project was scaffolded: this gives it a typecheck, unit tests and a page to try it on.

```
cd ml/vision-harness
npm install
npm run check     # typecheck + unit tests + build
npm run dev       # http://localhost:5174
```

If `npm install` fails on Windows with "'node' is not recognized", run `npm install --ignore-scripts` and then `node node_modules/esbuild/install.js`.

## The page

- **Start camera + microphone**: live signals. If the camera is refused, it carries on with the microphone.
- **Start microphone only**: the camera-off path.
- **Replay a clip**: runs the same code on a recorded video or audio file, using the clip's own timeline.
- **Calibrate (3 s)**: sit how you teach; later measures are compared with this.
- **Download bins (JSON)**: the rows in the table, exactly as the room would send them.

The Network tab shows only the one-time download of the MediaPipe models. No frame or sound is uploaded.

## Labelling clips for tuning

1. Record pairs: the same 30–40 s passage delivered once flat and once lively. Vary the person, light, glasses, hijab, laptop.
2. Replay each clip here and download its bins into `ml/eval/clips/` (git-ignored).
3. Label each 10 s as flat or lively, by ear and eye, without looking at the numbers.
4. The thresholds in `backend/app/services/delivery.py` and `features.ts` are set from half the clips and reported on the other half.

When the frontend exists, its own `npm run check` should cover the vision folder and this project can go.
