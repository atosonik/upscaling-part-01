# upscaling-part-01

Piece 1 of 3 from https://github.com/atosonik/upscaling.git.

This repo is one new commit. Paths match the original tree. History was not copied.
File bytes in this piece: 374.8 MB. Files: 407.

## Put the tree back together

```bash
mkdir -p upscaling-pieces && cd upscaling-pieces
git clone --depth 1 https://github.com/atosonik/upscaling-part-01.git
git clone --depth 1 https://github.com/atosonik/upscaling-part-02.git
git clone --depth 1 https://github.com/atosonik/upscaling-part-03.git
cd ..
mkdir -p upscaling
for d in upscaling-pieces/*/; do
  tar -C "$d" --exclude .git --exclude PIECE.md --exclude SPLIT.json -cf - . | tar -C upscaling -xf -
done
cd upscaling
python chunker.py merge
python pack_app.py --unpack
```

`chunker.py merge` rebuilds `weights/` from `parts/`.
`pack_app.py --unpack` rebuilds `dist/Lumina/` from `runableparts/`.
Every piece is listed in `SPLIT.json`.
