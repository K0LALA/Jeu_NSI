# POOcalypse

**POOCalypse** est un jeu 2D en vue de dessus dans lequel on incarne un personnage dont le but est de vaincre un méchant boss qui a fait du mal à son village.<br>
Le thème est medieval fantasy et le personnage navigue dans un monde post-apocalyptique, détruit par le méchant boss POO.<br>
En collectant des artefacts et de nouvelles technologies, il sera possible de vaincre des boss de plus en plus imposants, jusqu'à POO.....

## Lancer

Pour lancer via VSCode le projet, **dupliquez** (pas renommer) le fichier `launch.json.default` dans le dossier `.vscode` et enlevez l'extension *.default* sur ce second fichier.<br>
Dans l'onglet **Run And Debug**, choisir la bonne configuration, et lancer.<br>
Dans une console s'ouvre alors en mode interactif (on peut envoyer des commandes Python pendant qu'il s'exécute) le fichier `main.py`, point d'entrée du programme.<br>
Une fois fini, écrire dans la console stop(), qui fermera le serveur Web, une fois que le processus Python disparaît, on peut alors terminer la session de Degug avec *F8* ou en cliquant sur le carré rouge.<br>
Si vous voulez apporter des modifications aux configurations, modifiez dans `launch.json`, si vous pensez que ça peut être utile à tout le monde, ajoutez dans `launch.json.default` et publiez les changements.<br>

Pour lancer via la console simplement, exécuter cette commande en se situant dans le dossier `/src/` du projet, sinon adaptez la commande:
`PYTHONPATH=./libs/ python3 -i ./server/main.py`.<br>
Pour stopper le serveur, écrire la commande `stop()` dans le terminal intéractif et attendre que le processus Python soit fini, sinon les ports utilisés par le processus resteront utilisés et ne pourront pas être réutilisés.<br>


# Éditeur
## Commencer

Pour lancer l'éditeur il faut sélectionner la bonne configuration sur VSCode, en passant par le terminal, il faut exécuter le script `server/editor.py` au lieu de `server/main.py`.<br>
La première chose à faire une fois lancé, c'est sélectionner un monde en haut à droite, puis une couche sur laquelle on veut travailler.<br>
En selectionnant une couche, toutes les tiles disponibles s'affichent en bas, il est possible de les sélectionner puis de dessiner avec clic gauche ou effacer avec clic droit ou l'outil gomme.<br>

## Creation de monde

Si aucun monde n'a été créé il faut le faire manuellement en manipulant la base de données via sqlite3 par exemple.
La base de donnée se situe, par rapport à la racine du projet: `/src/content/data/worlds/worlds.db`.
Pour la modifier, il faut taper dans un terminal: `sqlite3 worlds.db`<br>
Ensuite, il faut ajouter un monde avec la commande: `INSERT INTO worlds VALUES (%NOM_DU_MONDE%);` et remplacer `%NOM_DU_MONDE%`.

## Ajout de couches

Si le monde vient d'être créé il n'a surement aucune couche, pour se faire il est possible de passer par sqlite3 ou par l'interface, il suffit de sélectionner les options souhaitées et cliquer sur le bouton **Ajouter**.
Si vous ne voyez pas la couche s'afficher dans la liste, c'est probablement qu'une autre couche est au même niveau, ce qui n'est pas permis.
Pour ajouter des collisions, il faut ajouter des couches spéciales, qui ne s'affichent que dans l'éditeur et non en jeu (comme les Barrier Block dans Minecraft)

## Suppression d'une couche

Pour supprimer une couche, il faut passer par sqlite3 et entrer la commande: `DELETE FROM layers WHERE world=%MONDE% AND layer_index=%NIVEAU_COUCHE%;` en veillant à remplacer `%MONDE%` et `%NIVEAU_COUCHE%`.
Néanmoins cela ne supprime pas le contenu de la couche concernée, c'est un problème car cela surcharge la base de données pour rien, donc il faut le supprimer.<br>
En commencant par les tiles: `DELETE FROM tiles WHERE block_id IN (SELECT block_id FROM blocks WHERE world=%MONDE% AND layer_index=%NIVEAU_COUCHE%);`, toujours en remplaçant `%MONDE%` et `%NIVEAU_COUCHE%`.<br>
Puis les blocks: `DELETE FROM blocks WHERE world=%MONDE% AND layer_index=%NIVEAU_COUCHE%);`.<br>

## Suppression de mondes

Pour supprimer un monde il faut supprimer toutes les couches, pour cela se référer à <a href="#suppression-dune-couche">la séction précédente</a> sans ajouter le paramètre `layer_index`.
Enfin, supprimer le monde lui-même avec `DELETE FROM worlds WHERE name=%MONDE%;`

## Outils

Il y a trois outils disponibles: le crayon, la gomme et la sélection

### Crayon

Permet de dessiner, il faut sélectionner une couche et une tile pour dessiner en utilisant le clic gauche.<br>
En utilisant le clic droit, il est possible d'effacer les tiles (gomme).

### Gomme

Permet de gommer, il faut sélectionner une couche, s'utilise avec le clic gauche

### Sélection

Permet de sélectionner une zone pour dessiner ou gommer.<br>
Pour sélectionner il faut 2 coins, le premier coin avec clic gauche et le deuxième avec clic droit.<br>
Puis pour dessiner, cliquer sur une tile avec une couche sélectionnée.<br>
Et pour gommer, cliquer sur la gomme, avec une couche sélectionnée.
