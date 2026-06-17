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
    tileset VARCHAR,
    health INTEGER,
    weapon INTEGER,
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
    cooldown FLOAT);
```
