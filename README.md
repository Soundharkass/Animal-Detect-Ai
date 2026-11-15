# Railway Track Obstacle Alert

ஒரு Python AI prototype: webcam/video frame-ல் நீங்கள் குறிக்கும் railway track area-க்குள் மனிதர், விலங்கு அல்லது வாகனம் இருந்தால் audible alert தரும்.

## என்ன கண்டறியும்?

இயல்புநிலை model labels:

- மனிதர்: `person`
- பொதுவான விலங்குகள்: `bird`, `cat`, `dog`, `horse`, `sheep`, `cow`, `elephant`, `bear`, `zebra`, `giraffe`
- வாகனங்கள்: `bicycle`, `car`, `motorcycle`, `bus`, `truck`

`train` label இயல்புநிலை hazard பட்டியலில் இல்லை. வேறு வகை objects-ஐ சேர்க்க `--hazard-labels` option பயன்படுத்தவும்; அந்த label பயன்படுத்தும் model-ல் இருக்க வேண்டும். Pretrained model எல்லா animal species-ஐயும் அல்லது railway debris-ஐயும் கண்டறியும் என்று உத்தரவாதம் இல்லை.

## Track area-ஐ தேர்வு செய்தல்

முதல் இயக்கத்தில் video-வின் முதல் frame காட்டப்படும். Track பகுதியின் வெளிப்புற எல்லையைச் சுற்றி குறைந்தது 3 இடங்களில் left-click செய்து, Enter அழுத்தி save செய்யவும். Right-click கடைசி புள்ளியை நீக்கும்; Esc cancel செய்யும். Polygon `track_zone.json`-ல் சேமிக்கப்படும்; அடுத்த இயக்கங்களில் அதே camera view-க்கு மீண்டும் தேர்வு செய்யத் தேவையில்லை. Camera angle மாறினால் `--set-zone` மூலம் மறுபடியும் குறிக்கவும்.

Alert-க்கு object bounding box-ன் கீழ்-நடு புள்ளி அந்த polygon-க்குள் இருக்க வேண்டும். இது track பகுதியைக் குறிக்க உதவும் எளிய கணிப்பு; தனியாக ரயில் பாதையை அடையாளம் காணும் model அல்ல.

## Windows-ல் இயக்குவது

Terminal-ல் project folder-க்கு சென்று:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py --source 0
```

முன்பே சேமித்த camera view-க்கு பதிலாக video file பயன்படுத்த:

```powershell
python main.py --source "C:\Videos\track-sample.mp4"
```

Track polygon-ஐ மறுபடியும் அமைக்க:

```powershell
python main.py --source 0 --set-zone
```

Video window-ல் `Q` அழுத்தி நிறுத்தவும்.

## Alert நடத்தை மற்றும் settings

Track zone-க்குள் hazard 5 தொடர்ச்சியான frames-ல் கண்டறியப்பட்ட பிறகு 5-விநாடி siren ஒலிக்கும். Hazard தொடர்ந்து இருந்தால் siren ஒவ்வொரு 5 விநாடிக்கும் மீண்டும் ஒலிக்கும்; hazard மறைந்தது 5 frames உறுதியானதும் sound நிற்கும். ஒருமுறை மட்டும் ஒலிக்க `--repeat-seconds 0` பயன்படுத்தவும்.

Webcam திறக்க முடியாவிட்டாலும் அல்லது camera frame read வராமல் தோல்வியுற்றாலும் 5-விநாடி camera-loss alarm வரும். Video file இயல்பாக முடிவது camera failure என்று கருதப்படாது.

```powershell
python main.py --source 0 --confidence 0.4 --stable-frames 6 --repeat-seconds 10
```

| Option | Default | பயன்பாடு |
|---|---:|---|
| `--source` | `0` | Webcam எண் அல்லது video file path |
| `--model` | `yolo26n.pt` | YOLO detection weights/model file |
| `--confidence` | `0.35` | குறைந்த confidence detections-ஐ தவிர்க்கும் மதிப்பு |
| `--stable-frames` | `5` | alert-க்கு முன் hazard தொடர்ந்து இருக்க வேண்டிய frames |
| `--repeat-seconds` | `5` | active hazard siren மீண்டும் ஒலிக்கும் இடைவெளி; `0` என்றால் ஒருமுறை மட்டும் |
| `--hazard-labels` | `person,bird,cat,dog,horse,sheep,cow,elephant,bear,zebra,giraffe,bicycle,car,motorcycle,bus,truck` | alert தர வேண்டிய model labels |
| `--zone-file` | `track_zone.json` | track polygon சேமிக்கும்/படிக்கும் file |
| `--set-zone` | off | track polygon-ஐ மறுபடியும் வரையச் செய்கிறது |

உதாரணமாக `suitcase` மற்றும் `backpack`-ஐயும் சேர்க்க:

```powershell
python main.py --source 0 --hazard-labels "person,bird,cat,dog,horse,sheep,cow,elephant,bear,zebra,giraffe,bicycle,car,motorcycle,bus,truck,suitcase,backpack"
```

## முதல் இயக்கம்

`yolo26n.pt` model weights முதல் இயக்கத்தில் பதிவிறங்கலாம்; இணைய இணைப்பு தேவை. Packages `requirements.txt`-ல் உள்ளன.

## Railway பாதுகாப்பு குறிப்பு

இது prototype/demo மட்டுமே; தவறான alert அல்லது கண்டறியாத hazard ஏற்படலாம். இதை உண்மையான ரயில் இயக்கம், brake, signal அல்லது dispatch முடிவுகளுக்கு பயன்படுத்த வேண்டாம். Operational பயன்பாட்டிற்கு railway-specific data-வில் validation, fail-safe design, hardware integration மற்றும் உரிய railway safety approval தேவை.

## Project files

- `main.py` — video capture, zone selection, YOLO detection, overlay, alarm logic.
- `alarm.wav` — five-second siren audio played on Windows.
- `requirements.txt` — Python dependencies.
- `track_zone.json` — முதல் இயக்கத்தில் உருவாகும் camera-view polygon.







