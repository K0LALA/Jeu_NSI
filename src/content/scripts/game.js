// L'objectif de ce script est de gérer l'affichage des personnages
// En effet l'utilisation de GIF pour chacun des personnages est laborieux
// D'une part pour l'export, il faut sélectionner les frames voulues, leur mettre une certaine durée puis exporter en GIF pour chaque animation
// D'autre part pour le rendu, les GIFs demandent beaucoup de ressources au processeur
// Ce script a donc pour but de simplifier ces 2 processus en utilisant un canvas commun à tous les personnages
// De plus, avec un tel fonctionnement, il devient alors possible d'avoir les personnages qui se chevauchent mieux selon leur position par rappport aux autres

// A chaque frame, on fait donc le rendu de tous les personnages
// Les personnages sont stockés dans une liste triée dans l'ordre croissant en fonction de leur position Y
// Les premiers personnages de la liste sont rendus au second plan
// Pour chacun des personnages, on stocke donc l'animation actuelle, l'indice de la frame dans l'animation et la position
let charactersCanvas = document.getElementById("canvas-characters");
charactersCanvas.width = window.innerWidth;
charactersCanvas.height = window.innerHeight;
let charactersCanvasContext = charactersCanvas.getContext("2d");
charactersCanvasContext.imageSmoothingEnabled = false;
let animationMap = new Map();
let characterMap = new Map();
let lastUpdate = document.timeline.currentTime;

class Animation {
    constructor(name, spritesheetPath, size, animations, frames, durations) {
        this.name = name;

        this.spritesheetPath = spritesheetPath;
        this.spritesheet = new Image;
        this.spritesheet.src = spritesheetPath;
        this.size = size;

        this.animations = new Map();
        let i = 0;
        animations.forEach(animation => {
            this.animations.set(animation, i);
            i++;
        });
        // Liste, donne le nombre de frames pour chaque animation
        this.frames = frames;
        // Liste de listes, donne la durée de chaque frame pour chaque animation
        this.durations = durations
    }

    getFrames(animation) {
        return this.frames[this.animations.get(animation)];
    }

    getDurations(animation) {
        return this.durations[this.animations.get(animation)];
    }

    drawFrame(animation, frame, x, y, dstSize) {
        while (!this.spritesheet.complete) {
            ;
        }
        let animationIndex = this.animations.get(animation);
        charactersCanvasContext.drawImage(this.spritesheet,
            frame * this.size, animationIndex * this.size, this.size, this.size,
            x, y, dstSize, dstSize
        )
    }
}

animationMap.set("player", new Animation("player", "../assets/spritesheets/player.png", 32,
    ["idle_front", "idle_right", "idle_back", "walk_front", "walk_right", "walk_right", "walk_back", "attack_front", "attack_right", "attack_back", "dead"],
    [6, 6, 6, 6, 6, 6, 4, 4, 4, 4],
    [   [150, 150, 150, 150, 150, 150],
        [150, 150, 150, 150, 150, 150],
        [150, 150, 150, 150, 150, 150],
        [150, 150, 150, 150, 150, 150],
        [150, 150, 150, 150, 150, 150],
        [150, 150, 150, 150, 150, 150],
        [150, 150, 100, 150],
        [150, 150, 100, 150],
        [150, 150, 100, 150],
        [150, 150, 150, 200]]))

class Character {
    constructor(name, animationName, x, y, size) {
        this.name = name;

        this.animation = animationMap.get(animationName);
        this.currentAnimation = this.animation.animations.keys().next().value;
        this.animationFrameIndex = 0;
        this.animationFrameCount = this.animation.getFrames(this.currentAnimation);
        this.animationDurations = this.animation.getDurations(this.currentAnimation);

        this.x = x;
        this.y = y;
        this.size = size;
        
        // Donne la durée passée sur la frame actuelle
        this.lasted = 0;
    }

    changeAnimation(animation) {
        if (this.animation.animations.has(animation) == false) {
            return;
        }
        this.currentAnimation = animation;
        this.animationFrameIndex = 0;
        this.animationFrameCount = this.animation.getFrames(this.currentAnimation);
        this.animationDurations = this.animation.getDurations(this.currentAnimation);
    }

    changePosition(x, y) {
        this.x = x;
        this.y = y;
    }

    tick(dT) {
        let new_lasted = this.lasted + dT;
        if (new_lasted > this.animationDurations[this.animationFrameIndex]) {
            new_lasted -= this.animationDurations[this.animationFrameIndex];
            this.animationFrameIndex += Math.floor(new_lasted / this.animationDurations[this.animationFrameIndex]);
            this.animationFrameIndex %= this.animationFrameCount;
        }
        this.lasted = new_lasted;

        this.animation.drawFrame(this.currentAnimation, this.animationFrameIndex, this.x, this.y, this.size);
    }
}

function updateRender(timestamp) {
    if (!animationMap.values().next().value.spritesheet.complete)
    {
        requestAnimationFrame(updateRender);
    }

    charactersCanvasContext.clearRect(0, 0, charactersCanvasContext.width, charactersCanvasContext.height);

    deltaTime = timestamp - lastUpdate;

    characterMap.forEach(character => {
        character.tick(deltaTime);
    });

    lastUpdate = timestamp;

    requestAnimationFrame(updateRender);
}

// TODO: Appeler cette fonction lorsque le menu se ferme
//requestAnimationFrame(updateRender);
