# Vision dataset

## v1: storefront / business-sign detection

**[Store Front Signage Detection](https://universe.roboflow.com/storefront-detection/store-front-signage-detection-ycolf)**
(Roboflow Universe) -- verified via search (Roboflow Universe pages block
direct fetching, so this was confirmed through indexed search results, not
a live page load -- re-check the page yourself before relying on exact
numbers):
- 788 images, 1 class: `store-sign`
- License: CC BY 4.0 (attribution required -- credit this in the README)
- Export format: YOLOv8 (native Roboflow export option)

This covers the BUSINESS entity category in the threat model directly --
storefront/shop signage revealing what business you're at. It's the
well-verified dataset the training script (`train.py`) is built against.

### Downloading it

```
venv/Scripts/python.exe -m vision.download_dataset \
    --workspace storefront-detection \
    --project store-front-signage-detection-ycolf \
    --version 1 \
    --api-key <your-free-roboflow-api-key>
```

Get a free API key at https://app.roboflow.com/settings/api after creating
an account. Downloads to `data/vision/store-front-signage-detection-ycolf/`
with a `data.yaml` the training script reads directly.

## v2 (not yet built): street name sign detection

The STREET entity category (green rectangular signs showing a street's
name, e.g. "Main St") is the other half of the vision threat model, but I
wasn't able to verify a good, confirmed dataset for it in this pass --
general "traffic sign" datasets (stop/yield/speed-limit signs, e.g. GTSRB
or the HF `StreetSignSet`) turned out to be a different category entirely
(regulatory/warning signage, not street-name signage), and Roboflow
Universe's street-sign-specific projects couldn't be verified in detail
(the site blocks automated fetching, and search snippets alone weren't
enough to confirm class taxonomy/quality).

Candidates worth checking by hand before committing to one:
- https://universe.roboflow.com/jacek-kaluzny/street-signs-tfqfg
- https://universe.roboflow.com/university-of-genoa-ijsvk/street-signs-ma7g6
  (search snippet called this one "street-signs-stickers" -- verify it's
  actually about street name signs and not something else, e.g. sticker
  vandalism on sign posts, before using it)

Once a dataset is picked, `download_dataset.py` and `train.py` both work
against any Roboflow YOLOv8 export already (they're not hardcoded to the
storefront project) -- either fine-tune a second model, or merge both
datasets into one Roboflow workspace project (a supported first-class
Roboflow feature for combining multiple public datasets with unified class
IDs) and fine-tune once on the merged set.
