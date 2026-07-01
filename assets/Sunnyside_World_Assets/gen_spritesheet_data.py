#!/usr/bin/env python3
"""
gen_spritesheet_data.py

Converts an Aseprite JSON sprite-sheet export into SQL INSERT statements
for an `animations` table, ready to be run with sqlite3.

Expected JSON structure (Aseprite "Array" export style):
{
  "frames": [
    {
      "filename": "#walk_0_75.aseprite",
      "frame": {"x": 0, "y": 0, "w": 64, "h": 64},
      "duration": 75,
      ...
    },
    ...
  ],
  "meta": {
    "frameTags": [
      {"name": "walk", "from": 0, "to": 7, ...},
      ...
    ]
  }
}

Usage:
    python gen_spritesheet_data.py path/to/file.json [-o output.sql]

The script will:
  1. Group frames into animations (using meta.frameTags if present,
     otherwise falling back to parsing the filename pattern
     "#<name>_<frame_index>_<duration>.aseprite").
  2. Compute position (y / frame_height), frame_count, and durations
     for each animation.
  3. Ask you interactively whether each animation should "repeat".
  4. Write an SQL file with one INSERT INTO animations statement
     per animation.
"""

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional


FILENAME_PATTERN = re.compile(r"^#?(?P<name>.+)_(?P<index>\d+)_(?P<duration>\d+)\.aseprite$")


class Frame:
    def __init__(self, filename: str, x: int, y: int, w: int, h: int, duration: int):
        self.filename = filename
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.duration = duration


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_frames(data: Dict[str, Any]) -> List[Frame]:
    frames = []
    for entry in data.get("frames", []):
        frame_box = entry["frame"]
        # duration may live at top-level (Aseprite "Array" export) - default to 0 if missing
        duration = entry.get("duration", 0)
        frames.append(
            Frame(
                filename=entry.get("filename", ""),
                x=frame_box["x"],
                y=frame_box["y"],
                w=frame_box["w"],
                h=frame_box["h"],
                duration=duration,
            )
        )
    return frames


def group_by_frame_tags(data: Dict[str, Any], frames: List[Frame]) -> Optional[Dict[str, List[Frame]]]:
    """Group frames using meta.frameTags, if available."""
    frame_tags = data.get("meta", {}).get("frameTags")
    if not frame_tags:
        return None

    animations: Dict[str, List[Frame]] = {}
    for tag in frame_tags:
        name = tag["name"]
        start = tag["from"]
        end = tag["to"]
        if start < 0 or end >= len(frames) or start > end:
            print(f"Warning: frameTag '{name}' has an invalid range ({start}-{end}), skipping.", file=sys.stderr)
            continue
        animations[name] = frames[start:end + 1]
    return animations if animations else None


def group_by_filename(frames: List[Frame]) -> Dict[str, List[Frame]]:
    """Fallback: group frames by parsing the filename pattern."""
    animations: Dict[str, List[Dict[str, Any]]] = {}
    for frame in frames:
        match = FILENAME_PATTERN.match(frame.filename)
        if not match:
            print(f"Warning: filename '{frame.filename}' does not match expected pattern, skipping.", file=sys.stderr)
            continue
        name = match.group("name")
        index = int(match.group("index"))
        animations.setdefault(name, []).append((index, frame))

    # sort each animation's frames by their parsed index and drop the index
    result: Dict[str, List[Frame]] = {}
    for name, indexed_frames in animations.items():
        indexed_frames.sort(key=lambda pair: pair[0])
        result[name] = [frame for _, frame in indexed_frames]
    return result


def compute_animation_data(name: str, frames: List[Frame]) -> Dict[str, Any]:
    if not frames:
        raise ValueError(f"Animation '{name}' has no frames.")

    frame_height = frames[0].h
    first_y = frames[0].y

    # Sanity check: warn if frames within the same animation don't share a common height
    heights = {f.h for f in frames}
    if len(heights) > 1:
        print(f"Warning: animation '{name}' has frames with differing heights: {heights}", file=sys.stderr)

    if frame_height == 0:
        raise ValueError(f"Animation '{name}' has a frame height of 0, cannot compute position.")

    position = first_y // frame_height
    frame_count = len(frames)
    durations = ",".join(str(f.duration) for f in frames)

    return {
        "name": name,
        "position": position,
        "frame_count": frame_count,
        "durations": durations,
    }


def ask_repeat(animation_name: str) -> bool:
    while True:
        answer = input(f"Should animation '{animation_name}' repeat? [y/n]: ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("Please answer 'y' or 'n'.")


def escape_sql_string(value: str) -> str:
    return value.replace("'", "''")


def build_insert_statements(spritesheet_id: str, animations: List[Dict[str, Any]]) -> str:
    lines = [
        "-- Auto-generated by gen_spritesheet_data.py",
        f"-- Spritesheet: {spritesheet_id}",
        "",
    ]
    for anim in animations:
        lines.append(
            "INSERT INTO animations "
            "VALUES ({name}, {spritesheet_id}, {position}, {repeat}, {frame_count}, {durations});".format(
                name=f"'{escape_sql_string(anim['name'])}'",
                spritesheet_id=f"'{escape_sql_string(spritesheet_id)}'",
                position=anim["position"],
                repeat=1 if anim["repeat"] else 0,
                frame_count=anim["frame_count"],
                durations=f"'{escape_sql_string(anim['durations'])}'",
            )
        )
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Convert an Aseprite JSON export into SQL INSERT statements for the animations table.")
    parser.add_argument("json_file", help="Path to the Aseprite JSON export file.")
    parser.add_argument("-o", "--output", help="Path to the output .sql file. Defaults to <json_basename>.sql")
    args = parser.parse_args()

    if not os.path.isfile(args.json_file):
        print(f"Error: file not found: {args.json_file}", file=sys.stderr)
        sys.exit(1)

    data = load_json(args.json_file)
    frames = parse_frames(data)

    if not frames:
        print("Error: no frames found in JSON file.", file=sys.stderr)
        sys.exit(1)

    grouped = group_by_frame_tags(data, frames)
    if grouped is None:
        print("No usable meta.frameTags found - falling back to filename parsing.")
        grouped = group_by_filename(frames)

    if not grouped:
        print("Error: could not detect any animations in the JSON file.", file=sys.stderr)
        sys.exit(1)

    spritesheet_id = os.path.splitext(os.path.basename(args.json_file))[0]

    print(f"Detected spritesheet_id: '{spritesheet_id}'")
    print(f"Detected {len(grouped)} animation(s): {', '.join(grouped.keys())}\n")

    animations_data = []
    # keep animations in a stable order (as they appear in frameTags / file)
    for name, anim_frames in grouped.items():
        anim_data = compute_animation_data(name, anim_frames)
        anim_data["repeat"] = ask_repeat(name)
        animations_data.append(anim_data)

    sql_output = build_insert_statements(spritesheet_id, animations_data)

    output_path = args.output or f"{spritesheet_id}.sql"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(sql_output)

    print(f"\nDone! SQL written to: {output_path}")


if __name__ == "__main__":
    main()
    