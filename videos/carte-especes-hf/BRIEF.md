---
workflow: general-video
flow: automation
storyboard: no
message: "On dépense plus avec la carte parce que la douleur de payer disparaît"
destination: shorts
aspect: 1080x1920
language: fr
length: 61s
---

## Intent

Short vertical pour une chaîne sur la psychologie de l'argent. Style inspiré des
vidéos de référence : personnage à gauche, cartes UI à droite, bandeau en haut,
sous-titres mot par mot.

## Assets

- assets/audio/voix.wav — voix off générée par l'utilisateur (61,16 s)
- transcript.json — transcription Groq whisper-large-v3, timings mot par mot
- assets/poses/*.png — 14 poses du personnage, fond transparent

## Notes

- index.html est généré : modifier src/template.html ou build.py, puis `python3 -I build.py`.
- Vérifier le chiffre de l'étude MIT 2001 (« près du double ») avant publication.
