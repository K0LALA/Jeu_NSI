# Structure base de données

Tous les mondes sont stockées dans la même base de données, `mondes.db`

Une première table `worlds` stocke les différents mondes:

```SQL
CREATE TABLE worlds (
    name VARCHAR PRIMARY KEY,
    origin_x INTEGER, -- Les coordonées de la tile qui
    origin_y INTEGER, -- doit être chargée au centre 
);
```

On crée aussi une table `layers` qui contient les couches de chaque monde :
```SQL
CREATE TABLE layers (
    world VARCHAR,
    layer_index INT,
    tileset TEXT, -- Chemin vers le dossier des images, exemple: "exterior", pour "/content/assets/tileset/exterior/"
    tiles_size INT,
    collisions BOOLEAN,
    PRIMARY KEY (world, layer_index)
);
```

Puis une autre table qui stocke des `blocks`, regroupement de `tiles`, `NPCs` et `ennemies` pour un affichage moins lourd et plus progressif.

```SQL
CREATE TABLE blocks (
    block_id INTEGER PRIMARY KEY AUTOINCREMENT,
    block_x INT,
    block_y INT,
    world VARCHAR,
    layer_index INT,
    FOREIGN KEY (world, layer_index) REFERENCES layers(world, layer_index)
);
```

Puis les autres tables: 

```SQL
CREATE TABLE tiles (
    block_id INT,
    x INT,
    y INT,
    PRIMARY KEY (block_id, x, y),
    image_name TEXT, -- Par exemple: "interior_001.png", pour récupérer le fichier image: layer.tileset + image_name
    FOREIGN KEY (block_id) REFERENCES blocks(block_id)
);

CREATE TABLE NPCs (
    npc_id INTEGER PRIMARY KEY AUTOINCREMENT,
    block_id INT,
    x INT,
    y INT,
    npc_name VARCHAR, -- On suppose pour l'instant que les dialogues sont récupérés par rapport au nom des NPC, chaque nom étant donc unique
    npc_image TEXT,
    FOREIGN KEY (block_id) REFERENCES blocks(block_id)
);

CREATE TABLE enemies (
    enemy_id INTEGER PRIMARY KEY AUTOINCREMENT,
    block_id INT,
    x INT,
    y INT,
    enemy_type VARCHAR, -- Suppose qu'il existe une table avec les types d'ennemis et leurs attributs
    FOREIGN KEY (block_id) REFERENCES blocks(block_id)
);

CREATE TABLE waypoints (
    waypoint_id INTEGER PRIMARY KEY AUTOINCREMENT,
    block_id INT,
    x INT,
    y INT,
    destination TEXT,
    FOREIGN KEY (block_id) REFERENCES blocks(block_id)
);
```