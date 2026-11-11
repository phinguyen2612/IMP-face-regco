# SCRFD sliced inference

The camera ROI filters person detections by their bottom-center point. It does
not change the resolution at which the person detector runs. SCRFD subsequently
receives each tracked person's crop, not the full camera frame.

SCRFD supports optional SAHI-style overlapping sliced inference implemented in
the existing adapter without the `sahi` package. The adapter preserves five-point
landmarks, the crop's source frame, and parent-ROI coordinates. TrackFaceProcessor
continues to convert those coordinates into full-frame coordinates for observations.

Add this object to the SCRFD model manifest's `metadata` and deploy that version
through the existing model delivery flow:

```json
"sliced_inference": {
  "enabled": true,
  "tile_width": 640,
  "tile_height": 640,
  "overlap_ratio": 0.2,
  "max_tiles": 16
}
```

These are the defaults except `enabled`, which defaults to `false`. Existing
deployments retain standard inference until explicitly configured. This is model
manifest configuration; there is no new camera UI setting.

The adapter always performs the standard crop pass, then overlapping tile passes.
It skips slicing when the crop fits in one tile. If the grid exceeds `max_tiles`,
it doubles tile dimensions until the entire crop fits within the budget; it never
truncates coverage. The budget excludes the standard pass and accepts 1–64 tiles.
Tile dimensions accept integers from 32 to 16384; overlap accepts 0–0.5.
Invalid or unknown settings fail adapter preparation explicitly.

Tile boxes and all five landmarks are translated back to parent-crop coordinates.
Global IoU NMS uses the manifest's existing `iou_threshold`, retaining the winning
box and its corresponding landmarks together. Candidate storage is capped at the
900 highest-confidence faces before global NMS. Timings accumulate across passes;
attempt/success/no-face counters count parent crops. Any tile failure fails the
whole crop attempt, rather than returning a partial success or `NO_FACE`.

Slicing can help faces that lose detail when large person crops are downscaled.
It cannot recover a person missed by the upstream person detector, faces outside
the person's crop, or detail absent from the source video. Small person crops may
already be enlarged by SCRFD, so slicing often does not help distant faces there.
This does not add full-frame face scanning or change tracking/identity association.

Before enabling on a camera, compare the same annotated video with slicing off
and on: face recall, duplicate/false detections, alignment/quality acceptance,
end-to-end latency and processed FPS. Use the same detector confidence threshold
and ROI. Tune tile dimensions to the actual SCRFD input and camera crop sizes.
The additional inference calls cost latency; a tile budget is not a time budget.
Controlled tests verify geometry and failure handling, not real-camera accuracy.

Reference: [SAHI sliced inference guide](https://github.com/obss/sahi/blob/main/docs/guides/sliced-inference.md).
