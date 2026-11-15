# Railway Track Obstacle Alert

A Python AI prototype that triggers an audible alert if a person, animal, or vehicle is detected within a specified railway track area in a webcam feed or video frame.

## What can it detect?

Default model labels:

- Humans: `person`
- Common animals: `bird`, `cat`, `dog`, `horse`, `sheep`, `cow`, `elephant`, `bear`, `zebra`, `giraffe`
- Vehicles: `bicycle`, `car`, `motorcycle`, `bus`, `truck`

The `train` label is not included in the default hazard list. To add other types of objects, use the `--hazard-labels` option; note that the chosen label must exist within the model being used. There is no guarantee that the pre-trained model will detect every animal species or all types of railway debris.

## Defining the track area

Upon the first run, the initial frame of the video will be displayed. Left-click at least three times around the outer boundary of the track area, then press Enter to save. Right-clicking removes the most recently added point, while pressing Esc cancels the operation. The polygon is saved in `track_zone.json`; you do not need to redefine it for subsequent runs, provided the camera view remains the same. If the camera angle changes, use the `--set-zone` option to redefine the area.

For an alert to be triggered, the bottom-center point of an object's bounding box must fall within the defined polygon. This is a simplified heuristic for identifying the track zone; it is not a dedicated model for detecting railway tracks themselves. ## Running on Windows

Navigate to the project folder in the Terminal and execute:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py --source 0
```

To use a video file instead of the live camera feed:

```powershell
python main.py --source "C:\Videos\track-sample.mp4"
```

To reconfigure the track polygon (zone):

```powershell
python main.py --source 0 --set-zone
```

Press `Q` in the video window to stop the program.

## Alert Behavior and Settings

If a hazard is detected within the track zone for 5 consecutive frames, a 5-second siren will sound. If the hazard persists, the siren will repeat every 5 seconds; the sound will stop once the hazard has been absent for 5 consecutive frames. Use `--repeat-seconds 0` to have the alert sound only once.

If the webcam fails to open or if the system cannot read a camera frame, a 5-second "camera-loss" alarm will trigger. The natural end of a video file is not considered a camera failure.

```powershell
python main.py --source 0 --confidence 0.4 --stable-frames 6 --repeat-seconds 10
```

| Option | Default | Usage |
|---|---:|---|
| `--source` | `0` | Webcam index or path to a video file |
| `--model` | `yolo26n.pt` | YOLO detection weights/model file |
| `--confidence` | `0.35` | Threshold to filter out low-confidence detections |
| `--stable-frames` | `5` | Number of consecutive frames a hazard must be present to trigger an alert |
| `--repeat-seconds` | `5` | Interval at which the siren repeats for an active hazard | `0` indicates a single instance (e.g., the first available camera) |
| `--hazard-labels` | `person,bird,cat,dog,horse,sheep,cow,elephant,bear,zebra,giraffe,bicycle,car,motorcycle,bus,truck` | Model labels that should trigger an alert |
| `--zone-file` | `track_zone.json` | File used to save/load the track polygon |
| `--set-zone` | off | Allows for re-drawing the track polygon |

For example, to include `suitcase` and `backpack` as well:

```powershell
python main.py --source 0 --hazard-labels "person,bird,cat,dog,horse,sheep,cow,elephant,bear,zebra,giraffe,bicycle,car,motorcycle,bus,truck,suitcase,backpack"
```

## Initial Run

The `yolo26n.pt` model weights may be downloaded during the first run; an internet connection is required. Dependencies are listed in `requirements.txt`.

## Railway Safety Note

This is a prototype/demo only; false alerts or missed hazards may occur. Do not use this for actual railway operations, braking, signaling, or dispatch decisions. Operational use requires validation on railway-specific data, fail-safe design, hardware integration, and appropriate railway safety approvals.

## Project Files

- `main.py` — Handles video capture, zone selection, YOLO detection, visual overlays, and alarm logic.
- `alarm.wav` — A five-second siren audio file (played on Windows).
- `requirements.txt` — Python dependencies.
- `track_zone.json` — The camera-view polygon, generated during the first run.
