board = document.getElementById("board");
tiles = document.getElementById("tiles");

worldSelect = document.getElementById("world");
layerContainer = document.getElementById("layers");
selected = null;
indexInput = document.getElementById("index");
tileSizeInput = document.getElementById("tile_size");
collisionsCheck = document.getElementById("collisions");
createLayerButton = document.getElementById("add");

tileset = document.getElementById("tileset");
tilesetSelect = document.getElementById("tileset-choice");
brush = null;
toolsElement = document.getElementById("tools");
activeTool = toolsElement.children[0];

worldSelect.addEventListener("change", (event) => {
    // On souhaite garder le premier enfant, sachant que c'est les cases de selection
    while (tiles.children.length > 1) {
        tiles.removeChild(tiles.lastChild);
    }
    transmettre("world_changed", event.target.value);
    event.target.blur();
});

function addLayers(layers) {
    while (layerContainer.firstChild) {
        layerContainer.removeChild(layerContainer.lastChild);
    }
    layers.forEach(element => {
        addLayer(element);
    });
}

function addLayer(layer) {
    // layer: [index: int, tileset: str, tiles_size: int, collisions: boolean]
    parent = document.createElement("div");
    parent.classList.add("layer");
    parent.id = "layer_option_" + String(layer[0])
    
    layerText = document.createElement("p");
    layerText.innerText = layer[0];
    layerText.classList.add("layer-id");
    
    tilesetText = document.createElement("p");
    tilesetText.innerText = layer[1];
    tilesetText.classList.add("layer-tileset");
    
    enabledInput = document.createElement("span");
    enabledInput.innerText = "🕶";
    enabledInput["layer"] = layer[0];
    enabledInput.classList.add("layer-enable");
    enabledInput.addEventListener("click", (e) => {
        layer = document.getElementById("layer_" + e.target.layer);
        if (e.target.innerText === "🕶") {
            e.target.innerText = "👁";
            layer.style["display"] = "none";
        }
        else {
            e.target.innerText = "🕶";
            layer.style["display"] = "block";
        }
        e.stopPropagation();
    });

    deleteInput = document.createElement("span");
    deleteInput.innerText = "🗑";
    deleteInput.classList.add("layer-delete");
    deleteInput.addEventListener("click", (e) => {
        if (confirm("Voulez-vous vraiment supprimer cette couche ?\nCette action sera définitive!")) {
            transmettre("delete_layer", selected.children[0].innerText);
        }
    });
    
    parent.appendChild(layerText);
    parent.appendChild(tilesetText);
    parent.appendChild(enabledInput);
    parent.appendChild(deleteInput);
    parent.tiles_size = layer[2];

    // On utilise function(event) et pas (event) =>
    // Sinon il n'y a pas de `this` et event.target se réfère à l'élément clické
    // Donc pas forcément parent car peut être le texte enfant
    parent.addEventListener("click", function(_) {
        if (selected === this)
        {
            return;
        }
        if (selected != null && selected != undefined)
        {
            selected.classList.remove("selected");
        }
        this.classList.add("selected");
        selected = this;
        transmettre("layer_changed", this.children[0].innerText);
        tileset.style["grid-auto-columns"] = String(this.tiles_size) + "px";
        tileset.style["grid-template-rows"] = "repeat(auto-fill, minmax(" + String(this.tiles_size) + "px, 1fr))";
    });
    layerContainer.appendChild(parent);
}

add.addEventListener("click", (_) => {
    let index = indexInput.value;
    // On verifie qu'il n'y ait pas d'autres couche avec le meme indice
    let children = layerContainer.children;
    for (let i = 0; i < children.length; i++)
    {
        if (children[i].children[0].innerText == index)
        {
            alert("Une couche existe deja a ce niveau !");
            return;
        }
    }
    let tileset = tilesetSelect.value;
    let tileSize = tileSizeInput.value;
    let collisions = collisionsCheck.checked;
    //addLayer([index, tileset, tileSize, collisions]);
    console.log([index,tileset,tileSize,collisions]);
    //transmettre("create_layer", [index, tileset, tileSize, collisions])
});

board.addEventListener("mousemove", (e) => {
    transmettre("mouse_moved", [e.target.id, e.buttons, e.clientX, e.clientY]);
});

function addTilesEvent() {
    children = tileset.children;
    for (let i = 0; i < children.length; i++) {
        children[i].addEventListener("click", (e) => {
            if (brush != null && brush != undefined) {
                brush.classList.remove("brush");
            }
            e.target.classList.add("brush");
            brush = e.target;
            src = e.target.src;
            // On ne recupere que le fichier image
            transmettre("tile_changed", src.substring(src.lastIndexOf("/") + 1));
        });
    }
}

function tool(toolElement, newActiveTool) {
    transmettre("tool_changed", newActiveTool);
    if (activeTool != null)
    {
        // Si c'est l'outil de sélection et qu'on gomme on veut pas sélectionner l'outil gomme mais effacer la sélection
        if (activeTool.innerText === "🔳" && newActiveTool === "erase" && !document.getElementById("corner-1").classList.contains("hidden") && !document.getElementById("corner-2").classList.contains("hidden"))
            return;
        activeTool.classList.remove("tool-selected");
    }
    activeTool = toolElement;
    toolElement.classList.add("tool-selected");
}

function hideBackground() {
    if (board.classList.contains("grid-background")) {
        board.classList.remove("grid-background");
    }
    else {
        board.classList.add("grid-background");
    }
}
