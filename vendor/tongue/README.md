# Local Tongue Detector

Unmodified 2 MB ONNX tongue detector from FoxyFace, Apache-2.0 (LICENSE included).
Pinned source commit: `1880fb94c2b1b61bedec84bc55746f7e688177ae`.

- Model: https://github.com/Jeka8833/FoxyFace/blob/1880fb94c2b1b61bedec84bc55746f7e688177ae/FoxyFace/src/foxyface/assets/tongue_detector.onnx
- Inference contract: https://github.com/Jeka8833/FoxyFace/blob/1880fb94c2b1b61bedec84bc55746f7e688177ae/FoxyFace/src/foxyface/stream/mediapipe/tongue/MediaPipeTongueModel.py
- SHA256: `b594913c35697a9dd26acb447082a9810d8a4f06141d9435c05852067cbe67f6`

Input: RGB float32 NHWC `[1,256,256,3]`, range 0..1, eye-aligned face crop.
Output: scalar tongue-out score. Our adapter uses upstream-style eye alignment,
proportional 12.5% padding on each side, and two-sample activation hysteresis.
Unlike fixed pixel padding, proportional padding retains crop scale at different
camera distances. This is image inference, not a
mouth-opening substitute. Physical camera accuracy is not yet certified.
No camera images are uploaded or recorded by the runtime.
