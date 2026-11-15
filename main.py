from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

DEFAULT_MODEL = "yolo26n.pt"
DEFAULT_HAZARD_LABELS = {
    "person",
    "bird",
    "cat",
    "dog",
    "horse",
    "sheep",
    "cow",
    "elephant",
    "bear",
    "zebra",
    "giraffe",
    "bicycle",
    "car",
    "motorcycle",
    "bus",
    "truck",
}
WINDOW_NAME = "Railway Track Obstacle Alert AI"


class HazardAlarm:
    """Repeat the five-second alarm while a stable obstacle remains detected."""

    def __init__(self, stable_frames: int, repeat_seconds: float) -> None:
        self.stable_frames = stable_frames
        self.repeat_seconds = repeat_seconds
        self.candidate: bool | None = None
        self.candidate_count = 0
        self.active: bool | None = None
        self.last_alert = 0.0

    def update(self, hazards: list[dict]) -> None:
        has_hazard = bool(hazards)
        if has_hazard == self.candidate:
            self.candidate_count += 1
        else:
            self.candidate = has_hazard
            self.candidate_count = 1

        if self.candidate_count < self.stable_frames:
            return

        now = time.monotonic()
        changed = has_hazard != self.active
        should_repeat = (
            has_hazard
            and not changed
            and self.repeat_seconds > 0
            and now - self.last_alert >= self.repeat_seconds
        )

        if has_hazard and (changed or should_repeat):
            labels = ", ".join(sorted({item["label"] for item in hazards}))
            print(f"ALERT: Obstacle in track zone: {labels}", flush=True)
            play_alarm()
            self.last_alert = now
        elif not has_hazard and changed and self.active is True:
            print("CLEAR: Track zone is clear", flush=True)
            stop_alarm()

        self.active = has_hazard


def play_alarm(*, wait_until_done: bool = False) -> None:
    """Play a five-second siren alarm on Windows, with a timed fallback."""
    if platform.system() == "Windows":
        import winsound

        alarm_file = Path(__file__).resolve().with_name("alarm.wav")
        if alarm_file.is_file():
            winsound.PlaySound(
                str(alarm_file),
                winsound.SND_FILENAME | winsound.SND_ASYNC,
            )
            if wait_until_done:
                time.sleep(5.0)
            return

        # Fallback pattern: 20 quarter-second tones total five seconds.
        for index in range(20):
            winsound.Beep(700 if index % 2 == 0 else 1250, 250)
        return

    # Most terminals render this as a bell; repeat for the requested duration.
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        print("\a", end="", flush=True)
        time.sleep(0.5)
def stop_alarm() -> None:
    """Stop an async Windows siren when the track zone clears."""
    if platform.system() == "Windows":
        import winsound

        winsound.PlaySound(None, 0)

def parse_source(value: str) -> int | str:
    return int(value) if value.isdecimal() else value


def pixel_polygon(points: list[list[float]], width: int, height: int) -> np.ndarray:
    pixels = [
        [round(x * (width - 1)), round(y * (height - 1))]
        for x, y in points
    ]
    return np.asarray(pixels, dtype=np.int32).reshape((-1, 1, 2))


def draw_track_zone(frame: np.ndarray, points: list[list[float]]) -> None:
    height, width = frame.shape[:2]
    polygon = pixel_polygon(points, width, height)
    cv2.polylines(frame, [polygon], True, (0, 210, 255), 3)


def select_track_zone(frame: np.ndarray) -> list[list[float]] | None:
    """Let the operator mark a polygon covering the visible railway track area."""
    height, width = frame.shape[:2]
    points: list[list[float]] = []

    def on_mouse(event, x, y, _flags, _param) -> None:
        if event == cv2.EVENT_LBUTTONDOWN:
            points.append([x / max(width - 1, 1), y / max(height - 1, 1)])
        elif event == cv2.EVENT_RBUTTONDOWN and points:
            points.pop()

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback(WINDOW_NAME, on_mouse)
    print(
        "Track-zone setup: left-click around the track area, right-click to undo, "
        "then press Enter to save (Esc cancels).",
        flush=True,
    )

    while True:
        preview = frame.copy()
        if points:
            polygon = pixel_polygon(points, width, height)
            for x, y in polygon.reshape((-1, 2)):
                cv2.circle(preview, (int(x), int(y)), 6, (0, 210, 255), -1)
            if len(points) >= 2:
                cv2.polylines(preview, [polygon], len(points) >= 3, (0, 210, 255), 2)
        cv2.putText(
            preview,
            "Click track boundary points | Enter: save | Right-click: undo | Esc: cancel",
            (18, 32),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        cv2.imshow(WINDOW_NAME, preview)
        key = cv2.waitKey(20) & 0xFF
        if key in (10, 13) and len(points) >= 3:
            cv2.destroyWindow(WINDOW_NAME)
            return points
        if key == 27:
            cv2.destroyWindow(WINDOW_NAME)
            return None


def load_track_zone(path: Path) -> list[list[float]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    points = data.get("points") if isinstance(data, dict) else None
    if not isinstance(points, list) or len(points) < 3:
        raise ValueError("track-zone file must contain at least three points")

    normalized: list[list[float]] = []
    for point in points:
        if not isinstance(point, list) or len(point) != 2:
            raise ValueError("each track-zone point must be [x, y]")
        x, y = float(point[0]), float(point[1])
        if not (0 <= x <= 1 and 0 <= y <= 1):
            raise ValueError("track-zone coordinates must be between 0 and 1")
        normalized.append([x, y])
    return normalized


def detect_hazards(result, track_zone: list[list[float]], hazard_labels: set[str]) -> list[dict]:
    hazards: list[dict] = []
    boxes = result.boxes
    if boxes is None or len(boxes) == 0:
        return hazards

    height, width = result.orig_shape
    contour = pixel_polygon(track_zone, width, height).astype(np.float32)
    names = result.names
    class_ids = boxes.cls.int().tolist()
    coordinates = boxes.xyxy.tolist()
    confidences = boxes.conf.tolist()

    for class_id, box, confidence in zip(class_ids, coordinates, confidences):
        label = str(names[class_id]).lower()
        if label not in hazard_labels:
            continue

        x1, y1, x2, y2 = box
        ground_contact = ((x1 + x2) / 2, y2)
        if cv2.pointPolygonTest(contour, ground_contact, False) >= 0:
            hazards.append(
                {
                    "label": label,
                    "confidence": float(confidence),
                    "box": [int(round(value)) for value in box],
                }
            )
    return hazards


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Alert when a person, animal, or vehicle is detected in a marked railway-track zone."
    )
    parser.add_argument(
        "--source",
        default="0",
        help="Webcam index (default: 0) or path to a video file.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Ultralytics detection weights (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--confidence",
        type=float,
        default=0.35,
        help="Minimum detection confidence from 0 to 1 (default: 0.35).",
    )
    parser.add_argument(
        "--stable-frames",
        type=int,
        default=5,
        help="Frames an obstacle must persist before alerting (default: 5).",
    )
    parser.add_argument(
        "--repeat-seconds",
        type=float,
        default=5,
        help="Repeat the five-second siren every N seconds while a hazard remains; default: 5.",
    )
    parser.add_argument(
        "--hazard-labels",
        default=",".join(sorted(DEFAULT_HAZARD_LABELS)),
        help="Comma-separated model labels that should trigger track-zone alerts.",
    )
    parser.add_argument(
        "--zone-file",
        default="track_zone.json",
        help="Saved track-zone polygon file (default: track_zone.json).",
    )
    parser.add_argument(
        "--set-zone",
        action="store_true",
        help="Redraw and save the track-zone polygon before detection starts.",
    )
    args = parser.parse_args()
    if not 0 < args.confidence <= 1:
        parser.error("--confidence must be greater than 0 and at most 1")
    if args.stable_frames < 1:
        parser.error("--stable-frames must be at least 1")
    if args.repeat_seconds < 0:
        parser.error("--repeat-seconds cannot be negative")
    args.hazard_labels = {
        label.strip().lower()
        for label in args.hazard_labels.split(",")
        if label.strip()
    }
    return args


def main() -> int:
    args = parse_args()
    source = parse_source(args.source)
    capture = cv2.VideoCapture(source)
    if not capture.isOpened():
        print(f"Could not open video source: {args.source}", file=sys.stderr)
        if isinstance(source, int):
            play_alarm(wait_until_done=True)
        return 1

    ok, first_frame = capture.read()
    if not ok:
        print(f"Could not read a frame from source: {args.source}", file=sys.stderr)
        if isinstance(source, int):
            play_alarm(wait_until_done=True)
        capture.release()
        return 1

    zone_path = Path(args.zone_file)
    try:
        if args.set_zone or not zone_path.exists():
            track_zone = select_track_zone(first_frame)
            if track_zone is None:
                print("Track-zone setup cancelled.", file=sys.stderr)
                capture.release()
                return 1
            zone_path.parent.mkdir(parents=True, exist_ok=True)
            zone_path.write_text(
                json.dumps({"points": track_zone}, indent=2),
                encoding="utf-8",
            )
            print(f"Saved track zone to {zone_path}", flush=True)
        else:
            track_zone = load_track_zone(zone_path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Could not load track zone ({zone_path}): {error}", file=sys.stderr)
        capture.release()
        return 1

    print(f"Loading AI model: {args.model}", flush=True)
    model = YOLO(args.model)
    alarm = HazardAlarm(args.stable_frames, args.repeat_seconds)
    print("Monitoring track zone. Press Q in the video window to quit.", flush=True)
    pending_frame: np.ndarray | None = first_frame

    try:
        while True:
            if pending_frame is not None:
                frame = pending_frame
                pending_frame = None
            else:
                ok, frame = capture.read()
                if not ok:
                    if isinstance(source, int):
                        print("Camera frame unavailable; sounding camera-loss alert.", file=sys.stderr)
                        play_alarm(wait_until_done=True)
                    break

            result = model(frame, conf=args.confidence, verbose=False)[0]
            hazards = detect_hazards(result, track_zone, args.hazard_labels)
            alarm.update(hazards)

            annotated = result.plot()
            draw_track_zone(annotated, track_zone)
            for item in hazards:
                x1, y1, x2, y2 = item["box"]
                label = f"TRACK HAZARD: {item['label']} {item['confidence']:.2f}"
                cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 255), 3)
                cv2.putText(
                    annotated,
                    label,
                    (x1, max(24, y1 - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (0, 0, 255),
                    2,
                    cv2.LINE_AA,
                )

            if hazards:
                names = ", ".join(sorted({item["label"] for item in hazards}))
                status = f"OBSTACLE IN TRACK ZONE: {names}"
                color = (0, 0, 255)
            else:
                status = "TRACK ZONE CLEAR"
                color = (40, 180, 40)
            cv2.putText(
                annotated,
                status[:90],
                (18, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                color,
                2,
                cv2.LINE_AA,
            )
            cv2.imshow(WINDOW_NAME, annotated)
            if cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q")):
                break
    except KeyboardInterrupt:
        print("Stopping detector...", flush=True)
    finally:
        capture.release()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())







