"""
ComfyUI Custom Node: Image Compress
Compresses an IMAGE tensor with two independent controls:

  quality      – JPEG: lossy encode quality (1-100).
                 PNG:  deflate compress level (quality 100 → level 0,
                       quality 1 → level 9). PNG pixels are always lossless;
                       this only affects saved file size.

  scale_percent – Downscales the image to this percentage of its original
                  dimensions BEFORE encoding (100 = no resize).
                  Applies to both JPEG and PNG and is the only way to
                  visibly reduce a PNG output tensor.

Outputs:
  image  – compressed/scaled IMAGE tensor
  report – plain-text performance report (also printed to server console)
"""

import io
import time
import numpy as np
import torch
from PIL import Image


class ImageCompress:

    CATEGORY = "image/processing"
    FUNCTION = "compress"
    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image", "report")
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "quality": (
                    "INT",
                    {
                        "default": 80,
                        "min": 1,
                        "max": 100,
                        "step": 1,
                        "display": "slider",
                        "tooltip": (
                            "JPEG: lossy encode quality (1=worst, 100=best). "
                            "PNG: deflate level (100=no compression/smallest deflate, "
                            "1=max deflate). PNG pixels are always lossless — use "
                            "scale_percent to visibly reduce the output."
                        ),
                    },
                ),
                "scale_percent": (
                    "INT",
                    {
                        "default": 100,
                        "min": 1,
                        "max": 100,
                        "step": 1,
                        "display": "slider",
                        "tooltip": (
                            "Resize the image to this percentage of its original "
                            "dimensions before encoding. 100 = no resize. "
                            "50 = half width and height. Applies to both JPEG and PNG."
                        ),
                    },
                ),
                "format": (
                    ["JPEG", "PNG"],
                    {
                        "default": "JPEG",
                        "tooltip": (
                            "JPEG is lossy (quality slider degrades pixels). "
                            "PNG is lossless (quality only affects file size; "
                            "use scale_percent to reduce pixel dimensions)."
                        ),
                    },
                ),
            },
        }

    # ── PIL / tensor helpers ──────────────────────────────────────────────────

    @staticmethod
    def _tensor_to_pil(tensor: torch.Tensor) -> Image.Image:
        np_img = (tensor.cpu().numpy() * 255).clip(0, 255).astype(np.uint8)
        if np_img.ndim == 2 or np_img.shape[2] == 1:
            return Image.fromarray(np_img.squeeze(-1), mode="L")
        elif np_img.shape[2] == 4:
            return Image.fromarray(np_img, mode="RGBA")
        return Image.fromarray(np_img, mode="RGB")

    @staticmethod
    def _pil_to_tensor(pil_img: Image.Image, original_channels: int) -> torch.Tensor:
        if original_channels == 1:
            pil_img = pil_img.convert("L")
            np_img  = np.array(pil_img, dtype=np.float32) / 255.0
            np_img  = np_img[:, :, np.newaxis]
        elif original_channels == 4:
            pil_img = pil_img.convert("RGBA")
            np_img  = np.array(pil_img, dtype=np.float32) / 255.0
        else:
            pil_img = pil_img.convert("RGB")
            np_img  = np.array(pil_img, dtype=np.float32) / 255.0
        return torch.from_numpy(np_img)

    @staticmethod
    def _resize(pil_img: Image.Image, scale_percent: int) -> tuple[Image.Image, int, int]:
        """
        Downscale pil_img to scale_percent % of original dimensions.
        Returns (resized_img, new_w, new_h).
        100 → no-op (original image returned unchanged).
        """
        if scale_percent == 100:
            return pil_img, pil_img.width, pil_img.height
        new_w = max(1, round(pil_img.width  * scale_percent / 100))
        new_h = max(1, round(pil_img.height * scale_percent / 100))
        return pil_img.resize((new_w, new_h), Image.LANCZOS), new_w, new_h

    # ── codec helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _encode_jpeg(pil_img: Image.Image, quality: int) -> bytes:
        buf = io.BytesIO()
        pil_img.convert("RGB").save(buf, format="JPEG", quality=quality, optimize=True)
        return buf.getvalue()

    @staticmethod
    def _encode_png(pil_img: Image.Image, quality: int) -> tuple[bytes, int]:
        # quality 100 → compress_level 0 (store), quality 1 → level 9 (max deflate)
        # optimize=True intentionally omitted — PIL ignores compress_level when it is set
        compress_level = round(9 - (quality - 1) * 9 / 99)
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG", compress_level=compress_level)
        return buf.getvalue(), compress_level

    # ── report builder ────────────────────────────────────────────────────────

    @staticmethod
    def _build_report(
        frame_metrics: list[dict],
        fmt: str,
        quality: int,
        scale_percent: int,
    ) -> str:
        sep = "─" * 58
        lines: list[str] = [
            "╔" + "═" * 56 + "╗",
            "║  IMAGE COMPRESS – PERFORMANCE REPORT" + " " * 18 + "║",
            "╚" + "═" * 56 + "╝",
            f"  Format        : {fmt}",
            f"  Quality       : {quality}/100"
            + ("  (deflate level affects file size only)" if fmt == "PNG" else ""),
            f"  Scale         : {scale_percent}%"
            + ("  (no resize)" if scale_percent == 100 else ""),
            f"  Frames        : {len(frame_metrics)}",
            sep,
        ]

        total_orig_kb = 0.0
        total_comp_kb = 0.0
        total_enc_ms  = 0.0
        total_dec_ms  = 0.0

        for m in frame_metrics:
            ratio    = m["orig_kb"] / m["comp_kb"] if m["comp_kb"] > 0 else float("inf")
            saved_pc = 100.0 * (1 - m["comp_kb"] / m["orig_kb"]) if m["orig_kb"] > 0 else 0.0

            frame_lines = [
                f"  Frame {m['index'] + 1:>3}",
                f"    Input  dimensions: {m['orig_w']:>5}×{m['orig_h']} px",
            ]
            if m["scaled"]:
                frame_lines.append(
                    f"    Output dimensions: {m['out_w']:>5}×{m['out_h']} px  "
                    f"(scaled to {scale_percent}%)"
                )
            frame_lines += [
                f"    Original size    : {m['orig_kb']:>9.2f} KB  (uncompressed)",
                f"    Compressed size  : {m['comp_kb']:>9.2f} KB",
                f"    Size reduction   : {saved_pc:>8.1f} %",
                f"    Compression ratio: {ratio:>7.2f}×",
            ]
            if m.get("compress_level") is not None:
                frame_lines.append(
                    f"    PNG deflate lvl  : {m['compress_level']:>9d}  (0=store, 9=max)"
                )
            if fmt == "PNG" and not m["scaled"]:
                frame_lines.append(
                    "    ⚠  PNG is lossless — output pixels identical to input."
                )
                frame_lines.append(
                    "       Set scale_percent < 100 to visibly reduce the image."
                )
            frame_lines += [
                f"    Encode time      : {m['enc_ms']:>8.2f} ms",
                f"    Decode time      : {m['dec_ms']:>8.2f} ms",
                f"    Total time       : {m['enc_ms'] + m['dec_ms']:>8.2f} ms",
                sep,
            ]
            lines += frame_lines

            total_orig_kb += m["orig_kb"]
            total_comp_kb += m["comp_kb"]
            total_enc_ms  += m["enc_ms"]
            total_dec_ms  += m["dec_ms"]

        if len(frame_metrics) > 1:
            avg_ratio    = total_orig_kb / total_comp_kb if total_comp_kb > 0 else float("inf")
            avg_saved_pc = 100.0 * (1 - total_comp_kb / total_orig_kb) if total_orig_kb > 0 else 0.0
            lines += [
                "  BATCH SUMMARY",
                f"    Total original   : {total_orig_kb:>9.2f} KB",
                f"    Total compressed : {total_comp_kb:>9.2f} KB",
                f"    Avg reduction    : {avg_saved_pc:>8.1f} %",
                f"    Avg ratio        : {avg_ratio:>7.2f}×",
                f"    Total encode     : {total_enc_ms:>8.2f} ms",
                f"    Total decode     : {total_dec_ms:>8.2f} ms",
                f"    Total time       : {total_enc_ms + total_dec_ms:>8.2f} ms",
                sep,
            ]

        return "\n".join(lines)

    # ── main entry point ──────────────────────────────────────────────────────

    def compress(
        self,
        image: torch.Tensor,
        quality: int,
        scale_percent: int,
        format: str,
    ) -> tuple[torch.Tensor, str]:
        is_png = (format == "PNG")

        out_frames: list[torch.Tensor] = []
        frame_metrics: list[dict] = []

        for i in range(image.shape[0]):
            pil_in   = self._tensor_to_pil(image[i])
            orig_h, orig_w = image[i].shape[:2]
            c        = image[i].shape[2] if image[i].ndim == 3 else 1
            orig_kb  = (orig_h * orig_w * c) / 1024.0

            # ── optional resize ───────────────────────────────────────────────
            pil_work, out_w, out_h = self._resize(pil_in, scale_percent)
            scaled = (scale_percent != 100)

            # ── encode ────────────────────────────────────────────────────────
            t0 = time.perf_counter()
            if is_png:
                compressed_bytes, compress_level = self._encode_png(pil_work, quality)
            else:
                compressed_bytes = self._encode_jpeg(pil_work, quality)
                compress_level   = None
            enc_ms = (time.perf_counter() - t0) * 1000.0

            comp_kb = len(compressed_bytes) / 1024.0

            # ── decode ────────────────────────────────────────────────────────
            t1 = time.perf_counter()
            buf     = io.BytesIO(compressed_bytes)
            pil_out = Image.open(buf)
            pil_out.load()
            dec_ms = (time.perf_counter() - t1) * 1000.0

            out_frames.append(self._pil_to_tensor(pil_out, original_channels=c))
            frame_metrics.append(dict(
                index=i,
                orig_w=orig_w, orig_h=orig_h,
                out_w=out_w,   out_h=out_h,
                scaled=scaled,
                orig_kb=orig_kb,
                comp_kb=comp_kb,
                compress_level=compress_level,
                enc_ms=enc_ms,
                dec_ms=dec_ms,
            ))

        out_tensor = torch.stack(out_frames, dim=0)
        report     = self._build_report(frame_metrics, format, quality, scale_percent)
        print("\n" + report + "\n")
        return (out_tensor, report)


# ── Registry ──────────────────────────────────────────────────────────────────

NODE_CLASS_MAPPINGS = {
    "ImageCompress": ImageCompress,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ImageCompress": "Image Compress",
}
