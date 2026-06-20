# Images du site TravelMind

Déposez les fichiers dans CE dossier (`frontend/public/images/`) avec EXACTEMENT ces noms.
Tant qu'un fichier manque, le site affiche automatiquement une photo de remplacement,
rien ne casse. Dès que le fichier est présent, il est utilisé tel quel.

| Fichier            | Format conseillé      | Contenu à chercher |
|--------------------|-----------------------|--------------------|
| `hero-main.jpg`    | Portrait 4:5, ≥ 960×1200  | Grande photo d'accueil : voyageur ou voyageuse de dos face à une vieille ville ou un panorama au coucher du soleil. Tons chauds (orangés) avec de la végétation ou des toits, lumière dorée. C'est LA photo du site. |
| `hero-detail.jpg`  | Carré, ≥ 640×640      | Petit visuel qui chevauche la grande photo : détail de préparation de voyage vu de dessus (carnet ouvert, billets d'avion, appareil photo, café sur une table en bois). |
| `dest-tokyo.jpg`   | Portrait 3:4, ≥ 900×1100 | Tokyo : croisement de Shibuya de nuit, ou temple Senso-ji avec lanternes, ou ruelle aux néons. Carte la plus grande de la galerie. |
| `dest-paris.jpg`   | Paysage ou portrait, ≥ 900×700 | Paris : toits haussmanniens au lever du soleil, ou la Seine avec la tour Eiffel au loin. |
| `dest-marrakech.jpg` | Paysage ou portrait, ≥ 900×700 | Marrakech : médina aux murs terracotta, souk coloré ou riad. Les tons orangés s'accordent avec la palette du site. |
| `dest-lisbonne.jpg`  | Paysage large, ≥ 1400×700 | Lisbonne : tram jaune dans une rue en pente, ou azulejos, ou miradouro sur les toits. Cette carte est large (elle occupe 2 colonnes). |
| `agent-cote.jpg`   | Portrait 4:5, ≥ 900×1100 | Section sombre « l'agent » : vue aérienne (drone) d'un littoral, d'une route côtière ou d'une forêt traversée par une route. Doit rester lisible avec du texte clair autour. |

Conseils :
- JPG qualité 80 suffit, viser moins de 400 Ko par image (https://squoosh.app pour compresser).
- Sources libres : unsplash.com, pexels.com.
- Les images de la page Explorer viennent de la base de données (`image_url`), pas de ce dossier.
