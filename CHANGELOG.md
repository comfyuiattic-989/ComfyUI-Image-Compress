# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-01

### Added
- Initial release
- JPEG lossy compression with quality slider (1–100)
- PNG lossless compression with deflate level control (mapped from quality slider)
- `scale_percent` input to resize image dimensions before encoding (1–100%)
- Batch tensor support — all frames in a batch are processed independently
- Performance report output (`STRING`) with per-frame metrics:
  - Original and compressed file sizes (KB)
  - Size reduction percentage and compression ratio
  - PNG deflate level confirmation
  - Encode and decode timing (ms)
  - Batch summary for multi-frame inputs
- Round-trip encode→decode so JPEG artefacts are reflected in the output tensor
- Explicit PIL mode normalisation (`RGB`, `RGBA`, `L`) to prevent shape mismatches downstream
- Warning in report when PNG is used at `scale_percent = 100` (pixels will be unchanged)
- Server console echo of the performance report on every execution
