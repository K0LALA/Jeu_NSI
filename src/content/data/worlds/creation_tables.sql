CREATE TABLE IF NOT EXISTS worlds (name VARCHAR PRIMARY KEY);
CREATE TABLE IF NOT EXISTS NPCs (npc_id INTEGER PRIMARY KEY AUTOINCREMENT, block_id INT, x INT, y INT, npc_name VARCHAR, npc_image TEXT, FOREIGN KEY (block_id) REFERENCES blocks(block_id));
CREATE TABLE IF NOT EXISTS ennemies (ennemy_id INTEGER PRIMARY KEY AUTOINCREMENT, block_id INT, x INT, y INT, ennemy_type VARCHAR, FOREIGN KEY (block_id) REFERENCES blocks(block_id));
CREATE TABLE IF NOT EXISTS blocks (block_id INTEGER PRIMARY KEY AUTOINCREMENT, block_x INT, block_y INT, world VARCHAR, layer_index INT, FOREIGN KEY (world, layer_index) REFERENCES layers(world, layer_index));
CREATE TABLE IF NOT EXISTS tiles(block_id INTEGER, x INTEGER, y INTEGER, image_name TEXT, PRIMARY KEY (block_id, x, y), FOREIGN KEY (block_id) REFERENCES blocks(block_id));
CREATE Table IF NOT EXISTS layers(world VARCHAR, layer_index INT, tileset TEXT, tiles_size INT, collisions BOOLEAN, PRIMARY KEY (world, layer_index));
CREATE Table IF NOT EXISTS waypoints (waypoint_id INTEGER PRIMARY KEY AUTOINCREMENT, block_id INT, x INT, y INT, destination TEXT, FOREIGN KEY (block_id) REFERENCES blocks(block_id));