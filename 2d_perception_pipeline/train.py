from ultralytics import YOLO
from pathlib import Path


def main():
    # Path to your dataset YAML file (Ultralytics format)
    # Example: mcity_yolo.yaml
    data_yaml = "./mcity_data_yolo/data.yaml"

    # Initialize YOLOv26 model
    # You can also start from a pretrained checkpoint if desired
    weights = "yolo26n.pt"
    model = YOLO(weights)
    project = Path("./runs")
    name = "msight_yolo26n"

    # Train the model
    model.train(
        data=data_yaml,
        imgsz=640,
        epochs=100,
        batch=16,
        device=0,        # use GPU 0; set to "cpu" if no GPU is available
        workers=8,
        project=str(project),
        name=name,
    )


if __name__ == "__main__":
    main()
   