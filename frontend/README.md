# Frontend

React 18 + Vite, plain JS/JSX, one CSS tree. Run: `npm install`, then `npm run dev` (http://localhost:5173). The dev server forwards `/api` to the backend on port 8000.

```
index.html              page title, fonts (Lora for headings, Plus Jakarta Sans for text), favicon
public/assets/          logo.svg and illustrations
src/
  main.jsx              entry point
  App.jsx               login gate, shared state (context), and the route table
  pages/                one file per screen: Login, Dashboard, Schedule, History, Performance, Report, Setup, DeviceCheck
  components/           pieces used by several pages: Shell (sidebar + top bar), Button, Empty, PageHeading, LessonFields, Reminder
  context/              AppContext: the saved reports/schedules store and the logged-in teacher
  hooks/                useDialogFocus (focus trap for dialogs), useSchedules
  lib/
    config.js           APP_NAME: the product name lives here only
    api.js              every call to the backend (see docs/api-contract.md)
    adapt.js            turns the backend report into what the Report page draws
    data.js             demo data, local storage, date helpers
    lesson.js           the lesson picked on Setup, lesson links, the saved draft
    device.js           the approved mic/camera stream shared across the flow
  features/
    setup/              MaterialUploader (PDF and picture upload on Setup)
    simulator/
      room/             Room (lesson logic) and its parts: RoomHeader, RoomAlerts, LessonStage, ChatPanel, RoomControls, RoomDialogs
      stage/            what the Room's main screen shows: PDF, picture, shared screen
      audio/            recorder.js: microphone to numbered audio pieces
      vision/           camera and voice signals (AI lead)
  styles/
    tokens.css          colours, fonts, radii: change the brand here
    index.css           imports the files below in cascade order
    base, layout, shell, components, login, dashboard, schedule, history, report, setup, room, responsive
```

Where to change things: colours and fonts in `styles/tokens.css`; text on a page in its file under `pages/`; the product name in `lib/config.js`.
