import time
from pathlib import Path

import cv2
from ultralytics import YOLO

IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def iter_images(img_dir: str | Path) -> list[Path]:
    img_dir = Path(img_dir)
    if not img_dir.exists():
        raise FileNotFoundError(f"Image directory not found: {img_dir}")

    paths = [
        p for p in img_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in IMG_EXTS
    ]
    return sorted(paths)


def main():
    # -------- paths --------
    weights = r"./runs/msight_yolo26n/weights/best.pt"
    img_dir = r"./test-data/gs_mcity_ne"
    # ----------------------

    imgsz = 640
    conf_thres = 0.25
    device = None        # "0" for GPU, "cpu" for CPU, None = auto

    show = True          # set True to see a preview window

    model = YOLO(weights)

    paths = iter_images(img_dir)
    if not paths:
        raise RuntimeError(f"No images found in: {img_dir}")

    print(f"[OK] Found {len(paths)} images")

    # ---- warmup (important for stable timing) ----
    first = cv2.imread(str(paths[0]))
    if first is None:
        raise RuntimeError(f"Cannot read first image: {paths[0]}")
    _ = model.predict(first, imgsz=imgsz, conf=conf_thres, device=device, verbose=False)

    for idx, p in enumerate(paths, 1):
        img = cv2.imread(str(p))
        if img is None:
            print(f"[WARN] Cannot read: {p}")
            continue

        t0 = time.perf_counter()
        results = model.predict(
            source=img,
            imgsz=imgsz,
            conf=conf_thres,
            device=device,
            verbose=False,
            end2end=False,
            iou=0.5,
        )
        infer_ms = (time.perf_counter() - t0) * 1000.0

        # Draw ONLY bounding boxes (no label, no confidence)
        annotated = results[0].plot(labels=False, conf=False)

        n_boxes = int(len(results[0].boxes)) if results[0].boxes is not None else 0
        print(
            f"[{idx:05d}/{len(paths):05d}] "
            f"{p.name} | boxes={n_boxes} | infer={infer_ms:.2f} ms"
        )

        if show:
            cv2.imshow("YOLO Playback", annotated)
            if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                break

    if show:
        cv2.destroyAllWindows()

    print("[OK] Detection complete.")


if __name__ == "__main__":
    main()
