# Examples

A lightweight, high-performance custom node for **ComfyUI** designed to optimize workflows by compressing images on the fly. This node is perfect for reducing storage footprints or preparing images for web delivery without leaving your workflow.

## 🛠 Features

  * **Lossy & Lossless Support:** Switch between PNG, JPEG, and WebP formats.
  * **Granular Quality Control:** Fine-tune the compression level to balance file size and visual fidelity.
  * **On-the-fly Scaling:** Reduce dimensions by a percentage to further optimize processing time and storage.
  * **Reporting:** Output a text report of the compression results.

-----

## 🚀 Node Settings

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| **image** | INPUT | - | The image tensor to be compressed. |
| **quality** | INT | 25 | Compression intensity (1-100). Lower values result in smaller files. |
| **scale\_percent** | INT | 65 | Resizes the image by this percentage before compression. |
| **format** | COMBO | PNG | Choose between `PNG`, `JPG`, or `WEBP`. |

-----

## 📊 Comparison Results

The following example demonstrates the node in action using a high-detail portrait. Even at a **Quality setting of 25** and a **Scale of 65%**, the node maintains significant visual integrity while drastically reducing the data footprint.

### 1\. Original (Uncompressed)

The original image contains high-frequency details in the hair, skin texture, and reflections in the sunglasses.

### 2\. Compressed (Quality: 25, Scale: 65%)

After processing, the image remains sharp enough for most web and AI-generation preview purposes.

### 3\. Node Configuration

The setup used for the comparison above:
[![Example-01-Settings.png](https://i.postimg.cc/ZRqf9jsf/Example-01-Settings.png)](https://postimg.cc/1gL020Q6)

-----

## Comparison Gallery

| Uncompressed (Original) | Compressed (65% Scale, 25 Quality) |
| :---: | :---: |
| [![Example-01-Uncompressed.png](https://i.postimg.cc/WpkG5Qrc/Example-01-Uncompressed.png)](https://postimg.cc/bdqSJV3m)(https://postimg.cc/bdqSJV3m) | [![Example-01-Compressed.png](https://i.postimg.cc/s2GxVRsb/Example-01-Compressed.png)](https://postimg.cc/yJBsPtJT)(https://postimg.cc/yJBsPtJT) |
| *Full Resolution / 3.55MB* | *Optimized / 1.62MB* |
