# OWNER SHAKEDOWN INSTRUCTIONS — Acoustic Loop Test (OPTIONAL)

SHAKEDOWN_ONLY / NOT_PAPER_EVIDENCE

THIS IS ENGINEERING SHAKEDOWN DATA.
IT MUST NOT BE USED AS FINAL PAPER EVIDENCE.

No participants. No recruitment. ~5 minutes of your time. This checks ONLY
whether the benchmark timing machinery survives real speakers, a real room,
and a real recording device — it is not a benchmark run and produces no
paper numbers.

## What you need

- Any loudspeaker (PC speakers, phone at moderate volume).
- Any recording device (phone voice-memo app or camera).
- The file `experiments/applied_system/results/shakedown/media/playback_buffer_song_a.wav`
  (≈65.5 s: chirp → music → chirp).

## Steps (1–2 takes, no more)

1. Start recording.
2. Wait at least 5 seconds of silence.
3. Play the WAV file once, in full. Do not pause, do not adjust volume
   mid-playback.
4. Wait at least 5 seconds of silence.
5. Stop recording. Do not trim or edit the recording.
6. Save the recording (WAV if possible; any format ffmpeg reads is fine)
   as:

   `experiments/applied_system/results/shakedown/acoustic/<label>.wav`

   (create the `acoustic/` folder if missing; `<label>` = `take1`, `take2`, …)

7. Run, per take:

   ```
   .venv/Scripts/python.exe -m experiments.applied_system.acoustic_loop \
       --capture experiments/applied_system/results/shakedown/acoustic/take1.wav \
       --label take1
   ```

8. Paste the printed verdict back to the agent. That's all.

## What the verdicts mean

- `GT_OK` — marker ground truth survived the acoustic round trip.
- `GT_FAILED` — the capture is missing/unusable markers (e.g., volume too
  low, recording started after the first chirp finished). This is a useful
  shakedown finding, not a mistake on your part.
- `GT_DIRECT_DISAGREEMENT` — machinery inconsistency the agent must
  investigate before any pilot.

Do NOT do more than two takes; the point is machinery contact with reality,
not measurement.
