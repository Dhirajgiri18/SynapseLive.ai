# SynapseLive.ai

SynapseLive.ai is a Windows desktop meeting copilot. It captures microphone and speaker-loopback audio, transcribes locally with Faster-Whisper, and displays a live transcript and concise Gemini cues in an always-on-top overlay. It can also use project documents as local retrieval context and save meeting notes as Markdown.

## Features

- Separate microphone (`[You]`) and system-audio (`[Speaker]`) streams.
- Local speech recognition with RMS gating and filters for common silence hallucinations.
- A searchable local LanceDB index built from TXT, Markdown, and PDF files in `docs/`.
- Gemini cues for qualifying speaker questions, with model cooldowns and quota alerts.
- A draggable overlay with a minimized status pill, saved window position, and close confirmation.
- Markdown summaries saved under `notes/`; short transcripts are skipped, and daily-quota failures save the raw transcript instead.

## Requirements

- Windows 10 or 11.
- Python 3.11 recommended.
- A Gemini API key with access to the configured models. Usage is subject to the Google AI Studio project quota.
- A working microphone and a Windows output device that exposes loopback capture.

## Setup

Open Command Prompt in the project root and create the virtual environment:

```cmd
py -3.11 -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

In PowerShell, activate the environment with `./venv/Scripts/Activate.ps1` instead.

Create `local_secrets.py` in the project root and put your API key in it:

```python
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
```

Use a valid, private key. `local_secrets.py` is ignored by Git; do not force-add it or paste the key into source files. If a key was ever exposed, revoke it and use a replacement.

Add project notes to `docs/` as `.txt`, `.md`, or `.pdf`. The app indexes these files into a local LanceDB database at startup. The first run may download the sentence-transformer embedding model and the Faster-Whisper model.

## Run

Optional checks before starting the app:

```cmd
python tools\check_audio.py
python tools\test_quota_alert.py
```

`check_audio.py` lists the default devices and available loopback microphones; it does not record. The quota test uses a fake Gemini client and makes no API request.

To preview the UI without starting audio capture or calling any models:

```cmd
python tools\ui_preview.py
```

Start the live app from the project root:

```cmd
python main.py
```

The overlay appears at the bottom-right by default. It shows the transcript and cues, can be dragged and minimized to a pill, and remembers its position in `data/ui_state.json`. The save button ends audio capture and creates a Markdown note in `notes/`. Press `Ctrl+C` in the launching terminal to exit. A second launch is rejected while another instance holds the app lock.

For the first live test, use non-confidential audio. You can close the overlay with its close button; if a transcript is unsaved or a summary is running, it asks before discarding the meeting.

## Audio, API, and Local Data

Audio is captured from the default microphone and the default speaker's loopback device while the app is running. Speech recognition runs locally. Qualifying speaker questions are sent as text to Gemini for cues; clicking the save button sends the meeting transcript to Gemini for summarization. Check your organization's recording policies and local consent requirements before using it in a real meeting.

Documents and the LanceDB index stay on the local machine. Meeting notes, the database, overlay state, the virtual environment, and `local_secrets.py` are excluded by `.gitignore`. Do not commit meeting notes or credentials.

Cue requests use the configured cue model chain; summaries use a separate summary chain. If Gemini reports that all models in a chain have exhausted their daily quotas, the overlay shows a quota alert. A summary quota failure writes a raw transcript note so the meeting is not lost. Model and quota settings are in `config.py`.

## Troubleshooting

- **No speaker transcript:** Run `python tools\check_audio.py`, confirm audio is playing through the listed default speakers, and select the correct Windows output device.
- **No microphone transcript:** Confirm the default microphone in Windows and check that its audio level is not muted.
- **RMS messages are below `0.01`:** The temporary `[ASR] rms=` output shows the measured input level. Tune `MIN_RMS` in `config.py` between room-noise and normal-speech readings.
- **Daily quota alert:** The app skips quota-blocked models until their retry window expires. The alert links to Google's rate-limit information. Restarting the app clears the in-memory quota state; it does not reset Google's actual quota.
- **`ModuleNotFoundError`:** Activate the project virtual environment and install dependencies with `python -m pip install -r requirements.txt` from the project root.
- **Stale or off-screen overlay position:** Delete `data/ui_state.json`; the overlay will return to its default position.
