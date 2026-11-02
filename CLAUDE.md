# Chaîne « psychologie de l'argent » — shorts vidéo

Shorts verticaux 9:16 (1080×1920, 30 i/s) montés en HTML avec HyperFrames. Un dossier par vidéo dans `videos/`.

## Conventions de la chaîne

- **Version française** : montants en euros (`1 240,00 €`), vouvoiement, voix off générée par l'utilisateur.
- **Version anglaise : toujours en dollars (`$1,240.00`, « a twenty-dollar bill »), jamais en euros.** Décision de l'utilisateur pour toutes les prochaines vidéos en anglais. Le script, les cartes, le relevé et la voix off doivent parler de dollars.
  - La vidéo `videos/carte-especes-en/` (première version anglaise) est restée en euros car elle était déjà faite : ne pas la prendre pour modèle sur ce point.
- L'utilisateur génère lui-même la voix off et me l'envoie (fichier `.wav`). Je fournis le texte du script.
- Chaque vidéo a aussi une fiche de publication (`Short_….md`) : titre, 5 titres alternatifs, description, hashtags, tags, au même format que `Short_33.md` fourni par l'utilisateur.

## Fabriquer une vidéo (dossier `videos/<nom>/`)

Tout le contenu est dans `plan.json` (séquences, icônes, poses, sons, caméra, chapitres). `build.py` génère `index.html` et `compositions/`. Le moteur le plus récent (multilingue) est celui de `videos/carte-especes-en/`.

1. Mettre la voix dans `assets/audio/voix.wav`, transcrire (Whisper local, ou Groq si l'utilisateur donne une clé) en `transcript.json` avec les mots horodatés.
2. Recaler les séquences et les poses de `plan.json` sur les mots de la voix.
3. `python3 -I make_video.py --skip-transcribe -o renders/<nom>.mp4` (construit, creuse la musique sous la voix, contrôle, rend).
4. Vérifier des images extraites du rendu, puis envoyer la vidéo à l'utilisateur.

Pour l'anglais, le plan utilise `"locale": {"lang": "en"}` : les préréglages de `build.py` donnent alors `$`, les séparateurs anglais et l'icône `dollar_banknote`. Dans les séquences, l'icône `money_note` désigne le billet de la devise de la langue.

## Pièges connus

- Lancer le rendu avec le chemin du projet : `npx hyperframes@0.8.177 render <dossier> -o <dossier>/renders/x.mp4`, sinon il ne trouve pas `index.html`.
- `renders/`, `node_modules/` et `.hyperframes/` ne sont pas versionnés : envoyer la vidéo à l'utilisateur avec SendUserFile.
- Ne jamais écrire une clé API dans le dépôt (la clé Groq se passe par la variable `GROQ_API_KEY`).
- Poses du personnage : `assets/poses/` (14 PNG transparents, même visage et mêmes vêtements). Icônes : Fluent Emoji 3D (MIT) dans `assets/icons/`.
- Les chiffres de l'étude du MIT (2001) sont à vérifier avant publication.
