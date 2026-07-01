La table `characters.db` donne les attributs des différents personnages du jeu, qu'ils soient le joueur, des ennemis ou des PNJ, tous leurs attributs sont répertoriés ici.

# Schéma

### `character`

Cette table représente un personnage avec ses différents attributs

```SQL
CREATE TABLE character(
    name VARCHAR(20) PRIMARY KEY,
    w INTEGER,      
    h INTEGER,
    hx1 INTEGER,    /* Les coins de la hitbox.          */
    hy1 INTEGER,    /* On ne considère pas le zoom ici  */
    hx2 INTEGER,
    hy2 INTEGER,
    spritesheet VARCHAR,
    health INTEGER,
    weapon INTEGER,
    speed INTEGER,
    FOREIGN KEY (spritesheet) REFERENCES spritesheet(name),
    FOREIGN KEY (weapon) REFERENCES weapon(weapon_id)
);
```

### `weapon`

Cette table représente une arme

```SQL
CREATE TABLE weapon(
    weapon_id INTEGER PRIMARY KEY AUTOINCREMENT,
    damage INTEGER,
    range INTEGER,
    cooldown FLOAT
);
```

### `spritesheet`

Cette table représente une spritesheet

```SQL
CREATE TABLE spritesheet(
    name VARCHAR(25) PRIMARY KEY,
    path TEXT,
    size INTEGER
);
```

### `animation`

Cette table représente une animation pour une spritesheet.<br>
Pour le moment, si l'attribut `repeat` est à False, on considère qu'aucune autre animation ne peut interrompre celle actuelle.
Si dans le futur une animation qui ne se répète pas, peut être interrompue par une autre, il faudrait ajouter un attribut comme `cancellable`.

```SQL
CREATE TABLE animations(
    name VARCHAR(25),
    spritesheet_id VARCHAR(25),
    position INT,
    repeat BOOLEAN,
    frame_count INT,
    durations TEXT, -- Représente une liste d'entiers
    FOREIGN KEY (spritesheet_id) REFERENCES spritesheet(name),
    PRIMARY KEY (name, spritesheet_id)
);
```
