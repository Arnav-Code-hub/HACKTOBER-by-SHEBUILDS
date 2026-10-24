# Approved demonstration photos

No images have been copied here: the existing app gallery has no documented
approval for public evidence use. Add only photos approved by their owner.
These files ship in the API Docker image through its existing `COPY seeds/`.

Copy `../photos.example.json` to `../photos.local.json`, specify the source,
affirm public-display approval and provide either a packaged file name or an
already uploaded deterministic public ID. Run the seed command with
`--photos-manifest seeds/demo/photos.local.json` and real Cloudinary settings.
The command verifies provider metadata and never attaches arbitrary URLs.

Uploads use deterministic IDs and `overwrite=false`. A database rollback can
leave a remote upload; a retry reuses it. Reset clears local records only and
keeps those remote assets and report-code sequence values.
