"""Render an explicitly labeled orbit of saved reconstructed geometry, not live capture."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps


def render(run: Path, destination: Path, cloud="cloud.json", dataset="TUM fr1_xyz", credit="TUM RGB-D · CC BY 4.0"):
    data = json.loads((run / cloud).read_text())
    summary = data["summary"]
    xyz, rgb = np.array(data["points"]), np.array(data["colors"], dtype=np.uint8)
    if data.get("cameras"):
        xyz = np.einsum("ij,jk->ik", xyz, np.array(data["cameras"][len(data["cameras"])//2]["rotation_world_from_camera"]), optimize=False)
    lower, upper = np.percentile(xyz, [1, 99], axis=0)
    xyz = (xyz-(lower+upper)/2) / max(upper-lower) * 2
    font_path = "/System/Library/Fonts/Supplemental/Arial.ttf"
    try:
        title = ImageFont.truetype(font_path, 25)
        body = ImageFont.truetype(font_path, 16)
        small = ImageFont.truetype(font_path, 13)
    except OSError:
        title, body, small = [ImageFont.load_default(size=size) for size in (25, 16, 13)]
    photos = sorted((run / "images").glob("*.jpg"))
    frames = []
    for index in range(28):
        image = Image.new("RGB", (900, 510), "#0b111b")
        draw = ImageDraw.Draw(image)
        draw.text((22, 15), "Multi-view reconstruction", font=title, fill="#eef5ff")
        draw.text((22, 48), f"{summary['registered_images']}/{summary['input_images']} estimated cameras · {summary['output_points']:,} {'sparse SfM' if summary['output_kind']=='sparse_sfm' else 'stereo'} points", font=body, fill="#74d9cb")
        draw.text((22, 83), f"Real RGB inputs ({dataset})", font=small, fill="#9eb0c8")
        for number, photo_index in enumerate((0, len(photos)//2, len(photos)-1)):
            with Image.open(photos[photo_index]) as photo:
                thumbnail = ImageOps.fit(photo, (205, 116))
            image.paste(thumbnail, (22, 110+number*126))
        draw.rounded_rectangle((246, 82, 880, 464), radius=8, fill="#0c1926", outline="#293b50")
        draw.text((261, 94), "Saved reconstruction · display orbit", font=small, fill="#9eb0c8")
        # Oscillation makes a loop; it does not add views, points or estimated poses.
        yaw = .5*np.sin(index/28*2*np.pi)
        cy, sy = np.cos(yaw), np.sin(yaw)
        rotation = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
        p = np.einsum("ij,jk->ik", xyz, rotation.T, optimize=False)
        z = p[:, 2] + 3.2
        px = np.rint(563+p[:, 0]/z*450).astype(int)
        py = np.rint(280+p[:, 1]/z*450).astype(int)
        inside = (z > .1) & (px > 250) & (px < 876) & (py > 120) & (py < 460)
        for i in np.argsort(-z):
            if inside[i]:
                draw.rectangle((int(px[i]), int(py[i]), int(px[i])+1, int(py[i])+1), fill=tuple(rgb[i]))
        draw.text((22, 480), f"{credit} · RGB only · arbitrary scale · saved-result orbit", font=small, fill="#9eb0c8")
        frames.append(image.quantize(colors=96, method=Image.Quantize.MEDIANCUT))
    destination.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(destination, save_all=True, append_images=frames[1:], duration=90, loop=0, optimize=True)
    frames[0].convert("RGB").save(destination.with_suffix(".png"))
    return destination.stat().st_size


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--cloud", default="cloud.json")
    parser.add_argument("--dataset", default="TUM fr1_xyz")
    parser.add_argument("--credit", default="TUM RGB-D · CC BY 4.0")
    args = parser.parse_args()
    print(render(args.run, args.destination, args.cloud, args.dataset, args.credit))
